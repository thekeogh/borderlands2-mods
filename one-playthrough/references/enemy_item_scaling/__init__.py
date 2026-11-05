from functools import cache
from typing import TYPE_CHECKING, Any

import unrealsdk
from mods_base import BoolOption, SpinnerOption, build_mod, get_pc, hook
from unrealsdk import logging
from unrealsdk.hooks import Block, Type, prevent_hooking_direct_calls

if TYPE_CHECKING:
    from collections.abc import Callable

    from unrealsdk.unreal import BoundFunction, UClass, UObject, WrappedStruct

# Injected by build_mod() from pyproject.toml
__version__: str
__version_info__: tuple[int, ...]

VANILLA = "Vanilla"

# Spinner label -> how far from the player's level the bound sits. None means the bound is off.
LEVEL_CHOICES: dict[str, int | None] = {
    VANILLA: None,
    "Player Level": 0,
    "Within 1 Level": 1,
    **{f"Within {n} Levels": n for n in range(2, 11)},
}


# Appended to every bound's description
CHOICES_HELP = (
    "'Player Level' is exactly your level. 'Within N Levels' is N levels below you for a\n"
    "minimum and N levels above you for a maximum."
)


def _level_spinner(identifier: str, description: str) -> SpinnerOption:
    return SpinnerOption(
        identifier,
        VANILLA,
        list(LEVEL_CHOICES),
        description=f"{description}\n{CHOICES_HELP}",
    )


min_enemy_level = _level_spinner(
    "Minimum Enemy Level",
    "Enemies that would spawn below this are raised to it.",
)
max_enemy_level = _level_spinner(
    "Maximum Enemy Level",
    "Enemies that would spawn above this are lowered to it.",
)
min_item_level = _level_spinner(
    "Minimum Item Level",
    "Loot that would drop below this is raised to it. Independent of the enemy settings,"
    " so you can keep vanilla enemies and still get on-level gear.",
)
max_item_level = _level_spinner(
    "Maximum Item Level",
    "Loot that would drop above this is lowered to it.",
)
min_mission_level = _level_spinner(
    "Minimum Mission Level",
    "Missions you have accepted that fall below this are raised to it and follow you as you"
    " level up, so their reward item, XP and cash come at that level.\n"
    "Saved with your character: a raised mission keeps its level if you set this back to"
    " Vanilla.",
)
on_level_vendors = BoolOption(
    "On-Level Vendors",
    False,
    description=(
        "Vending machines below your level stock items at your level, including the item of\n"
        "the day. Machines above your level are left as they are: lowering one can leave it\n"
        "with nothing to sell. Applies when a machine spawns or restocks."
    ),
)
log_adjustments = BoolOption(
    "Log Adjustments",
    False,
    description=(
        "Print every level change, every vending machine you open and every mission you turn\n"
        "in to the console and to Binaries/Win32/Plugins/unrealsdk.log.\n"
        "Useful when testing or reporting a bug."
    ),
)

OPTIONS = [
    min_enemy_level,
    max_enemy_level,
    min_item_level,
    max_item_level,
    min_mission_level,
    on_level_vendors,
    log_adjustments,
]

LOG_PREFIX = "[Enemy and Item Scaling]"

# EInputEvent.IE_Pressed
IE_PRESSED = 0


def clamp_level(
    level: int,
    player_level: int,
    floor_offset: int | None,
    ceiling_offset: int | None,
) -> int:
    """
    Clamps a level into the band [player - floor_offset, player + ceiling_offset].

    Args:
        level: The level the game chose.
        player_level: The player's effective level.
        floor_offset: How far below the player the floor sits, or None for no floor.
        ceiling_offset: How far above the player the ceiling sits, or None for no ceiling.
    Returns:
        The clamped level. Equal to the input whenever it was already inside the band.
    """
    if floor_offset is not None:
        level = max(level, player_level - floor_offset)
    if ceiling_offset is not None:
        level = min(level, player_level + ceiling_offset)
    return level


# GetCurrentPlaythrough() is 0-based: Normal, TVHM, UVHM. Overpower levels only exist in UVHM.
UVHM_PLAYTHROUGH = 2


