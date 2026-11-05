"""AVHM (Absolute Vault Hunter Mode) - Play UVHM from level 1 with sensible scaling."""

from __future__ import annotations

from typing import Any

from mods_base import (
    CoopSupport,
    DropdownOption,
    Game,
    RestartToDisable,
    build_mod,
    get_pc,
    hook,
)
from unrealsdk import find_all, find_object, load_package, logging
from unrealsdk.hooks import Block, Type, prevent_hooking_direct_calls

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PT3_TUNING_PATH = "GD_Playthrough3Tuning.Balance.BalanceMod_PT3"

STAGE_PACKAGES = (
    "GD_GameStages",
    "GD_Aster_GameStages",
    "GD_Anemone_GameStages",
    "GD_Iris_GameStages",
    "GD_Orchid_GameStages",
    "GD_Sage_GameStages",
    "GD_Allium_GameStages",
    "GD_Flax_GameStages",
    "GD_Lobelia_GameStages",
    "GD_Nasturtium_GameStages",
)

# NVHM: vanilla Normal mode multipliers (all 1x).
# TVHM: 2x health, everything else 1x.
# UVHM: vanilla UVHM multipliers from BalanceMod_PT3 (regen always disabled by this mod).
PROFILES: dict[str, dict[str, float]] = {
    "NVHM": dict(eh=1.0, bh=1.0, es=1.0, bs=1.0, ed=1.0, bd=1.0),
    "TVHM": dict(eh=2.0, bh=1.0, es=1.0, bs=1.0, ed=1.0, bd=1.0),
    "UVHM": dict(eh=4.0, bh=2.8, es=5.0, bs=3.5, ed=1.1, bd=1.1),
}

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

_orig_modifiers: list[dict[str, Any]] | None = None
_orig_stages: dict[str, list[dict[str, Any]]] = {}
_mission_locked: dict[str, int] = {}
_tuning_applied = False
_ui_level_override: int | None = None
_ui_level_override_depth: int = 0

# ---------------------------------------------------------------------------
# Options
# ---------------------------------------------------------------------------


def _on_option_change(option: Any, _val: Any) -> None:
    if option.mod and option.mod.is_enabled:
        _apply_tuning()
        logging.info(f"[AVHM] Option changed, tuning reapplied")


scaling_opt = DropdownOption(
    "scaling_profile",
    "TVHM",
    list(PROFILES.keys()),
    display_name="Scaling Profile",
    description=(
        "NVHM: vanilla Normal mode multipliers (1x everything). "
        "TVHM: 2x enemy health, normal shields and damage. "
        "UVHM: vanilla UVHM multipliers (4x health, 5x shields). "
        "Enemy health regen is always disabled regardless of profile."
    ),
    on_change=_on_option_change,
)
# Health regen is always disabled — no toggle exposed.

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _profile() -> dict[str, float]:
    return PROFILES.get(scaling_opt.value, PROFILES["TVHM"])


def _player_level() -> int:
    pc = get_pc(possibly_loading=True)
    if pc is None:
        return 1
    try:
        return max(1, int(pc.PlayerReplicationInfo.ExpLevel))
    except (AttributeError, TypeError):
        pass
    try:
        return max(1, int(pc.GetCachedSaveGame().ExpLevel))
    except (AttributeError, TypeError):
        return 1


def _obj_path(obj: Any) -> str:
    try:
        return str(obj._path_name())
    except Exception:
        return str(obj)


def _get_mission_def_from_args(args: Any) -> Any | None:
    if args is None:
        return None
    for attr in ("Mission", "MissionDef", "MissionDefinition"):
        mdef = getattr(args, attr, None)
        if mdef is not None:
            return mdef
    return None


def _get_mission_def_from_obj(obj: Any) -> Any | None:
    if obj is None:
        return None
    for attr in ("Mission", "MissionDef", "MissionDefinition", "DisplayedMission"):
        mdef = getattr(obj, attr, None)
        if mdef is not None:
            return mdef
    return None


