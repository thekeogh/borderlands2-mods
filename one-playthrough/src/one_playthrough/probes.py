"""Explicit scaling queries and a separate temporary data experiment; never part of F10."""
from __future__ import annotations

from itertools import islice

import unrealsdk
from unrealsdk.hooks import prevent_hooking_direct_calls
from unrealsdk.unreal import UObject

from .core import safe_text, unavailable
from .reflection import Snapshot, identity, read


def query(obj, name, arguments, out_names=()):
    """Require the exact parameter shape evidenced by 0.1.2 reflection."""
    try:
        function = obj.Class._find(name)
        params = [p for p in islice(function._properties(), 48)
                  if int(p.PropertyFlags) & 128 and not int(p.PropertyFlags) & 1024]
        if {str(p.Name) for p in params} != set(arguments):
            return unavailable(f"{name}: parameter shape differs from verified capture")
        if [str(p.Name) for p in params if int(p.PropertyFlags) & 256] != list(out_names):
            return unavailable(f"{name}: output parameters differ from verified capture")
        with prevent_hooking_direct_calls():
            result = getattr(obj, name)(**arguments)
        if out_names:
            if not isinstance(result, tuple) or len(result) != len(out_names) + 1:
                return unavailable(f"{name}: SDK returned an unexpected output tuple shape")
            return {"return_value": Snapshot().value(result[0]),
                    "out_parameters": {key: Snapshot().value(value) for key, value in zip(out_names, result[1:])},
                    "outputs_valid": result[0] is True}
        return {"return_value": Snapshot().value(result)}
    except Exception as exc:
        return unavailable(f"{name}: {type(exc).__name__}: {safe_text(exc)}")


def scaling_probe(pc):
    if pc is None:
        return unavailable("Load the test character first")
    playthrough = query(pc, "GetCurrentPlaythrough", {})
    if playthrough.get("return_value") != 2 or read(pc, "OverpowerChoiceValue") != 0:
        return unavailable("Probe requires genuine UVHM with OP selection zero")
    result = {"provenance": "explicit SDK read-only calls; direct hooks bypassed, nested native calls may invoke other mods",
              "maximum_player_level": query(pc, "GetMaximumPossiblePlayerLevelCap", {}),
              "missions": [], "regions": []}
    playthroughs = read(pc, "MissionPlaythroughs")
    if isinstance(playthroughs, dict) or len(playthroughs) <= 2:
        return unavailable("UVHM mission records unavailable")
    entries = read(playthroughs[2], "MissionList")
    if isinstance(entries, dict):
        return entries
    regions = {}
    # Actual current-playthrough records only; no guessed active mission.
    for entry in islice(entries, 16):
        mission = read(entry, "MissionDef")
        if not isinstance(mission, UObject):
            continue
        result["missions"].append({"mission": identity(mission),
            "stored_stage": Snapshot().value(read(entry, "GameStage")),
            "stored_status": Snapshot().value(read(entry, "Status")),
            "GetGameStage": query(mission, "GetGameStage", {}),
            "GetExpectedGameStage": query(mission, "GetExpectedGameStage", {}),
            "mission_map_GetLevelForMission": query(pc, "GetLevelForMission", {"InMission": mission}),
            "GetExperienceReward": query(mission, "GetExperienceReward", {"InWPC": pc, "bGetAltReward": False}),
            "GetCurrencyReward": query(mission, "GetCurrencyReward", {"InWPC": pc, "bGetAltReward": False})})
        region = read(mission, "GameStageRegion")
        if isinstance(region, UObject) and len(regions) < 4:
            regions[str(region._path_name())] = region
        if len(result["missions"]) >= 4:
            break
    for region in regions.values():
        result["regions"].append({"region": identity(region),
            "GetGameStageFromRegion": query(pc, "GetGameStageFromRegion", {"Region": region}),
            "GetDefaultRegionGameStage": query(region, "GetDefaultRegionGameStage", {
                "MinGameStage": 0, "MaxGameStage": 0, "AwesomeLevel": 0, "GameStageIncreaseOverPlayerLevel": 0},
                ("MinGameStage", "MaxGameStage", "AwesomeLevel", "GameStageIncreaseOverPlayerLevel")),
            "GetRegionGameStage_current": query(region, "GetRegionGameStage", {
                "GameStage": 0, "AwesomeLevel": 0, "bDefaultGameStage": False}, ("GameStage", "AwesomeLevel")),
            "GetRegionGameStage_default": query(region, "GetRegionGameStage", {
                "GameStage": 0, "AwesomeLevel": 0, "bDefaultGameStage": True}, ("GameStage", "AwesomeLevel"))})
    return result


def threshold_experiment(pc):
    """Opt-in test of the brief's tuning-threshold lead, with guaranteed restore attempt.

    Ordinary F10 and the ordinary scaling probe never run this experiment. It
    changes only the first verified UVHM activation threshold, queries the same
    region, and restores it before returning. No save/actor/reward function runs.
    """
    before = scaling_probe(pc)
    if not before.get("regions"):
        return {"available": False, "reason": "No verified UVHM mission region to compare", "baseline": before}
    path = "GD_Playthrough3Tuning.Balance.BalanceMod_PT3"
    report = {"baseline": before, "temporary_edit": {"object": path, "field": "BalanceModifiers[0].MinEffectiveLevel"},
              "restoration_attempted": False, "restored": False,
              "restart_after_test": True,
              "scope": "explicit temporary data experiment; no gameplay correction enabled"}
    row = None
    original = None
    try:
        tuning = unrealsdk.find_object("BalanceModifierDefinition", path)
        rows = read(tuning, "BalanceModifiers")
        thresholds = [int(read(r, "MinEffectiveLevel")) for r in islice(rows, 4)]
        if thresholds != [50, 61, 73]:
            report["available"] = False
            report["not_run"] = "Threshold layout differs from the captured game build"
            report["observed_thresholds"] = thresholds
            return report
        row = rows[0]
        original = int(read(row, "MinEffectiveLevel"))
        report["tuning_before"] = Snapshot().value(row)
        report["temporary_edit"].update({"original": original, "temporary": 1})
        try:
            row.MinEffectiveLevel = 1
            if int(read(row, "MinEffectiveLevel")) != 1:
                raise RuntimeError("Threshold write did not read back as 1")
            report["with_threshold_1"] = scaling_probe(pc)
        finally:
            report["restoration_attempted"] = True
            row.MinEffectiveLevel = original
            report["restored"] = int(read(row, "MinEffectiveLevel")) == original
        report["after_restore"] = scaling_probe(pc)
        report["tuning_after"] = Snapshot().value(row)
        report["tuning_snapshot_matches_after_restore"] = report["tuning_before"] == report["tuning_after"]
        report["later_thresholds_unchanged"] = [int(read(r, "MinEffectiveLevel")) for r in islice(rows, 4)] == thresholds
    except Exception as exc:
        report["error"] = safe_text(f"{type(exc).__name__}: {exc}")
        if report["restoration_attempted"] and not report["restored"]:
            report["restart_required"] = True
    return report