@cache
def has_overpower_levels() -> bool:
    """
    Whether this game has Overpower levels.

    They are a Borderlands 2 feature: The Pre-Sequel's player controller has no
    OverpowerChoiceValue field at all, and reading it there would raise inside every hook. The
    field itself is looked for, rather than asking which game is running, so an unrecognised
    executable name (which the SDK treats as Borderlands 2) can't make the mod read a field that
    isn't there.
    """
    try:
        unrealsdk.find_class("WillowPlayerController")._find_prop("OverpowerChoiceValue")
    except ValueError:
        return False
    return True


def player_level_for(pc: UObject) -> int | None:
    """
    Gets a player's effective level: experience level, plus the Overpower level in BL2 UVHM.

    Args:
        pc: The player's WillowPlayerController.
    Returns:
        The level that enemies and loot are measured against, or None while the player isn't
        loaded yet (a level of 0 would otherwise drag every spawn down to nothing).
    """
    pri = pc.PlayerReplicationInfo
    if pri is None:
        return None
    level = int(pri.ExpLevel)
    if level <= 0:
        return None
    if has_overpower_levels() and pc.GetCurrentPlaythrough() == UVHM_PLAYTHROUGH:
        level += int(pc.OverpowerChoiceValue)
    return level


def get_player_level() -> int | None:
    """
    Gets the local player's effective level, or None while they aren't loaded yet.

    Returns:
        See `player_level_for`.
    """
    pc = get_pc(possibly_loading=True)
    return None if pc is None else player_level_for(pc)


@cache
def _player_pawn_class() -> UClass:
    return unrealsdk.find_class("WillowPlayerPawn")


# Classes that count as vending machines: the base class every game has, plus ones only some
# games have (looked up by their short native name; a missing one is skipped). The SHiFT
# machine in The Pre-Sequel's Concordia is an interactive object of its own, not a
# WillowVendingMachineBase.
VENDOR_CLASS_NAME = "WillowVendingMachineBase"
OPTIONAL_VENDOR_CLASS_NAMES = ("WillowVendingMachineShift",)


@cache
def _vendor_classes() -> tuple[UClass, ...]:
    classes = [unrealsdk.find_class(VENDOR_CLASS_NAME)]
    for name in OPTIONAL_VENDOR_CLASS_NAMES:
        try:
            classes.append(unrealsdk.find_class(name))
        except ValueError:
            # Not a class in this game
            continue
    return tuple(classes)


def _is_player_pawn(obj: UObject) -> bool:
    return obj.Class._inherits(_player_pawn_class())


def _is_vending_machine(obj: UObject) -> bool:
    cls = obj.Class
    return any(cls._inherits(vendor) for vendor in _vendor_classes())


def _replace_level(
    kind: str,
    obj: UObject,
    setter: BoundFunction,
    requested: int,
    *,
    wanted: int,
    player_level: int,
) -> type[Block] | None:
    """
    Re-issues a level-setter call with a different level, if it differs from the requested one.

    Args:
        kind: What is being scaled, for the log line.
        obj: The object whose level is being set.
        setter: The level setter the game is calling, bound to `obj`.
        requested: The level the game asked for.
        wanted: The level we want instead.
        player_level: The player's level, for the log line.
    Returns:
        Block if the call was replaced, None to let the original run untouched.
    """
    if wanted == requested:
        return None

    if log_adjustments.value:
        logging.info(
            f"{LOG_PREFIX} {kind} {obj.Name}: {requested} -> {wanted} (player {player_level})",
        )

    # The args struct is a copy, so the only way to change the level is to call the setter
    # ourselves and block the original call. Direct calls in here don't re-trigger our hooks.
    with prevent_hooking_direct_calls():
        setter(wanted)
    return Block


def _band_target(
    requested: int,
    floor: SpinnerOption,
    ceiling: SpinnerOption,
) -> tuple[int, int] | None:
    """
    Works out what a band would turn a requested level into.

    Args:
        requested: The level the game asked for.
        floor: The spinner holding the lower bound.
        ceiling: The spinner holding the upper bound.
    Returns:
        (wanted level, player level) when the band changes the level, None when it leaves it
        alone (both bounds vanilla, player not loaded, or already inside the band).
    """
    floor_offset = LEVEL_CHOICES.get(floor.value)
    ceiling_offset = LEVEL_CHOICES.get(ceiling.value)
    if floor_offset is None and ceiling_offset is None:
        return None

    player_level = get_player_level()
    if player_level is None:
        return None
    wanted = clamp_level(requested, player_level, floor_offset, ceiling_offset)
    if wanted == requested:
        return None
    return wanted, player_level


