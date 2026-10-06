"""Economy hook regression checks without a running game or SDK installation."""

import contextlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock


class Object(types.SimpleNamespace):
    def _path_name(self):
        return self.path

    def _get_address(self):
        return id(self)


class WeakPointer:
    def __init__(self, obj):
        self.obj = obj

    def __call__(self):
        return self.obj


class Block:
    pass


credits = 0
sdk = types.ModuleType("unrealsdk")
sdk.logging = types.SimpleNamespace(info=Mock(), error=Mock())
sdk.find_enum = lambda _: types.SimpleNamespace(CURRENCY_Credits=credits)
hooks = types.ModuleType("unrealsdk.hooks")
hooks.Block = Block
hooks.Type = types.SimpleNamespace(PRE=0, POST=1)
hooks.prevent_hooking_direct_calls = contextlib.nullcontext
hooks.add_hook = Mock(return_value=True)
hooks.remove_hook = Mock()
sdk.hooks = hooks
unreal = types.ModuleType("unrealsdk.unreal")
unreal.BoundFunction = unreal.UObject = unreal.WrappedStruct = Object
unreal.WeakPointer = WeakPointer
base = types.ModuleType("mods_base")
base.build_mod = Mock()
base.get_pc = Mock()
mod = types.ModuleType("economy_under_test")
source = Path(__file__).resolve().parents[1] / "op_inflation_buster" / "__init__.py"
with unittest.mock.patch.dict(sys.modules, {
    "unrealsdk": sdk, "unrealsdk.hooks": hooks,
    "unrealsdk.unreal": unreal, "mods_base": base,
}):
    # The SDK uses newer Python; postponed hints also allow the tests on Python 3.9.
    exec(compile("from __future__ import annotations\n" + source.read_text(), str(source), "exec"), mod.__dict__)


def item_definition(path, currency=credits, effects=()):
    return Object(path=path, FormOfCurrency=currency, AttributeSlotEffects=effects)


def cash_effect(external=True, attribute=None, formula=None):
    return Object(
        bExternalSlot=external,
        AttributeToModify=Object(path=attribute or mod.CREDITS_ATTRIBUTE),
        BaseModifierValue=Object(InitializationDefinition=Object(path=formula or mod.CASH_PICKUP_FORMULA)),
        PerGradeUpgrade=Object(InitializationDefinition=None),
    )


