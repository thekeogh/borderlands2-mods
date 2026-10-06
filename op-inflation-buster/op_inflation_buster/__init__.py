"""OP inflation buster: price cash economy at the configured level."""

from copy import copy
from typing import Any

import unrealsdk
from mods_base import build_mod, get_pc
from unrealsdk import logging
from unrealsdk.hooks import Block, Type, prevent_hooking_direct_calls
from unrealsdk.unreal import BoundFunction, UObject, WeakPointer, WrappedStruct


CEILING = 1
VANILLA_PRICE_GROWTH = 1.12
RESPEC_CAP = int(100 * VANILLA_PRICE_GROWTH ** CEILING)
CASH_ITEM_DEFINITIONS = {
    "GD_Currency.A_Item.Currency",
    "GD_Currency.A_Item.Currency_Big",
    "GD_Currency.A_Item.Currency_Crystal",
    "GD_Skeleton_Crystal.A_Item.Currency_CrystalBones",
}
# These grant fixed money or return money already taken from the player.
UNSCALED_CASH_DEFINITIONS = {
    "GD_RatShared.Pools.Item_RatShared_StolenMoney",
    "GD_Allium_GrandmaData.A_Item.CurrencyOneDollar",
    "GD_Z3_ChosenOneData.ItemDefs.ID_MO_ChosenOne_Cash",
}
CASH_PICKUP_FORMULA = "GD_Economy.CashPickups.Init_CashPickupCalc"
CREDITS_ATTRIBUTE = "D_Attributes.Currency.CreditsOnHand"
MAX_DIAGNOSTICS = 8
_dynamic_hooks: list[tuple[str, Type, str]] = []
_touched: dict[int, tuple[WeakPointer[UObject], int]] = {}
_attempted: dict[int, WeakPointer[UObject]] = {}
_in_progress: set[int] = set()
_reports: dict[str, int] = {}
_last_vendor: WeakPointer[UObject] | None = None
_slot_actors: dict[int, WeakPointer[UObject]] = {}
_slot_original_costs: dict[int, tuple[WeakPointer[UObject], int, Any, Any, Any]] = {}
_cash_before: dict[int, tuple[WeakPointer[UObject], int, int, bool]] = {}
_cash_definitions: dict[int, tuple[WeakPointer[UObject], bool]] = {}


def report_problem(key: str, message: str, *, error: bool = False) -> None:
    """Report each problem once, with a small total budget per enabled session."""
    if key in _reports or len(_reports) >= MAX_DIAGNOSTICS:
        return
    _reports[key] = 1
    emit = logging.error if error else logging.info
    emit(f"[OP inflation buster] {message}")


def is_scaled_cash_definition(item: UObject) -> bool:
    """Recognize level-scaled cash effects, including matching DLC/mod pickups."""
    path = item._path_name()
    if path in UNSCALED_CASH_DEFINITIONS:
        return False
    if item.FormOfCurrency != unrealsdk.find_enum("ECurrencyType").CURRENCY_Credits:
        return False
    if path in CASH_ITEM_DEFINITIONS:
        return True
    address = item._get_address()
    cached = _cash_definitions.get(address)
    if cached is not None and cached[0]() == item:
        return cached[1]
    scaled = False
    for effect in getattr(item, "AttributeSlotEffects", ()):
        attribute = effect.AttributeToModify
        if not effect.bExternalSlot or attribute is None or attribute._path_name() != CREDITS_ATTRIBUTE:
            continue
        for value in (effect.BaseModifierValue, effect.PerGradeUpgrade):
            formula = value.InitializationDefinition
            if formula is not None and formula._path_name() == CASH_PICKUP_FORMULA:
                scaled = True
                break
        if scaled:
            break
    _cash_definitions[address] = (WeakPointer(item), scaled)
    return scaled