def _apply_band(
    kind: str,
    obj: UObject,
    setter: BoundFunction,
    requested: int,
    *,
    floor: SpinnerOption,
    ceiling: SpinnerOption,
) -> type[Block] | None:
    """
    Replaces a level-setter call when the requested level falls outside the configured band.

    Args:
        kind: What is being scaled, for the log line.
        obj: The object whose level is being set.
        setter: The level setter the game is calling, bound to `obj`.
        requested: The level the game asked for.
        floor: The spinner holding the lower bound.
        ceiling: The spinner holding the upper bound.
    Returns:
        Block if the call was replaced with a clamped one, None to let the original run.
    """
    target = _band_target(requested, floor, ceiling)
    if target is None:
        return None
    wanted, player_level = target
    return _replace_level(kind, obj, setter, requested, wanted=wanted, player_level=player_level)


def _apply_on_level(
    kind: str,
    obj: UObject,
    setter: BoundFunction,
    requested: int,
    *,
    enabled: BoolOption,
) -> type[Block] | None:
    """
    Raises a level-setter call to the player's level, when the toggle is on.

    Never lowers: item pools only offer some categories from a minimum level, so a machine
    pulled far below its area's level can come out with little or nothing to sell (seen in the
    Fight for Sanctuary DLC with a low-level character).

    Args:
        kind: What is being scaled, for the log line.
        obj: The object whose level is being set.
        setter: The level setter the game is calling, bound to `obj`.
        requested: The level the game asked for.
        enabled: The toggle for this source.
    Returns:
        Block if the call was replaced, None to let the original run.
    """
    if not enabled.value:
        return None
    player_level = get_player_level()
    if player_level is None:
        return None
    return _replace_level(
        kind,
        obj,
        setter,
        requested,
        wanted=max(requested, player_level),
        player_level=player_level,
    )


def _factory_name(factory: UObject) -> str:
    balance = factory.PawnBalanceDefinition
    return factory.Name if balance is None else balance.Name


def _vehicle_factory_name(factory: UObject) -> str:
    archetype = factory.VehicleArchetype
    return factory.Name if archetype is None else archetype.Name


def _spawn_in_band(
    obj: UObject,
    args: WrappedStruct,
    func: BoundFunction,
    name_of: Callable[[UObject], str],
) -> tuple[type[Block], UObject | None] | None:
    """
    Re-runs a population factory call with its GameStage argument clamped to the enemy band.

    Args:
        obj: The population factory.
        args: The factory call's arguments; GameStage is the level it was asked for.
        func: The factory call, bound to `obj`.
        name_of: Names the factory for the log line.
    Returns:
        (Block, the spawned actor) when the level was clamped, None to let the original run.
    """
    requested = int(args.GameStage)
    target = _band_target(requested, min_enemy_level, max_enemy_level)
    if target is None:
        return None
    wanted, player_level = target

    if log_adjustments.value:
        logging.info(
            f"{LOG_PREFIX} spawn {name_of(obj)}: {requested} -> {wanted} (player {player_level})",
        )
    args.GameStage = wanted
    with prevent_hooking_direct_calls():
        spawned = func(args)
    return Block, spawned


@hook("WillowGame.PopulationFactoryBalancedAIPawn:CreatePopulationActor")
@hook("WillowGame.PopulationFactoryBalancedAIPawn:RestorePopulatedAIPawn")
def on_spawn_ai_pawn(
    obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    func: BoundFunction,
) -> tuple[type[Block], UObject | None] | None:
    """
    Scales an enemy's level before the population factory builds it.

    The factory hands its GameStage argument to everything that makes up the enemy: the game
    stage, the displayed level (ExpLevel, which its health and damage are computed from) and
    the level of its drops. Changing the argument here moves all of them together; changing
    only the game stage afterwards (the v0.1-v0.4 approach) left the enemy at its old level
    with on-level drops.
    """
    return _spawn_in_band(obj, args, func, _factory_name)


# PopulationFactoryWillowVehicle.BalanceVehicleFor (EVehicleBalanceOption): 0 balances the
# vehicle for the players who will drive it, 1 for the enemy AI that crews it.
VEHICLE_BALANCE_FOR_ENEMY_AI = 1