def _resolve_mission_def(obj: Any = None, args: Any = None) -> Any | None:
    mdef = _get_mission_def_from_args(args)
    if mdef is not None:
        return mdef
    mdef = _get_mission_def_from_obj(obj)
    if mdef is not None:
        return mdef
    # Fallback: active mission from tracker
    pc = get_pc(possibly_loading=True)
    if pc is None:
        return None
    try:
        tracker = pc.WorldInfo.GRI.MissionTracker
        return getattr(tracker, "ActiveMission", None)
    except (AttributeError, TypeError):
        return None


def _snap_val(v: Any) -> dict[str, Any]:
    return dict(
        c=v.BaseValueConstant, a=v.BaseValueAttribute,
        i=v.InitializationDefinition, s=v.BaseValueScaleConstant,
    )


def _restore_val(v: Any, s: dict[str, Any]) -> None:
    v.BaseValueConstant = s["c"]
    v.BaseValueAttribute = s["a"]
    v.InitializationDefinition = s["i"]
    v.BaseValueScaleConstant = s["s"]


def _set_flat(v: Any, level: int) -> None:
    v.BaseValueConstant = float(level)
    v.BaseValueAttribute = None
    v.InitializationDefinition = None
    v.BaseValueScaleConstant = 1.0


# ---------------------------------------------------------------------------
# PT3 Tuning — enemy multipliers + regen
# ---------------------------------------------------------------------------


def _get_tuning() -> Any | None:
    try:
        load_package("GD_Playthrough3Tuning")
    except Exception:
        pass
    for cls in ("BalanceModifierDefinition", "Object"):
        try:
            obj = find_object(cls, PT3_TUNING_PATH)
            if obj is not None:
                return obj
        except Exception:
            continue
    return None


def _apply_tuning() -> None:
    global _orig_modifiers, _tuning_applied

    tuning = _get_tuning()
    if tuning is None:
        logging.error("[AVHM] PT3 tuning object not found!")
        return

    if _orig_modifiers is None:
        _orig_modifiers = []
        for m in tuning.BalanceModifiers:
            _orig_modifiers.append(dict(
                min=m.MinEffectiveLevel,
                eh=m.EnemyHealthMultiplier, bh=m.BadassEnemyHealthMultiplier,
                es=m.EnemyShieldStrengthMultiplier, bs=m.BadassEnemyShieldStrengthMultiplier,
                ed=m.EnemyDamageMultiplier, bd=m.BadassEnemyDamageMultiplier,
            ))
        logging.info(f"[AVHM] Snapshotted {len(_orig_modifiers)} balance modifiers "
                     f"(orig MinEffectiveLevel={_orig_modifiers[0]['min']})")

    p = _profile()
    for i, m in enumerate(tuning.BalanceModifiers):
        if i == 0:
            m.MinEffectiveLevel = 1
        m.EnemyHealthMultiplier = p["eh"]
        m.BadassEnemyHealthMultiplier = p["bh"]
        m.EnemyShieldStrengthMultiplier = p["es"]
        m.BadassEnemyShieldStrengthMultiplier = p["bs"]
        m.EnemyDamageMultiplier = p["ed"]
        m.BadassEnemyDamageMultiplier = p["bd"]
        _kill_regen_effect(m)

    _kill_regen_formulas()

    _tuning_applied = True
    logging.info(f"[AVHM] Tuning applied — MinEffectiveLevel=1, health={p['eh']}x")


def _restore_tuning() -> None:
    global _tuning_applied
    if not _tuning_applied or _orig_modifiers is None:
        return
    tuning = _get_tuning()
    if tuning is None:
        return
    for m, s in zip(tuning.BalanceModifiers, _orig_modifiers):
        m.MinEffectiveLevel = s["min"]
        m.EnemyHealthMultiplier = s["eh"]
        m.BadassEnemyHealthMultiplier = s["bh"]
        m.EnemyShieldStrengthMultiplier = s["es"]
        m.BadassEnemyShieldStrengthMultiplier = s["bs"]
        m.EnemyDamageMultiplier = s["ed"]
        m.BadassEnemyDamageMultiplier = s["bd"]
    _tuning_applied = False


def _kill_regen_effect(modifier: Any) -> None:
    for eff in getattr(modifier, "AttributeEffectsForSpawnedEnemies", ()):
        attr = getattr(eff, "AttributeToModify", None)
        if attr and "HealthPassiveRegenerationRate" in str(attr):
            v = eff.BaseModifierValue
            v.BaseValueConstant = 0.0
            v.BaseValueAttribute = None
            v.InitializationDefinition = None
            v.BaseValueScaleConstant = 0.0
            break


