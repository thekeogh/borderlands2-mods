"""Explicit native override feasibility test. Restart is the only claimed cleanup."""
from __future__ import annotations

from itertools import islice

import unrealsdk
from unrealsdk.hooks import prevent_hooking_direct_calls
from unrealsdk.unreal import UObject, UFunction

from .core import safe_text, unavailable
from .probes import query, scaling_probe
from .reflection import Snapshot, identity, read


def region_values(region):
    return {
        "region": identity(region),
        "reflected_fields": Snapshot(max_nodes=80, max_array=3).fields(region, pattern=None),
        "default_bounds": query(region, "GetDefaultRegionGameStage", {
            "MinGameStage": 0, "MaxGameStage": 0, "AwesomeLevel": 0, "GameStageIncreaseOverPlayerLevel": 0},
            ("MinGameStage", "MaxGameStage", "AwesomeLevel", "GameStageIncreaseOverPlayerLevel")),
        "current": query(region, "GetRegionGameStage", {
            "GameStage": 0, "AwesomeLevel": 0, "bDefaultGameStage": False}, ("GameStage", "AwesomeLevel")),
        "default": query(region, "GetRegionGameStage", {
            "GameStage": 0, "AwesomeLevel": 0, "bDefaultGameStage": True}, ("GameStage", "AwesomeLevel")),
    }


def region_override_experiment(pc):
    report = {"setter_attempted": False, "restart_required": False,
              "scope": "explicit native-setter experiment; no actor, mission-record, inventory or save writes",
              "original_override": unavailable("No reflected getter/backing field is known; effective stage is not the stored override"),
              "restoration": "No guessed reset value or exact restoration claimed; quit/restart after any setter attempt"}
    try:
        if pc is None or query(pc, "GetCurrentPlaythrough", {}).get("return_value") != 2:
            return {**report, **unavailable("Load the genuine UVHM test character first")}
        if read(pc, "OverpowerChoiceValue") != 0:
            return {**report, **unavailable("Non-zero OP selection is outside this experiment")}
        pri = read(pc, "PlayerReplicationInfo")
        level = read(pri, "ExpLevel")
        if not isinstance(level, int) or isinstance(level, bool) or not 1 <= level < 50:
            return {**report, **unavailable("Experiment requires actual XP level 1–49")}
        baseline = scaling_probe(pc)
        report["mission_baseline"] = baseline
        candidates = baseline.get("regions", [])
        if not candidates:
            return {**report, **unavailable("No verified current-playthrough mission region")}
        # The argument comes from the exact mission region in the actual save.
        target_path = candidates[0]["region"]["path"]
        target = unrealsdk.find_object("WillowRegionDefinition", target_path)
        function = target.Class._find("SetGameStageOverride")
        if not isinstance(function, UFunction):
            raise ValueError("SetGameStageOverride is not a reflected UFunction")
        if str(function.Outer._path_name()) != "WillowGame.WillowRegionDefinition":
            raise ValueError("Setter owner differs from the captured build")
        props = list(islice(function._properties(), 16))
        if len(props) != 1 or (str(props[0].Name), str(props[0].Class.Name), int(props[0].PropertyFlags)) != (
                "NewGameStageOverride", "IntProperty", 128):
            raise ValueError("Setter parameter shape differs from the captured build")
        if int(function.FunctionFlags) != 140288:
            raise ValueError("Setter flags differ from the captured build")
        regions = [target]
        scan_errors = []
        try:
            # A small independent sample tests whether this setter affects other
            # regions too. These objects are already loaded; no packages are loaded.
            for obj in islice(unrealsdk.find_all("WillowRegionDefinition", exact=False), 128):
                path = str(obj._path_name())
                if path.startswith("GD_GameStages.Zone1.") and path != target_path:
                    regions.append(obj)
                    if len(regions) == 3:
                        break
        except Exception as exc:
            scan_errors.append(safe_text(exc))
        report.update({"target_region": identity(target), "requested_stage": level,
                       "setter_flags": int(function.FunctionFlags), "scan_errors": scan_errors,
                       "before": [region_values(obj) for obj in regions]})
        stage = report["before"][0]["current"]
        if not stage.get("outputs_valid") or stage.get("out_parameters", {}).get("GameStage") != 50:
            return {**report, **unavailable("Baseline does not match the observed level-50 floor; setter not called")}
        # There is intentionally no unsafe guessed restore, e.g. -1 or 0. Even a
        # setter exception can occur after native state changed: always restart.
        report["setter_attempted"] = report["restart_required"] = True
        with prevent_hooking_direct_calls():
            target.SetGameStageOverride(NewGameStageOverride=level)
        report["setter_returned"] = True
        report["after"] = [region_values(obj) for obj in regions]
        changed = []
        for before, after in zip(report["before"], report["after"]):
            if before["current"].get("outputs_valid") and after["current"].get("outputs_valid"):
                if before["current"]["out_parameters"] != after["current"]["out_parameters"]:
                    changed.append(after["region"]["path"])
        report["regions_with_changed_current_outputs"] = changed
        after_stage = report["after"][0]["current"]
        report["target_returned_requested_stage"] = (after_stage.get("outputs_valid") is True and
            after_stage.get("out_parameters", {}).get("GameStage") == level)
        report["interpretation_limit"] = "Query feasibility only; does not establish native offsets, spawns, rewards or persistence"
    except Exception as exc:
        report["error"] = safe_text(f"{type(exc).__name__}: {exc}")
    return report