@hook("WillowGame.PopulationFactoryWillowVehicle:CreatePopulationActor")
def on_spawn_vehicle(
    obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    func: BoundFunction,
) -> tuple[type[Block], UObject | None] | None:
    """
    Scales an enemy vehicle's level before its population factory builds it.

    Bandit technicals, sandskiffs, turrets, fan boats and The Pre-Sequel's scav buggies are
    vehicles, not pawns (buzzards are pawns): they have a factory and level setters of their
    own, so the enemy hooks above never see them. This factory passes its GameStage argument
    on the same way the pawn one does, so the same clamp moves the vehicle's level, health and
    drops together. Catch-A-Ride vehicles come from factories balanced for players, which the
    game levels to the players itself.
    """
    if int(obj.BalanceVehicleFor) != VEHICLE_BALANCE_FOR_ENEMY_AI:
        return None
    return _spawn_in_band(obj, args, func, _vehicle_factory_name)


@hook("WillowGame.WillowPawn:SetGameStage")
def on_pawn_game_stage(
    obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    func: BoundFunction,
) -> type[Block] | None:
    """
    Scales an enemy's game stage as it is set.

    Safety net for enemies that don't come through the population factory. For the ones that
    do, the factory hook above already passed the clamped level in, so this is a no-op.
    """
    if _is_player_pawn(obj):
        return None
    requested = int(args.NewGameStage)
    return _apply_band(
        "enemy",
        obj,
        func,
        requested,
        floor=min_enemy_level,
        ceiling=max_enemy_level,
    )


@hook("WillowGame.WillowAIPawn:SetExpLevel")
def on_ai_pawn_exp_level(
    obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    func: BoundFunction,
) -> type[Block] | None:
    """
    Scales an enemy's displayed level (the one its health and damage come from) as it is set.

    Same safety net as the game stage one: the factory sets this right after the game stage,
    from the same argument, so an enemy that skipped the factory still ends up consistent.
    """
    if _is_player_pawn(obj):
        return None
    requested = int(args.NewExpLevel)
    return _apply_band(
        "enemy level",
        obj,
        func,
        requested,
        floor=min_enemy_level,
        ceiling=max_enemy_level,
    )


def _is_player_vehicle(obj: UObject) -> bool:
    """Whether a vehicle came from a Catch-A-Ride station: the game levels those to the players."""
    return bool(obj.WasSpawnedFromASpawnStation())


@hook("WillowGame.WillowVehicle:SetGameStage")
def on_vehicle_game_stage(
    obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    func: BoundFunction,
) -> type[Block] | None:
    """
    Scales an enemy vehicle's game stage as it is set.

    Vehicles have their own level setters, which the pawn safety nets never see. Same role as
    those: for a vehicle that skipped its factory; a no-op after the factory hook.
    """
    if _is_player_vehicle(obj):
        return None
    requested = int(args.NewGameStage)
    return _apply_band(
        "vehicle",
        obj,
        func,
        requested,
        floor=min_enemy_level,
        ceiling=max_enemy_level,
    )


@hook("WillowGame.WillowVehicle:SetExpLevel")
def on_vehicle_exp_level(
    obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    func: BoundFunction,
) -> type[Block] | None:
    """Scales an enemy vehicle's displayed level as it is set; the same safety net."""
    if _is_player_vehicle(obj):
        return None
    requested = int(args.NewExpLevel)
    return _apply_band(
        "vehicle level",
        obj,
        func,
        requested,
        floor=min_enemy_level,
        ceiling=max_enemy_level,
    )


@hook("WillowGame.WillowPawn:SetGameStageForSpawnedInventory")
@hook("WillowGame.WillowAIPawn:SetGameStageForSpawnedInventory")
def on_pawn_loot_game_stage(
    obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    func: BoundFunction,
) -> type[Block] | None:
    """Scales the level of the loot an enemy will drop."""
    if _is_player_pawn(obj):
        return None
    requested = int(args.NewInventoryGameStage)
    return _apply_band("loot", obj, func, requested, floor=min_item_level, ceiling=max_item_level)


# Maps whose containers are never lowered: Bouncy Loot God found a chest in each that spawns
# nothing when down-levelled (Mercenary Day's hub, The Pre-Sequel's intro). Object paths start
# with the map name.
NO_DOWNLEVEL_MAP_PREFIXES = ("Xmas_P.", "MoonShotIntro_P.")