def _kill_regen_formulas() -> None:
    try:
        load_package("GD_Playthrough3Tuning")
    except Exception:
        pass
    for obj in find_all("AttributeInitializationDefinition"):
        if "Init_EnemyHealthRegenFormula" not in _obj_path(obj):
            continue
        formula = getattr(obj, "ValueFormula", None)
        if formula is None:
            continue
        if hasattr(formula, "bEnabled"):
            formula.bEnabled = False
        for part in ("Multiplier", "Level", "Power", "Offset"):
            val = getattr(formula, part, None)
            if val and hasattr(val, "BaseValueConstant"):
                _set_flat(val, 0)


# ---------------------------------------------------------------------------
# Game Stage Scaling — zone levels
# ---------------------------------------------------------------------------


def _is_pt3_balance(balance: Any) -> bool:
    p = _obj_path(balance)
    return "GameStages" in p and (".Balance.Balance_P3" in p or "_P3_GameBalance" in p)


def _find_pt3_balances() -> list[Any]:
    for pkg in STAGE_PACKAGES:
        try:
            load_package(pkg)
        except Exception:
            pass
    seen: set[str] = set()
    result: list[Any] = []
    for b in find_all("GameBalanceDefinition"):
        if not _is_pt3_balance(b):
            continue
        p = _obj_path(b)
        if p not in seen:
            seen.add(p)
            result.append(b)
    return result


def _apply_stages() -> None:
    level = _player_level()
    count = 0
    for balance in _find_pt3_balances():
        p = _obj_path(balance)
        if p not in _orig_stages:
            _orig_stages[p] = [
                dict(mn=_snap_val(r.MinDefaultGameStage),
                     mx=_snap_val(r.MaxDefaultGameStage),
                     bp=r.bSpecifyBoostAbovePlayer,
                     bv=_snap_val(r.GameStageIncreaseAbovePlayer))
                for r in getattr(balance, "BalanceByRegion", ())
            ]
        for r in getattr(balance, "BalanceByRegion", ()):
            _set_flat(r.MinDefaultGameStage, level)
            _set_flat(r.MaxDefaultGameStage, level)
            r.bSpecifyBoostAbovePlayer = False
            _set_flat(r.GameStageIncreaseAbovePlayer, 0)
            # Also scale mission overrides within the region
            for mo in getattr(r, "MissionOverrides", ()):
                _set_flat(mo.MinGameStage, level)
                _set_flat(mo.MaxGameStage, level)
        count += 1
    logging.info(f"[AVHM] Scaled {count} PT3 zone balances to level {level}")


def _restore_stages() -> None:
    for balance in _find_pt3_balances():
        snap = _orig_stages.get(_obj_path(balance))
        if snap is None:
            continue
        for r, s in zip(getattr(balance, "BalanceByRegion", ()), snap):
            _restore_val(r.MinDefaultGameStage, s["mn"])
            _restore_val(r.MaxDefaultGameStage, s["mx"])
            r.bSpecifyBoostAbovePlayer = s["bp"]
            _restore_val(r.GameStageIncreaseAbovePlayer, s["bv"])


# ---------------------------------------------------------------------------
# Mission Level Locking
# ---------------------------------------------------------------------------


def _mkey(mdef: Any) -> str | None:
    return _obj_path(mdef) if mdef is not None else None


def _lock_mission(mdef: Any, level: int | None = None) -> int:
    key = _mkey(mdef)
    if key is None:
        return _player_level()
    lv = max(1, int(level if level is not None else _player_level()))
    _mission_locked[key] = lv
    return lv


def _display_level(mdef: Any) -> int:
    key = _mkey(mdef)
    locked = _mission_locked.get(key) if key else None
    return locked if locked is not None else _player_level()


def _reward_level(mdef: Any) -> int:
    key = _mkey(mdef)
    locked = _mission_locked.get(key) if key else None
    player = _player_level()
    return max(locked, player) if locked is not None else player