class EconomyTests(unittest.TestCase):
    def setUp(self):
        for cache in (mod._cash_before, mod._cash_definitions, mod._reports, mod._attempted,
                      mod._touched, mod._slot_actors, mod._slot_original_costs):
            cache.clear()
        sdk.logging.info.reset_mock()
        sdk.logging.error.reset_mock()
        self.wallet = 1_000_000
        self.rep = Object(
            GetCurrencyOnHand=lambda _: self.wallet,
            AddCurrencyOnHand=lambda _, amount: setattr(self, "wallet", self.wallet + amount),
        )
        self.pc = Object(PlayerReplicationInfo=self.rep, Pawn=Object(GameStage=85))
        base.get_pc.return_value = self.pc

    def pickup(self, definition, gain=26322, stage=85, exp_level=85):
        inventory = Object(Class=Object(Name="WillowUsableItem"), ExpLevel=exp_level,
                           DefinitionData=Object(ItemDefinition=definition, GameStage=stage))
        mod.cash_use_pre(inventory, None, None, None)
        self.wallet += gain
        mod.cash_use_post(inventory, None, None, None)
        return inventory

    def test_all_known_cash_types_cap_wallet_once(self):
        for path in mod.CASH_ITEM_DEFINITIONS:
            with self.subTest(path=path):
                old = self.wallet
                inventory = self.pickup(item_definition(path))
                self.assertEqual(self.wallet - old, 2)
                mod.cash_use_post(inventory, None, None, None)
                self.assertEqual(self.wallet - old, 2)
        self.assertFalse(sdk.logging.error.called)

    def test_new_definition_with_verified_formula_is_covered(self):
        definition = item_definition("Example.Cash", effects=[cash_effect()])
        self.pickup(definition)
        self.assertEqual(self.wallet, 1_000_002)
        self.assertTrue(mod._cash_definitions[definition._get_address()][1])

    def test_refunds_fixed_rewards_and_other_currencies_are_unchanged(self):
        definitions = [item_definition(path, effects=[cash_effect()])
                       for path in mod.UNSCALED_CASH_DEFINITIONS]
        definitions += [item_definition("Other.Eridium", 1, [cash_effect()]),
                        item_definition("Other.Health"),
                        item_definition("Other.InternalEffect", effects=[cash_effect(external=False)]),
                        item_definition("Other.FixedCash", effects=[cash_effect(formula="Fixed.Cash")]),
                        item_definition("Other.Ammo", effects=[cash_effect(attribute="Ammo.Count")])]
        for definition in definitions:
            with self.subTest(path=definition.path):
                old = self.wallet
                self.pickup(definition)
                self.assertEqual(self.wallet - old, 26322)

    def test_cash_formula_uses_experience_level(self):
        self.pickup(item_definition("GD_Currency.A_Item.Currency"), gain=100, stage=85, exp_level=1)
        self.assertEqual(self.wallet, 1_000_100)

    def test_small_pickup_keeps_one_dollar_minimum(self):
        self.pickup(item_definition("GD_Currency.A_Item.Currency"), gain=100)
        self.assertEqual(self.wallet, 1_000_001)

    def test_successful_pickups_are_silent(self):
        for _ in range(50):
            self.pickup(item_definition("GD_Currency.A_Item.Currency"))
        self.assertEqual(sdk.logging.info.call_count, 0)
        self.assertEqual(sdk.logging.error.call_count, 0)

    def test_unknown_cash_pickup_is_reported_once_and_not_scaled(self):
        item = item_definition("Unknown.Cash")
        for _ in range(20):
            before = self.wallet
            self.pickup(item, gain=12345)
            self.assertEqual(self.wallet - before, 12345)
        self.assertEqual(sdk.logging.info.call_count, 1)
        message = sdk.logging.info.call_args.args[0]
        self.assertIn("item=Unknown.Cash", message)
        self.assertIn("gain=12345", message)

    def test_problems_are_deduplicated_and_have_a_global_limit(self):
        for _ in range(100):
            mod.report_problem("repeated error", "Failure", error=True)
        self.assertEqual(sdk.logging.error.call_count, 1)
        for number in range(100):
            mod.report_problem(f"unknown {number}", "Unknown cash")
        self.assertEqual(sdk.logging.info.call_count + sdk.logging.error.call_count, mod.MAX_DIAGNOSTICS)

    def mission(self, locked=True):
        return Object(path="Example.Mission", GameStage=85, bGameStageLocked=locked,
                      Reward=Object(CurrencyRewardType=credits),
                      AlternativeReward=Object(CurrencyRewardType=1))

    def test_mission_reward_and_unlock_state_restore(self):
        for locked in (True, False):
            mission = self.mission(locked)
            func = lambda **_: round(200 * 1.12 ** (mission.GameStage if mission.bGameStageLocked else 85))
            result = mod.mission_reward_pre(mission, Object(InWPC=self.pc, bGetAltReward=False), None, func)
            self.assertEqual(result, (Block, 224))
            self.assertEqual((mission.GameStage, mission.bGameStageLocked, self.pc.Pawn.GameStage), (85, locked, 85))
        self.assertFalse(sdk.logging.info.called)

    def test_optional_credits_cap_without_changing_primary_currency(self):
        mission = self.mission()
        mission.Reward.CurrencyRewardType = 1
        args = Object(InWPC=self.pc, ReturnValue=0,
                      _type=Object(_properties=lambda: [Object(Name="InWPC"), Object(Name="ReturnValue")]))
        func = lambda InWPC: round(200 * 1.12 ** mission.GameStage)
        self.assertEqual(mod.optional_mission_cash_pre(mission, args, None, func), (Block, 224))
        self.assertEqual(mission.Reward.CurrencyRewardType, 1)
        self.assertEqual(mission.GameStage, 85)
        self.assertFalse(sdk.logging.error.called)

    def test_preview_exception_restores_mission_and_player(self):
        mission = self.mission(False)
        def func(**_):
            if self.pc.Pawn.GameStage == 1:
                raise RuntimeError("native preview failed")
            return 1000
        self.assertIsNone(mod.preview_mission_cash(mission, self.pc, func, {}))
        self.assertEqual((mission.GameStage, mission.bGameStageLocked, self.pc.Pawn.GameStage), (85, False, 85))

    def test_lock_preview_exception_restores_state(self):
        mission = self.mission(False)
        def func(**_):
            if mission.bGameStageLocked:
                raise RuntimeError("native preview failed")
            return 1000
        self.assertIsNone(mod.preview_mission_cash(mission, self.pc, func, {}))
        self.assertEqual((mission.GameStage, mission.bGameStageLocked, self.pc.Pawn.GameStage), (85, False, 85))

    def test_zero_and_other_currency_rewards_are_untouched(self):
        mission = self.mission()
        func = Mock(return_value=0)
        self.assertIsNone(mod.preview_mission_cash(mission, self.pc, func, {}))
        self.assertEqual(func.call_count, 1)
        self.assertIsNone(mod.mission_reward_pre(mission, Object(InWPC=self.pc, bGetAltReward=True), None, func))
        self.assertEqual(func.call_count, 1)

    def test_inventory_refunds_and_non_credit_prices_skip_preview(self):
        for definition, currency in [(item_definition("GD_RatShared.Pools.Item_RatShared_StolenMoney"), 0),
                                     (item_definition("Other.Token"), 2)]:
            inventory = Object(DefinitionData=Object(ItemDefinition=definition),
                               GetCurrencyTypeInventoryIsValuedIn=lambda: currency,
                               CreateItemFromDef=Mock())
            mod.cap_inventory_value(inventory, self.pc.Pawn, "test")
            inventory.CreateItemFromDef.assert_not_called()

    def test_weapon_preview_caps_price_without_changing_real_gear(self):
        # Weapon definitions have WeaponTypeDefinition, not ItemDefinition.
        data = Object(GameStage=85, ManufacturerGradeIndex=85,
                      WeaponTypeDefinition=Object(path="Weapon.Pistol"))
        inventory = Object(Class=Object(Name="WillowWeapon"), DefinitionData=data, value=7837246,
                           GetCurrencyTypeInventoryIsValuedIn=lambda: credits)
        inventory.GetMonetaryValue = lambda: inventory.value
        inventory.OverrideMonetaryValue = lambda NewMonetaryValue: setattr(inventory, "value", NewMonetaryValue)
        def preview(**kwargs):
            copied = kwargs["NewWeaponDef"]
            self.assertEqual((copied.GameStage, copied.ManufacturerGradeIndex), (1, 1))
            return Object(DefinitionData=copied, GetMonetaryValue=lambda: 500)
        inventory.CreateWeaponFromDef = Mock(side_effect=preview)
        mod.cap_inventory_value(inventory, self.pc.Pawn, "test")
        self.assertEqual(inventory.value, 500)
        self.assertEqual((data.GameStage, data.ManufacturerGradeIndex), (85, 85))
        mod.cap_inventory_value(inventory, self.pc.Pawn, "test")
        inventory.CreateWeaponFromDef.assert_called_once()
        mod.on_disable()
        self.assertEqual(inventory.value, 7837246)

    def test_respec_and_credit_slot_cost_use_level_one(self):
        self.assertEqual(mod.CEILING, 1)
        self.assertEqual(mod.RESPEC_CAP, 112)
        self.assertEqual(mod.respec_cost_pre(None, None, None, lambda: 10000), (Block, 112))
        self.assertEqual(mod.respec_cost_pre(None, None, None, lambda: 50), (Block, 50))
        actor = Object(GameStage=85, CostsToUseAmount=[0])
        mod._slot_actors[actor._get_address()] = WeakPointer(actor)
        args = Object(ChangeType="CHANGE_Enable", CostType="CURRENCY_Credits", CostAmount=732442, UsedType=0)
        def cost(**kwargs):
            actor.CostsToUseAmount[0] = kwargs["CostAmount"]
        self.assertIs(mod.slot_cost_pre(actor, args, None, cost), Block)
        self.assertEqual(actor.CostsToUseAmount[0], 54)
        args.CostType = "CURRENCY_Eridium"
        self.assertIsNone(mod.slot_cost_pre(actor, args, None, cost))

    def test_optional_hook_registers_and_unregisters(self):
        mod.on_enable()
        expected = "WillowGame.MissionDefinition:GetOptionalCreditReward"
        self.assertTrue(any(path == expected for path, _, _ in mod._dynamic_hooks))
        removed_probes = {"WillowGame.WillowPlayerReplicationInfo:AddCurrencyOnHand",
                          "WillowGame.WillowPlayerController:ScriptAnnounceCreditGain",
                          "WillowGame.StatusMenuExGFxMovie:SetRewardsTotalCredits"}
        self.assertFalse(any(path in removed_probes for path, _, _ in mod._dynamic_hooks))
        mod._slot_original_costs.clear()
        mod.on_disable()
        self.assertFalse(mod._dynamic_hooks)
        self.assertFalse(mod._cash_definitions)
        self.assertTrue(any(call.args[0] == expected for call in hooks.remove_hook.call_args_list))
        self.assertFalse(sdk.logging.info.called)
        self.assertFalse(sdk.logging.error.called)


if __name__ == "__main__":
    unittest.main()