@hook("WillowGame.WillowInteractiveObject:SetGameStage")
def on_interactive_object_game_stage(
    obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    func: BoundFunction,
) -> type[Block] | None:
    """
    Scales the level of chests, slot machines and other containers, and raises vending machines.

    Vending machines are interactive objects too, but they get their own toggle rather than the
    item band, and are only ever raised.
    """
    requested = int(args.NewGameStage)
    if _is_vending_machine(obj):
        return _apply_on_level("vendor", obj, func, requested, enabled=on_level_vendors)
    target = _band_target(requested, min_item_level, max_item_level)
    if target is None:
        return None
    wanted, player_level = target
    if wanted < requested and obj._path_name().startswith(NO_DOWNLEVEL_MAP_PREFIXES):
        return None
    return _replace_level(
        "container",
        obj,
        func,
        requested,
        wanted=wanted,
        player_level=player_level,
    )


@hook("WillowGame.WillowVendingMachine:ResetInventory")
@hook("WillowGame.WillowVendingMachineShift:ResetInventory")
def on_vending_machine_reset(
    obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    """
    Raises a vending machine to the player's level right before it restocks.

    A machine keeps the level it spawned with, so without this the 20 minute restock (and paid
    resets) would keep producing stock at the level you had when you entered the map. A machine
    at or above the player's level is left alone, as at spawn. The second hook target is The
    Pre-Sequel's SHiFT machine; in Borderlands 2 no such function exists and the hook simply
    never fires.
    """
    if not on_level_vendors.value:
        return
    player_level = get_player_level()
    if player_level is None:
        return
    current = int(obj.GameStage)
    if current >= player_level:
        return

    if log_adjustments.value:
        logging.info(f"{LOG_PREFIX} vendor restock {obj.Name}: {current} -> {player_level}")
    # Same pair of setters the game's own factory calls when it spawns the machine
    with prevent_hooking_direct_calls():
        obj.SetGameStage(player_level)
        obj.SetExpLevel(player_level)


@cache
def _stocked_vendor_class() -> UClass:
    # The machines with a stock list; the black market and the SHiFT machine have none
    return unrealsdk.find_class("WillowVendingMachine")


@hook("WillowGame.WillowInteractiveObject:UseObject", Type.POST)
def on_interactive_object_used(
    obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    """
    Logs a vending machine's level and how much it has for sale when the player opens it.

    Only reports, and runs whether or not On-Level Vendors is on, so a machine with nothing to
    sell can be compared both ways from the log alone.
    """
    if not log_adjustments.value or not _is_vending_machine(obj):
        return
    stock = ""
    if obj.Class._inherits(_stocked_vendor_class()):
        count = sum(1 for item in obj.ShopInventory if item is not None)
        featured = "none" if obj.FeaturedItem is None else "yes"
        stock = f", {count} items, item of the day {featured}"
    logging.info(
        f"{LOG_PREFIX} vendor opened {obj.Name}: level {int(obj.GameStage)}"
        f" (exp level {int(obj.ExpLevel)}){stock} (player {get_player_level()})",
    )


# EMissionStatus values for a mission the player has accepted but not finished with:
# Active, RequiredObjectivesComplete, ReadyToTurnIn.
MISSION_ACCEPTED_STATUSES = frozenset({1, 2, 3})
# The ones a mission can be turned in from, and the one it ends in.
MISSION_TURN_IN_STATUSES = frozenset({2, 3})
MISSION_COMPLETE = 4

# Missions whose turn-in was confirmed and that haven't been reported complete since, by path.
# Cleared on every map load.
_open_turn_ins: set[str] = set()

# The level each mission had when the game rolled its rewards, keyed by mission path. Only used
# to check the reward item against it as the player takes it; cleared on every map load.
_rolled_stages: dict[str, int] = {}


def _mission_floor_offset() -> int | None:
    """How far below the player the mission floor sits, or None when the bound is off."""
    return LEVEL_CHOICES.get(min_mission_level.value)


def _player_mission_entry(pc: UObject, mission: UObject) -> WrappedStruct | None:
    """
    Finds a player's own record of a mission (status, progress and game stage).

    Args:
        pc: The WillowPlayerController.
        mission: The MissionDefinition.
    Returns:
        The MissionStatusPlayerData entry for the current playthrough, or None if the player
        has none for this mission.
    """
    index = int(pc.NativeGetMissionIndex(mission))
    if index < 0:
        return None
    playthroughs = pc.MissionPlaythroughs
    playthrough = int(pc.GetCurrentPlaythrough())
    if not 0 <= playthrough < len(playthroughs):
        return None
    missions = playthroughs[playthrough].MissionList
    if index >= len(missions):
        return None
    return missions[index]


def _level_mission(mission: UObject, pc: UObject, entry: WrappedStruct | None = None) -> None:
    """
    Raises a mission's level to the mission floor (the player's level minus the bound's offset).

    The level lives in two places: the definition's transient `GameStage` (what the mission
    log, the XP and cash, the reward roll and mods asking `mission.GetGameStage()` see) and the
    player's own record of the mission, which is what the save file stores and what the game
    puts back into the definition on load. Both are written, so from now on the mission simply
    is at that level, as if it had been accepted at that level in UVHM.

    Never lowered: reward pools have minimum levels, and a mission locked above the player (a
    DLC mission taken early) could end up with no reward at all if pulled below them.

    Args:
        mission: The MissionDefinition.
        pc: The WillowPlayerController whose level to use.
        entry: The player's record of the mission, if the caller already has it.
    """
    offset = _mission_floor_offset()
    player_level = player_level_for(pc)
    if offset is None or player_level is None:
        return
    floor = max(1, player_level - offset)
    if entry is None:
        entry = _player_mission_entry(pc, mission)
    current = int(mission.GameStage)
    locked = bool(mission.bGameStageLocked)
    entry_stage = None if entry is None else int(entry.GameStage)
    # Raise only, and never below what the player's own record says: the definition is rebuilt
    # from that record on load.
    wanted = max(current, entry_stage or 0, floor)
    if current == wanted and locked and entry_stage in (None, wanted):
        return

    if log_adjustments.value and current != wanted:
        logging.info(f"{LOG_PREFIX} mission {mission.Name}: {current} -> {wanted}")
    mission.GameStage = wanted
    # Accepted missions are already locked; make sure of it so the game doesn't recompute the
    # stage from the mission's region.
    mission.bGameStageLocked = True
    if entry is not None:
        entry.GameStage = wanted


def _level_accepted_missions(pc: UObject) -> None:
    """
    Levels every mission a player has accepted and not yet turned in.

    Args:
        pc: The WillowPlayerController.
    """
    playthroughs = pc.MissionPlaythroughs
    playthrough = int(pc.GetCurrentPlaythrough())
    if not 0 <= playthrough < len(playthroughs):
        return
    for entry in playthroughs[playthrough].MissionList:
        if int(entry.Status) in MISSION_ACCEPTED_STATUSES and entry.MissionDef is not None:
            _level_mission(entry.MissionDef, pc, entry)


def _note_turn_in(mission: UObject, pc: UObject, status: int) -> None:
    """
    Records a confirmed turn-in, warning if the last one of the same mission never completed.

    A turn-in that doesn't complete leaves the mission in the list, and turning it in again can
    pay its XP and cash again. This mod never stops a completion, but another mod's turn-in can
    fail partway, so this is always logged.

    Args:
        mission: The MissionDefinition being turned in.
        pc: The WillowPlayerController turning it in.
        status: The mission's status for that player as the turn-in was confirmed.
    """
    path = mission._path_name()
    if path in _open_turn_ins:
        logging.warning(
            f"{LOG_PREFIX} {mission.Name} is being turned in again, but the last turn-in never"
            " completed it, so its XP and cash may be paid again. Something stopped it"
            " completing, possibly another mod (please report this, with any errors above)",
        )
    _open_turn_ins.add(path)
    if log_adjustments.value:
        logging.info(
            f"{LOG_PREFIX} turn-in {mission.Name}: level {int(mission.GameStage)},"
            f" status {status} (player {player_level_for(pc)})",
        )


def _note_complete(mission: UObject) -> None:
    """
    Marks a turned-in mission as completed.

    Args:
        mission: The MissionDefinition the game just set to complete.
    """
    path = mission._path_name()
    if path not in _open_turn_ins:
        return
    _open_turn_ins.discard(path)
    if log_adjustments.value:
        logging.info(f"{LOG_PREFIX} turn-in {mission.Name} complete")


@hook("WillowGame.WillowPlayerController:AcceptMission", Type.POST)
def on_mission_accepted(
    obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    """
    Levels a mission as the player accepts it, so the log shows it at their level at once.

    The game can refuse an acceptance (dependencies not met, for one), and this runs either
    way, so the mission's status is checked first.
    """
    if _mission_floor_offset() is None:
        return
    mission = args.Mission
    if mission is None:
        return
    if int(obj.GetPlayersMissionStatus(mission)) not in MISSION_ACCEPTED_STATUSES:
        return
    _level_mission(mission, obj)


@hook("WillowGame.WillowPlayerController:ClientReceiveMissionStatus", Type.POST)
def on_mission_status_received(
    obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    """
    Levels a mission as the player is told its new status, for acceptances with no NPC.

    Plot missions handed out by an ECHO or a cutscene never go through `AcceptMission`; the
    status notification is the last thing the game sends each player about the change, so a
    write here can't be overwritten by the game's own stage bookkeeping. Also marks a turned-in
    mission complete, whatever the mission bound is set to.
    """
    data = args.MissionStatusData
    mission = data.Mission
    if mission is None:
        return
    status = int(data.Status)
    if status == MISSION_COMPLETE:
        # A co-op host sees other players' completions too; only our own turn-ins are tracked
        if obj.IsLocalPlayerController():
            _note_complete(mission)
        return
    if _mission_floor_offset() is None or status not in MISSION_ACCEPTED_STATUSES:
        return
    _level_mission(mission, obj)


@hook("WillowGame.WillowPlayerController:OnExpLevelChange", Type.POST)
def on_player_level_up(
    obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    """
    Levels every accepted mission when the player levels up.

    The game also calls this once while a character loads, with both flags off and possibly a
    stale level; that call is skipped and the map-load hook below does the work instead.
    """
    if _mission_floor_offset() is None:
        return
    if not (bool(args.bFeedback) or bool(args.bNaturalLevelup)):
        return
    _level_accepted_missions(obj)


@hook("WillowGame.WillowPlayerController:WillowClientDisableLoadingMovie", Type.POST)
def on_map_loaded(
    obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    """
    Levels every accepted mission once a map has loaded, and starts the session's records over.

    Covers missions accepted before the option was turned on and characters that levelled while
    the mission sat in another map; after a save-quit the game puts the saved record back into
    the definition, so the level sticks and this has nothing to do.
    """
    # On a co-op host this also fires for each client that loads in; only our own load resets
    # the per-session state
    if obj.IsLocalPlayerController():
        _rolled_stages.clear()
        _open_turn_ins.clear()
        if log_adjustments.value:
            settings = ", ".join(f"{option.identifier} = {option.value}" for option in OPTIONS)
            logging.info(f"{LOG_PREFIX} settings v{mod.version}: {settings}")
    if _mission_floor_offset() is None:
        return
    _level_accepted_missions(obj)


@hook("WillowGame.QuestAcceptGFxMovie:UpdateMissionList", Type.POST)
@hook("WillowGame.QuestAcceptGFxMovie:DetermineQuestEntries", Type.POST)
@hook("WillowGame.QuestAcceptGFxMovie:extPopulateQuestEntries", Type.POST)
def on_mission_list_updated(
    obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    """
    Levels every accepted mission in an NPC's mission list as soon as the list is built.

    Normally a no-op (the missions were levelled on accept and on each level-up). Kept because
    it runs before anything can be turned in, whichever order other mods' hooks run in, which
    is what makes mods that roll rewards themselves (Reward Reroller) see the level.
    """
    if _mission_floor_offset() is None:
        return
    pc = obj.WPCOwner
    if pc is None:
        return
    for entry in obj.MissionList:
        if int(entry.MissionStatus) in MISSION_ACCEPTED_STATUSES and entry.MissionDef is not None:
            _level_mission(entry.MissionDef, pc)


@hook("WillowGame.QuestAcceptGFxMovie:SetRewardCard")
def on_reward_card(
    _obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    """
    Levels an accepted mission when its reward card is shown, before anything can turn it in.

    This is early enough for mods that roll the rewards themselves on the turn-in confirm,
    such as Reward Reroller, whose calls never go through the hooks below.
    """
    if _mission_floor_offset() is None:
        return
    mission = args.MissionDef
    pc = args.WPC
    if mission is None or pc is None:
        return
    if int(pc.GetPlayersMissionStatus(mission)) not in MISSION_ACCEPTED_STATUSES:
        return
    _level_mission(mission, pc)


@hook("WillowGame.QuestAcceptGFxMovie:extCompleteConfirmed")
def on_complete_confirmed(
    obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    """
    Notes the turn-in as it is confirmed, and levels the mission as a backstop.

    The levelling only beats another mod's hook on the same function if ours registered first
    (true when both were enabled at launch), so the mission-list hook above is the one to rely
    on. The turn-in note runs whatever the mission bound is set to.
    """
    pc = obj.WPCOwner
    if pc is None:
        return
    index = int(obj.GetSelectedIndex())
    entries = obj.MissionList
    if not 0 <= index < len(entries):
        return
    mission = entries[index].MissionDef
    if mission is None:
        return
    # The live status, not the list entry's copy from when the list was built
    status = int(pc.GetPlayersMissionStatus(mission))
    if status not in MISSION_ACCEPTED_STATUSES:
        return
    if _mission_floor_offset() is not None:
        _level_mission(mission, pc)
    if status in MISSION_TURN_IN_STATUSES:
        _note_turn_in(mission, pc, status)


@hook("WillowGame.QuestAcceptGFxMovie:HandleRewardInputKey")
def on_reward_page_key(
    obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    """
    Logs the keys pressed on a mission's reward page.

    Only reports. Tells apart a reward page that was left without accepting, one that never
    took input, and an accept that didn't complete the mission.
    """
    if not log_adjustments.value or int(args.uevent) != IE_PRESSED:
        return
    reward = obj.RewardObject
    mission = None if reward is None else reward.RewardData.Mission
    name = "no mission" if mission is None else mission.Name
    logging.info(f"{LOG_PREFIX} reward page key {args.ukey} ({name})")


@hook("WillowGame.WillowPlayerController:ServerGrantMissionRewards")
def on_grant_mission_rewards(
    obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    """
    Levels a mission to the player it is rewarding, right before the game rolls the rewards.

    Covers completions that never show a reward card (scripted ones). Expected to run on the
    host once per player (untested in co-op), so the level comes from that player's controller.
    Remembers the level the roll is about to use, for the check below.
    """
    if _mission_floor_offset() is None:
        return
    mission = args.Mission
    if mission is None:
        return
    _level_mission(mission, obj)
    _rolled_stages[mission._path_name()] = int(mission.GameStage)


@hook("WillowGame.WillowPlayerController:UpdateMissionStatus", Type.POST_UNCONDITIONAL)
def on_mission_status_updated(
    obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    """
    Levels a mission whenever the game sets it to an accepted status.

    The game locks a mission's level right before this runs for a newly accepted mission, so
    this is where the player's record of it is first complete; the accept hook above then has
    nothing left to do. Also marks a turned-in mission complete, whatever the mission bound is
    set to.
    """
    mission = args.Mission
    if mission is None:
        return
    status = int(args.NewMissionStatus)
    if status == MISSION_COMPLETE:
        # A co-op host sees other players' completions too; only our own turn-ins are tracked
        if obj.IsLocalPlayerController():
            _note_complete(mission)
        return
    if _mission_floor_offset() is None or status not in MISSION_ACCEPTED_STATUSES:
        return
    _level_mission(mission, obj)


@hook("WillowGame.WillowPlayerController:ReceiveWeaponReward")
@hook("WillowGame.WillowPlayerController:ReceiveItemReward")
def on_receive_reward(
    _obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    """
    Checks, as the player takes a reward item, that it was rolled at the mission's level.

    Nothing is changed here: the mission itself was at the player's level when the game rolled
    the reward, so the item should be too. An item below that level means the roll read
    something else, which is a bug worth reporting, so it is always logged. A reward with no
    remembered roll (Reward Reroller's, or one left unclaimed in an earlier session) is not
    checked.
    """
    if _mission_floor_offset() is None:
        return
    mission = args.Mission
    if mission is None:
        return
    expected = _rolled_stages.get(mission._path_name())
    if expected is None:
        return
    rolled = int(args.DefinitionData.ManufacturerGradeIndex)
    if rolled < expected:
        logging.warning(
            f"{LOG_PREFIX} reward item {mission.Name} is level {rolled} but the mission was level"
            f" {expected} when it was rolled (please report this)",
        )


mod = build_mod(options=OPTIONS)