def _scale_mission_def(mdef: Any, level: int) -> None:
    if mdef is None:
        return
    for attr in ("GameStage", "ExpLevel"):
        if hasattr(mdef, attr):
            try:
                setattr(mdef, attr, level)
            except Exception:
                pass
    # Also scale the region object if present
    region = getattr(mdef, "GameStageRegion", None)
    if region is not None:
        _scale_region(region, level)


def _scale_region(region: Any, level: int) -> None:
    if region is None:
        return
    if hasattr(region, "bSpecifyBoostAbovePlayer"):
        region.bSpecifyBoostAbovePlayer = False
    for attr, target in (("MinGameStage", level), ("MaxGameStage", level),
                         ("MinDefaultGameStage", level), ("MaxDefaultGameStage", level),
                         ("GameStageIncreaseAbovePlayer", 0)):
        val = getattr(region, attr, None)
        if val is None:
            continue
        if hasattr(val, "BaseValueConstant"):
            _set_flat(val, target)
        else:
            try:
                setattr(region, attr, target)
            except Exception:
                pass
    for simple in ("GameStage", "ExpLevel", "Level"):
        if hasattr(region, simple):
            try:
                setattr(region, simple, level)
            except Exception:
                pass


def _sync_missions() -> None:
    pc = get_pc(possibly_loading=True)
    if pc is None:
        return
    try:
        pt = int(pc.GetCurrentPlaythrough())
    except (AttributeError, TypeError):
        return
    playthroughs = getattr(pc, "MissionPlaythroughs", None)
    if playthroughs is None or pt >= len(playthroughs):
        return
    player = _player_level()
    count = 0
    for attr in ("MissionList", "MissionData"):
        mlist = getattr(playthroughs[pt], attr, None)
        if mlist is None:
            continue
        for entry in mlist:
            mdef = _get_mission_def_from_args(entry)
            if mdef is None:
                continue
            gs = getattr(entry, "GameStage", None)
            if isinstance(gs, (int, float)) and gs > 0:
                # Cap at player level — vanilla UVHM saves have GameStage=50 for all missions.
                # min(saved, player) means a fresh Gibbed save (50,1)->1, a later session (5,8)->5.
                _lock_mission(mdef, min(int(gs), player))
                count += 1
    logging.info(f"[AVHM] Synced {count} mission levels from save (player_level={player})")


def _apply_all_mission_scaling() -> None:
    pc = get_pc(possibly_loading=True)
    if pc is None:
        return
    try:
        pt = int(pc.GetCurrentPlaythrough())
    except (AttributeError, TypeError):
        return
    playthroughs = getattr(pc, "MissionPlaythroughs", None)
    if playthroughs is None or pt >= len(playthroughs):
        return
    player = _player_level()
    for attr in ("MissionList", "MissionData"):
        mlist = getattr(playthroughs[pt], attr, None)
        if mlist is None:
            continue
        for entry in mlist:
            mdef = _get_mission_def_from_args(entry)
            if mdef is None:
                continue
            level = _display_level(mdef)
            for gs_attr in ("GameStage", "ExpLevel"):
                if hasattr(entry, gs_attr):
                    try:
                        setattr(entry, gs_attr, level)
                    except Exception:
                        pass
            _scale_mission_def(mdef, level)


# ---------------------------------------------------------------------------
# UI mission level override (for fanfare / reward screens)
# ---------------------------------------------------------------------------


def _push_ui_override(level: int) -> None:
    global _ui_level_override, _ui_level_override_depth
    _ui_level_override = level
    _ui_level_override_depth += 1


def _pop_ui_override() -> None:
    global _ui_level_override, _ui_level_override_depth
    if _ui_level_override_depth > 0:
        _ui_level_override_depth -= 1
    if _ui_level_override_depth <= 0:
        _ui_level_override_depth = 0
        _ui_level_override = None


def _patch_mission_ui(obj: Any = None, args: Any = None) -> int:
    """Resolve the mission, scale it, patch UI payloads, return the level."""
    mdef = _resolve_mission_def(obj, args)
    if mdef is not None:
        level = _display_level(mdef)
        _scale_mission_def(mdef, level)
    else:
        level = _player_level()

    # Patch level into all payload objects
    for target in (obj, args, mdef):
        _apply_level_to_payload(target, level)
    # Also patch nested data structs
    if args is not None:
        for sub in ("MissionData", "OutMissionData", "MissionStatusData",
                     "DisplayedMissionData", "MissionDisplayData"):
            _apply_level_to_payload(getattr(args, sub, None), level)
    if obj is not None:
        for sub in ("MissionData", "OutMissionData", "MissionStatusData",
                     "DisplayedMissionData", "MissionDisplayData"):
            _apply_level_to_payload(getattr(obj, sub, None), level)
    return level