def interactive_object_probe(
    actor: UObject,
    args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    try:
        definition = getattr(args, "Definition", None)
        if definition is None:
            definition = getattr(actor, "Definition", None)
        if definition is not None and "slotmachine" in definition._path_name().lower():
            _slot_actors[actor._get_address()] = WeakPointer(actor)
    except Exception as exc:
        report_problem("slot tracking", f"Interactive object probe failed: {exc!r}", error=True)
    return None


def cash_use_probe(
    obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
    phase: str,
) -> None:
    try:
        inventory = obj if obj.Class.Name == "WillowUsableItem" else getattr(obj, "Inventory", None)
        if inventory is None or inventory.Class.Name != "WillowUsableItem":
            return None
        definition = inventory.DefinitionData
        item = definition.ItemDefinition
        if item._path_name() in UNSCALED_CASH_DEFINITIONS:
            return None
        if item.FormOfCurrency != unrealsdk.find_enum("ECurrencyType").CURRENCY_Credits:
            return None
        pc = get_pc()
        wallet = None
        if pc is not None and pc.PlayerReplicationInfo is not None:
            credits = unrealsdk.find_enum("ECurrencyType").CURRENCY_Credits
            wallet = int(pc.PlayerReplicationInfo.GetCurrencyOnHand(credits))
        if wallet is not None:
            address = inventory._get_address()
            if phase == "PRE":
                # CurrencyItemLevel resolves ExpLevel in the game's cash formula.
                stage = int(getattr(inventory, "ExpLevel", definition.GameStage))
                _cash_before[address] = (WeakPointer(inventory), wallet, stage, is_scaled_cash_definition(item))
            else:
                before = _cash_before.pop(address, None)
                if before is not None and before[0]() == inventory:
                    old_wallet, stage, scaled = before[1:]
                    gain = wallet - old_wallet
                    if stage > CEILING and gain > 0 and not scaled:
                        path = item._path_name()
                        report_problem(
                            f"unknown cash {path}",
                            f"Unrecognized cash pickup: item={path} level={stage} "
                            f"gain={gain} wallet={old_wallet}->{wallet}",
                        )
                    elif stage > CEILING and gain > 0:
                        capped_gain = max(1, round(gain * VANILLA_PRICE_GROWTH ** (CEILING - stage)))
                        pc.PlayerReplicationInfo.AddCurrencyOnHand(credits, capped_gain - gain)
    except Exception as exc:
        report_problem("cash pickup", f"Cash use probe failed: {exc!r}", error=True)
    return None


def cash_use_pre(obj: UObject, args: WrappedStruct, ret: Any, func: BoundFunction) -> None:
    return cash_use_probe(obj, args, ret, func, "PRE")


def cash_use_post(obj: UObject, args: WrappedStruct, ret: Any, func: BoundFunction) -> None:
    return cash_use_probe(obj, args, ret, func, "POST")


def slot_cost_pre(
    actor: UObject,
    args: WrappedStruct,
    _ret: Any,
    func: BoundFunction,
) -> type[Block] | None:
    pointer = _slot_actors.get(actor._get_address())
    if pointer is None or pointer() != actor:
        return None
    try:
        if "CHANGE_Enable" not in repr(args.ChangeType) or "CURRENCY_Credits" not in repr(args.CostType):
            return None
        stage = int(actor.GameStage)
        original_cost = int(args.CostAmount)
        if stage <= CEILING or original_cost <= 0:
            return None
        capped_cost = max(1, round(original_cost * VANILLA_PRICE_GROWTH ** (CEILING - stage)))
        with prevent_hooking_direct_calls():
            func(
                ChangeType=args.ChangeType,
                CostType=args.CostType,
                CostAmount=capped_cost,
                UsedType=args.UsedType,
            )
        actual_cost = int(actor.CostsToUseAmount[0])
        if actual_cost != capped_cost:
            report_problem(
                "slot override", f"Slot cost override returned {actual_cost}, expected {capped_cost}", error=True,
            )
            return None
        _slot_original_costs[actor._get_address()] = (
            WeakPointer(actor), original_cost, args.ChangeType, args.CostType, args.UsedType
        )
        return Block
    except Exception as exc:
        report_problem("slot cost", f"Slot cost cap failed: {exc!r}", error=True)
        return None


def respec_cost_pre(
    _pc: UObject,
    _args: WrappedStruct,
    _ret: Any,
    func: BoundFunction,
) -> tuple[type[Block], int] | None:
    try:
        with prevent_hooking_direct_calls():
            vanilla_cost = int(func())
        capped_cost = min(vanilla_cost, RESPEC_CAP)
        return Block, capped_cost
    except Exception as exc:
        report_problem("respec", f"Respec cost cap failed: {exc!r}", error=True)
        return None


def mission_reward_pre(
    mission: UObject,
    args: WrappedStruct,
    _ret: Any,
    func: BoundFunction,
) -> tuple[type[Block], int] | None:
    """Ask the game's reward formula for the same mission at the cash ceiling."""
    try:
        reward = mission.AlternativeReward if args.bGetAltReward else mission.Reward
        if reward.CurrencyRewardType != unrealsdk.find_enum("ECurrencyType").CURRENCY_Credits:
            return None
        call_args = {"InWPC": args.InWPC, "bGetAltReward": args.bGetAltReward}
        return preview_mission_cash(mission, args.InWPC, func, call_args)
    except Exception as exc:
        report_problem("mission preview", f"Mission cash preview failed: {exc!r}", error=True)
    return None


def optional_mission_cash_pre(
    mission: UObject,
    args: WrappedStruct,
    _ret: Any,
    func: BoundFunction,
) -> tuple[type[Block], int] | None:
    """Cap extra credits on missions whose main reward is another currency."""
    try:
        call_args = {
            str(field.Name): getattr(args, str(field.Name))
            for field in args._type._properties()
            if str(field.Name) != "ReturnValue"
        }
        pc = next((value for value in call_args.values() if hasattr(value, "Pawn")), None)
        return preview_mission_cash(mission, pc, func, call_args)
    except Exception as exc:
        report_problem("optional mission preview", f"Optional mission cash preview failed: {exc!r}", error=True)
    return None


def preview_mission_cash(
    mission: UObject,
    pc: UObject | None,
    func: BoundFunction,
    call_args: dict[str, Any],
) -> tuple[type[Block], int] | None:
    try:
        stage = int(mission.GameStage)
        if stage <= CEILING:
            return None
        with prevent_hooking_direct_calls():
            vanilla = int(func(**call_args))
            if vanilla <= 0:
                return None
            try:
                mission.GameStage = CEILING
                ceiling_value = int(func(**call_args))
            finally:
                mission.GameStage = stage
            player_stage_preview = None
            if ceiling_value >= vanilla:
                pawn = getattr(pc, "Pawn", None)
                if pawn is not None:
                    player_stage = int(pawn.GameStage)
                    if player_stage > CEILING:
                        try:
                            pawn.GameStage = CEILING
                            player_stage_preview = int(func(**call_args))
                        finally:
                            pawn.GameStage = player_stage
            locked_stage_preview = None
            if ceiling_value >= vanilla and not bool(mission.bGameStageLocked):
                original_lock = bool(mission.bGameStageLocked)
                try:
                    mission.GameStage = CEILING
                    mission.bGameStageLocked = True
                    locked_stage_preview = int(func(**call_args))
                finally:
                    mission.bGameStageLocked = original_lock
                    mission.GameStage = stage
        capped = next(
            (
                value for value in (ceiling_value, player_stage_preview, locked_stage_preview)
                if value is not None and 0 < value < vanilla
            ),
            None,
        )
        if capped is not None:
            return Block, capped
        report_problem(
            f"mission unchanged {mission._path_name()}",
            f"Mission cash unchanged: {mission._path_name()} stage={stage} vanilla={vanilla}",
        )
    except Exception as exc:
        report_problem("mission preview", f"Mission cash preview failed: {exc!r}", error=True)
    return None


def cap_inventory_value(inventory: UObject, owner: UObject, source: str) -> None:
    """Value a temporary copy at the cash ceiling and override only money."""
    try:
        if inventory.GetCurrencyTypeInventoryIsValuedIn() != unrealsdk.find_enum("ECurrencyType").CURRENCY_Credits:
            return None
        definition = inventory.DefinitionData
        item = getattr(definition, "ItemDefinition", None)
        if item is not None and item._path_name() in UNSCALED_CASH_DEFINITIONS:
            return None
        stage = int(definition.GameStage)
        grade = int(definition.ManufacturerGradeIndex)
    except (AttributeError, TypeError, ValueError):
        return None
    if stage <= CEILING and grade <= CEILING:
        return None

    address = inventory._get_address()
    if address in _in_progress:
        return None
    if address in _attempted and _attempted[address]() == inventory:
        return None
    _attempted[address] = WeakPointer(inventory)
    _in_progress.add(address)

    try:
        original_value = int(inventory.GetMonetaryValue())
        if original_value <= 0:
            return None
        ceiling_definition = copy(definition)
        ceiling_definition.GameStage = min(stage, CEILING)
        ceiling_definition.ManufacturerGradeIndex = min(grade, CEILING)
        if inventory.Class.Name == "WillowWeapon":
            preview = inventory.CreateWeaponFromDef(
                NewWeaponDef=ceiling_definition,
                PlayerOwner=owner,
                bForceSelectNameParts=True,
            )
        else:
            preview = inventory.CreateItemFromDef(
                NewItemDef=ceiling_definition,
                PlayerOwner=owner,
                NewQuantity=1,
                bForceSelectNameParts=True,
            )
        if preview is None:
            raise RuntimeError("cash-ceiling preview creation returned None")
        ceiling_value = int(preview.GetMonetaryValue())

        if ceiling_value > 0 and ceiling_value != original_value:
            inventory.OverrideMonetaryValue(NewMonetaryValue=ceiling_value)
            actual_value = int(inventory.GetMonetaryValue())
            if actual_value != ceiling_value:
                inventory.OverrideMonetaryValue(NewMonetaryValue=original_value)
                raise RuntimeError(f"override returned {actual_value}, expected {ceiling_value}")
            _touched[address] = (WeakPointer(inventory), original_value)
    except Exception as exc:
        report_problem("inventory preview", f"Cash-ceiling preview failed: source={source} error={exc!r}", error=True)
    finally:
        _in_progress.discard(address)
    return None


def cap_backpack(pc: UObject) -> None:
    """Value loaded backpack items only while a vendor UI is active."""
    try:
        owner = pc.Pawn
        manager = pc.GetPawnInventoryManager()
        if owner is None or manager is None:
            return
        for item in list(manager.Backpack):
            if item is not None:
                cap_inventory_value(item, owner, "backpack")
    except Exception as exc:
        report_problem("backpack", f"Backpack scan failed: {exc!r}", error=True)


def vendor_movie_start(
    _movie: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    try:
        pc = get_pc()
        if pc is not None:
            cap_backpack(pc)
    except Exception as exc:
        report_problem("vendor start", f"Vendor start scan failed: {exc!r}", error=True)
    return None


def item_card_pre(
    _card: UObject,
    args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    try:
        pc = get_pc()
        if pc is not None and pc.Pawn is not None and args.InventoryItem is not None:
            cap_inventory_value(args.InventoryItem, pc.Pawn, "item card")
    except Exception as exc:
        report_problem("item card", f"Item card value failed: {exc!r}", error=True)
    return None


def item_of_the_day_focus_pre(
    movie: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    try:
        data = movie.ItemOfTheDayData
        item = data.Item
        pc = get_pc()
        if pc is None or pc.Pawn is None or item is None:
            return None
        cached_price = int(data.Price)
        cap_inventory_value(item, pc.Pawn, "item of the day")
        vendor = _last_vendor() if _last_vendor is not None else None
        expected_price = None
        if vendor is not None:
            expected_price = int(vendor.GetSellingPriceForInventory(item, pc, 1))
            if expected_price > 0 and cached_price > expected_price:
                data.Price = expected_price
    except Exception as exc:
        report_problem("item of the day", f"Item of the day focus probe failed: {exc!r}", error=True)
    return None


def vendor_price_pre(
    vendor: UObject,
    args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    global _last_vendor
    try:
        pc = args.WPC
        _last_vendor = WeakPointer(vendor)
        cap_inventory_value(args.InventoryForSale, pc.Pawn, "vendor")
        cap_backpack(pc)
    except (AttributeError, TypeError, ValueError):
        pass
    return None


def on_enable() -> None:
    hooks = (
        ("WillowGame.WillowUsableItem:GivenTo", Type.PRE, "cash_before", cash_use_pre),
        ("WillowGame.WillowUsableItem:GivenTo", Type.POST, "cash_after", cash_use_post),
        ("WillowGame.WillowPlayerController:GetSkillTreeResetCost", Type.PRE, "respec", respec_cost_pre),
        ("WillowGame.MissionDefinition:GetCurrencyReward", Type.PRE, "mission", mission_reward_pre),
        ("WillowGame.MissionDefinition:GetOptionalCreditReward", Type.PRE, "optional_mission_cash", optional_mission_cash_pre),
        ("WillowGame.WillowInteractiveObject:InitializeFromDefinition", Type.PRE, "slot_actor", interactive_object_probe),
        ("WillowGame.WillowInteractiveObject:Behavior_ChangeUsabilityCost", Type.PRE, "slot_cost", slot_cost_pre),
        ("WillowGame.VendingMachineExGFxMovie:Start", Type.PRE, "backpack", vendor_movie_start),
        ("WillowGame.ItemCardGFxObject:SetItemCardEx", Type.PRE, "item_card", item_card_pre),
        ("WillowGame.VendingMachineExGFxMovie:SwitchToItemOfTheDay", Type.PRE, "item_of_the_day", item_of_the_day_focus_pre),
    )
    for path, hook_type, name, callback in hooks:
        identifier = f"op_inflation_buster.{name}"
        try:
            if unrealsdk.hooks.add_hook(path, hook_type, identifier, callback):
                _dynamic_hooks.append((path, hook_type, identifier))
            else:
                report_problem(f"hook {path}", f"Hook unavailable: {path}", error=True)
        except Exception as exc:
            report_problem(f"hook {path}", f"Hook failed: {path}: {exc!r}", error=True)

    for class_name in ("WillowPawn", "WillowVendingMachineBase", "WillowVendingMachine"):
        path = f"WillowGame.{class_name}:GetSellingPriceForInventory"
        identifier = f"op_inflation_buster.vendor.{class_name}"
        try:
            if unrealsdk.hooks.add_hook(path, Type.PRE, identifier, vendor_price_pre):
                _dynamic_hooks.append((path, Type.PRE, identifier))
        except Exception as exc:
            report_problem(f"hook {path}", f"Vendor hook failed: {path}: {exc!r}", error=True)


def on_disable() -> None:
    global _last_vendor
    for path, hook_type, identifier in _dynamic_hooks:
        unrealsdk.hooks.remove_hook(path, hook_type, identifier)
    _dynamic_hooks.clear()

    for pointer, original_cost, change_type, cost_type, used_type in _slot_original_costs.values():
        actor = pointer()
        if actor is None:
            continue
        try:
            actor.Behavior_ChangeUsabilityCost(
                ChangeType=change_type,
                CostType=cost_type,
                CostAmount=original_cost,
                UsedType=used_type,
            )
        except Exception as exc:
            report_problem("slot restore", f"Slot cost restore failed: {exc!r}", error=True)
    _slot_original_costs.clear()


    for pointer, original_value in _touched.values():
        inventory = pointer()
        if inventory is None:
            continue
        try:
            inventory.OverrideMonetaryValue(NewMonetaryValue=original_value)
        except Exception as exc:
            report_problem("inventory restore", f"Value restore failed: {exc!r}", error=True)
    _touched.clear()
    _cash_before.clear()
    _cash_definitions.clear()
    _attempted.clear()
    _in_progress.clear()
    _reports.clear()
    _last_vendor = None
    _slot_actors.clear()


build_mod()