def _apply_level_to_payload(payload: Any, level: int) -> None:
    if payload is None:
        return
    for attr in ("GameStage", "ExpLevel", "Level", "MissionLevel",
                 "RecommendedLevel", "RecommendedGameStage", "MinLevel", "MaxLevel"):
        if hasattr(payload, attr):
            try:
                setattr(payload, attr, level)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Full apply (called on spawn / map load)
# ---------------------------------------------------------------------------


def _full_apply() -> None:
    _apply_tuning()
    _apply_stages()
    _sync_missions()
    _apply_all_mission_scaling()


# ---------------------------------------------------------------------------
# Hooks — map load / spawn / menu
# ---------------------------------------------------------------------------


@hook("WillowGame.WillowPlayerController:SpawningProcessComplete", Type.POST)
def _on_spawn(*_: Any) -> None:
    logging.info("[AVHM] SpawningProcessComplete")
    _mission_locked.clear()
    _full_apply()


@hook("WillowGame.WillowPlayerController:WillowClientDisableLoadingMovie", Type.POST)
def _on_map_load(*_: Any) -> None:
    logging.info("[AVHM] Map loaded")
    _full_apply()


@hook("WillowGame.FrontendGFxMovie:NotifyAtMainMenu", Type.POST)
def _on_main_menu(*_: Any) -> None:
    logging.info("[AVHM] Main menu")
    _apply_tuning()
    _apply_stages()


# ---------------------------------------------------------------------------
# Hooks — scale enemies, vehicles, interactives, environment
# ---------------------------------------------------------------------------


@hook("WillowGame.WillowPawn:SetGameStage", Type.POST_UNCONDITIONAL)
@hook("WillowGame.WillowVehicle:SetGameStage", Type.POST_UNCONDITIONAL)
def _scale_pawn_stage(obj: Any, *_: Any) -> None:
    if "WillowPlayerPawn" in str(getattr(obj, "Class", "")):
        # When the player pawn's stage is set, re-apply zone + mission scaling
        _apply_stages()
        _apply_all_mission_scaling()
        return
    level = _player_level()
    with prevent_hooking_direct_calls():
        if hasattr(obj, "SetGameStage"):
            obj.SetGameStage(level)
        if hasattr(obj, "SetExpLevel"):
            obj.SetExpLevel(level)


@hook("WillowGame.WillowPawn:SetExpLevel", Type.POST_UNCONDITIONAL)
@hook("WillowGame.WillowVehicle:SetExpLevel", Type.POST_UNCONDITIONAL)
def _scale_pawn_exp(obj: Any, *_: Any) -> None:
    if "WillowPlayerPawn" in str(getattr(obj, "Class", "")):
        return
    level = _player_level()
    with prevent_hooking_direct_calls():
        if hasattr(obj, "SetGameStage"):
            obj.SetGameStage(level)
        if hasattr(obj, "SetExpLevel"):
            obj.SetExpLevel(level)


@hook("WillowGame.WillowInteractiveObject:SetGameStage", Type.POST_UNCONDITIONAL)
def _scale_interactive(obj: Any, *_: Any) -> None:
    level = _player_level()
    with prevent_hooking_direct_calls():
        if hasattr(obj, "SetGameStage"):
            obj.SetGameStage(level)
        if hasattr(obj, "SetExpLevel"):
            obj.SetExpLevel(level)


@hook("WillowGame.BehaviorVolume:InitializeAttributeStartingValues", Type.POST_UNCONDITIONAL)
def _scale_behavior_volume(obj: Any, *_: Any) -> None:
    level = _player_level()
    with prevent_hooking_direct_calls():
        if hasattr(obj, "SetGameStage"):
            obj.SetGameStage(level)
        if hasattr(obj, "SetExpLevel"):
            obj.SetExpLevel(level)


# ---------------------------------------------------------------------------
# Hooks — scale ALL inventory (loot drops, world pickups, vendors)
# ---------------------------------------------------------------------------


@hook("Engine.WillowInventory:ClientInitializeInventoryFromDefinition")
def _scale_inventory(obj: Any, args: Any, *_: Any) -> None:
    if not hasattr(args, "DefinitionData"):
        return

    # Don't rescale player-owned items
    owner = getattr(obj, "AdditionalQueryInterfaceSource", None)
    if owner is not None and "Player" in str(getattr(owner, "Class", "")):
        return

    level = _player_level()
    with prevent_hooking_direct_calls():
        if hasattr(obj, "SetGameStage"):
            obj.SetGameStage(level)
        if hasattr(obj, "SetExpLevel"):
            obj.SetExpLevel(level)

    d = args.DefinitionData
    for attr in ("ManufacturerGradeIndex", "GameStage"):
        if hasattr(d, attr):
            try:
                setattr(d, attr, level)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Hooks — mission accept / status / complete
# ---------------------------------------------------------------------------


@hook("WillowGame.WillowPlayerController:AcceptMission", Type.POST)
def _on_accept(_obj: Any, args: Any, *_: Any) -> None:
    mdef = _get_mission_def_from_args(args)
    if mdef is not None:
        lv = _lock_mission(mdef)
        _scale_mission_def(mdef, lv)
        logging.info(f"[AVHM] Mission accepted at level {lv}: {_obj_path(mdef)}")


@hook("WillowGame.WillowPlayerController:UpdateMissionStatus", Type.POST)
def _on_status_update(_obj: Any, args: Any, *_: Any) -> None:
    mdef = _get_mission_def_from_args(args)
    if mdef is not None:
        level = _display_level(mdef)
        _scale_mission_def(mdef, level)


@hook("WillowGame.WillowPlayerController:ServerCompleteMission")
def _on_complete(_obj: Any, args: Any, *_: Any) -> None:
    mdef = _get_mission_def_from_args(args)
    if mdef is None:
        return None
    level = _reward_level(mdef)
    _scale_mission_def(mdef, level)
    logging.info(f"[AVHM] Mission completing at level {level}: {_obj_path(mdef)}")
    return None


# ---------------------------------------------------------------------------
# Hooks — mission UI level display
# ---------------------------------------------------------------------------


@hook("WillowGame.WillowPlayerController:GetLevelForMission")
def _fix_get_level(_obj: Any, args: Any, *_: Any) -> tuple[type[Block], int] | None:
    mdef = _get_mission_def_from_args(args)
    if mdef is None:
        return None
    level = _display_level(mdef)
    _scale_mission_def(mdef, level)
    return Block, level


@hook("WillowGame.WillowPlayerController:PopulateMissionDataFromStatus", Type.POST)
def _fix_populated(_obj: Any, args: Any, *_: Any) -> None:
    mdef = _get_mission_def_from_args(args)
    level = _display_level(mdef)
    _apply_level_to_payload(args, level)
    for sub in ("MissionData", "OutMissionData", "MissionStatusData"):
        _apply_level_to_payload(getattr(args, sub, None), level)


@hook("WillowGame.WillowPlayerController:ShowStatusMenu", Type.POST)
def _fix_status_menu(*_: Any) -> None:
    _sync_missions()
    _apply_all_mission_scaling()


# ---------------------------------------------------------------------------
# Hooks — mission fanfare UI (completion popup)
# ---------------------------------------------------------------------------


@hook("WillowGame.WillowPlayerController:ClientDoMissionStatusFanfare")
def _fanfare_pre(_obj: Any, args: Any, *_: Any) -> None:
    level = _patch_mission_ui(args=args)
    _push_ui_override(level)


@hook("WillowGame.WillowPlayerController:ClientDoMissionStatusFanfare", Type.POST)
def _fanfare_post(*_: Any) -> None:
    _pop_ui_override()


@hook("WillowGame.WillowHUDGFxMovie:DoMissionStatusFanfare")
@hook("WillowGame.HUDWidget_Missions:DoMissionStatusFanfare")
@hook("WillowGame.HUDWidget_Missions:SetDisplayedMission")
def _hud_fanfare_pre(obj: Any, args: Any, *_: Any) -> None:
    level = _patch_mission_ui(obj, args)
    _push_ui_override(level)


@hook("WillowGame.WillowHUDGFxMovie:DoMissionStatusFanfare", Type.POST)
@hook("WillowGame.HUDWidget_Missions:DoMissionStatusFanfare", Type.POST)
@hook("WillowGame.HUDWidget_Missions:SetDisplayedMission", Type.POST)
def _hud_fanfare_post(*_: Any) -> None:
    _pop_ui_override()


# Override player exp level during fanfare so the "IMPOSSIBLE" comparison works
@hook("WillowGame.WillowUIInteraction:GetExpLevel")
@hook("WillowGame.WillowUIInteraction:GetExpLevelForEquip")
@hook("WillowGame.WillowPlayerPawn:GetExpLevel")
@hook("WillowGame.WillowPlayerPawn:GetExpLevelForEquip")
@hook("WillowGame.WillowPlayerController:GetExpLevelLoadedFromSavedGame")
def _override_ui_exp_level(*_: Any) -> tuple[type[Block], int] | None:
    if _ui_level_override is None:
        return None
    return Block, _ui_level_override


# ---------------------------------------------------------------------------
# Hooks — weapon & item reward scaling
# ---------------------------------------------------------------------------


@hook("WillowGame.WillowPlayerController:ReceiveWeaponReward")
def _fix_weapon_reward(obj: Any, args: Any, *_: Any) -> type[Block] | None:
    if not hasattr(args, "DefinitionData"):
        return None
    d = args.DefinitionData
    level = _reward_level(_get_mission_def_from_args(args))
    scaled = (
        d.WeaponTypeDefinition, d.BalanceDefinition, d.ManufacturerDefinition,
        level, d.BodyPartDefinition, d.GripPartDefinition, d.BarrelPartDefinition,
        d.SightPartDefinition, d.StockPartDefinition, d.ElementalPartDefinition,
        d.Accessory1PartDefinition, d.Accessory2PartDefinition,
        d.MaterialPartDefinition, d.PrefixPartDefinition, d.TitlePartDefinition,
        level, d.UniqueId,
    )
    with prevent_hooking_direct_calls():
        obj.ReceiveWeaponReward(args.Mission, scaled)
    logging.info(f"[AVHM] Weapon reward -> level {level}")
    return Block


@hook("WillowGame.WillowPlayerController:ReceiveItemReward")
def _fix_item_reward(obj: Any, args: Any, *_: Any) -> type[Block] | None:
    if not hasattr(args, "DefinitionData"):
        return None
    d = args.DefinitionData
    level = _reward_level(_get_mission_def_from_args(args))
    scaled = (
        d.ItemDefinition, d.BalanceDefinition, d.ManufacturerDefinition,
        level, d.AlphaItemPartDefinition, d.BetaItemPartDefinition,
        d.GammaItemPartDefinition, d.DeltaItemPartDefinition,
        d.EpsilonItemPartDefinition, d.ZetaItemPartDefinition,
        d.EtaItemPartDefinition, d.ThetaItemPartDefinition,
        d.MaterialItemPartDefinition, d.PrefixItemNamePartDefinition,
        d.TitleItemNamePartDefinition, level, d.UniqueId,
    )
    with prevent_hooking_direct_calls():
        obj.ReceiveItemReward(args.Mission, scaled)
    logging.info(f"[AVHM] Item reward -> level {level}")
    return Block


# ---------------------------------------------------------------------------
# Enable / disable
# ---------------------------------------------------------------------------


def _on_enable() -> None:
    global _ui_level_override, _ui_level_override_depth
    _mission_locked.clear()
    _ui_level_override = None
    _ui_level_override_depth = 0
    _full_apply()
    logging.info(f"[AVHM] Enabled — profile={scaling_opt.value}, "
                 f"regen_disabled=always, player_level={_player_level()}")


def _on_disable() -> None:
    global _ui_level_override, _ui_level_override_depth
    _ui_level_override = None
    _ui_level_override_depth = 0
    _restore_tuning()
    _restore_stages()
    logging.info("[AVHM] Disabled")


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

mod = build_mod(
    cls=RestartToDisable,
    supported_games=Game.BL2,
    coop_support=CoopSupport.Incompatible,
    options=[scaling_opt],
    on_enable=_on_enable,
    on_disable=_on_disable,
)
