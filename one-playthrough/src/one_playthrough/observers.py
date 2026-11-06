"""Focused SDK observers: no gameplay edits and no pickup polling/physics hooks."""
from __future__ import annotations

import re
import time
from itertools import islice

import unrealsdk
from mods_base import get_pc
from unrealsdk.hooks import Type, add_hook, has_hook, remove_hook
from unrealsdk.unreal import UFunction, UObject, WrappedArray, WrappedStruct

from .activity import transaction_resources
from .core import Recorder, safe_text
from .reflection import Snapshot, identity, property_names, read

# Exact candidates evidenced by 0.1.2 reflection/observations. Missing functions
# are reported; registration is never interpreted as proof of execution.
TARGETS = {
    "WillowPlayerController": (
        "AcceptMission", "ClientReceiveMissionStatus", "UpdateMissionStatus",
        "ApplyMissionSaveGameData", "PopulateGameMissionDataFromSavegame",
        "ServerCompleteMission", "ServerGrantMissionRewards",
        "ReceiveWeaponReward", "ReceiveItemReward", "ClientDoMissionStatusFanfare",
        "PopulateMissionDataFromStatus",
        "SpawningProcessComplete", "WillowClientDisableLoadingMovie", "WillowClientShowLoadingMovie",
    ),
    "MissionDefinition": ("GetExpectedGameStage", "GetExperienceReward", "GetCurrencyReward"),
    "WillowPlayerReplicationInfo": ("AddCurrencyOnHand", "SetCurrencyOnHand"),
    "WillowPlayerPawn": ("TakeDamage", "Died"),
    "WillowInventoryManager": ("AddInventory", "RemoveInventory"),
    "QuestAcceptGFxMovie": ("SetRewardCard", "SetRewardsXP", "SetRewardsTotalCredits", "extCompleteConfirmed"),
    "StatusMenuExGFxMovie": ("SetRewardCard", "SetRewardsXP", "SetRewardsTotalCredits", "SetActiveMission", "UpdateMissionDetails"),
    "MissionRewardGFxObject": ("SetPendingMissionRewardData",),
    "WillowHUDGFxMovie": ("DoMissionStatusFanfare",),
    "HUDWidget_Missions": ("SetDisplayedMission",),
    "FrontendGFxMovie": ("NotifyAtMainMenu",),
}
UI = re.compile(r"GFxMovie|GFxObject|HUDWidget|Fanfare|PopulateMissionData", re.I)
CRITICAL = re.compile(r"Mission|Reward|Fanfare|Loading|Spawning|MainMenu|Currency|Died", re.I)
COMBAT_EVENT = re.compile(r"^(?:TakeDamage|Died|ServerMeleeAttack)$")
ECONOMY = re.compile(r"^(?:AddCurrencyOnHand|SetCurrencyOnHand|HandlePickup|PickedUpBy|GiveTo|AddExperience)$")
TRANSACTION = re.compile(r"Reward|ServerCompleteMission|extCompleteConfirmed|Currency|HandlePickup|PickedUpBy|GiveTo|AddExperience", re.I)
TRAVEL_START = {"WillowClientShowLoadingMovie", "NotifyAtMainMenu"}
RETRY = {"SpawningProcessComplete", "WillowClientDisableLoadingMovie"}


def mission_paths(value, depth=0):
    if depth > 3:
        return set()
    if isinstance(value, UObject):
        try:
            if value.Class._inherits(unrealsdk.find_class("MissionDefinition")):
                return {str(value._path_name())}
            # Do not scan UI objects on the gameplay hot path. Actual mission
            # arguments/returns and the MissionDefinition caller identify events.
        except Exception:
            pass
    if isinstance(value, (WrappedArray, list, tuple)):
        return set().union(*(mission_paths(v, depth + 1) for v in islice(value, 4)))
    if isinstance(value, WrappedStruct):
        result = set()
        for name in property_names(value, 32):
            if name.lower() != "returnvalue":
                result.update(mission_paths(getattr(value, name), depth + 1))
        return result
    return set()


class Observers:
    def __init__(self):
        self.recorder = Recorder()
        self.status, self.pending, self.discovery = {}, {}, {}
        self.enabled = self.collecting = self.armed = self._observing = self._installing = False
        self.capture_callback = None
        self.tuning = None
        self.mission_scaling = None
        self._last = {}

    def enable(self):
        self.enabled = True
        self.install()
        self.recorder.record("enabled", {"tuning": self.tuning.snapshot() if self.tuning else None,
                                         "capture_policy": "focused lightweight observers"})

    def disable(self):
        self.enabled = self.armed = False
        for target, status in self.status.items():
            for phase in status.get("phases", []):
                try:
                    remove_hook(target, getattr(Type, phase), f"one_playthrough:{phase}")
                except Exception as exc:
                    status["remove_error"] = safe_text(exc)
        self.recorder.clear_context()

    def install(self):
        if self._installing:
            return
        self._installing = True
        try:
            for class_name, candidates in TARGETS.items():
                try:
                    cls = unrealsdk.find_class(class_name)
                    if UI.search(class_name):
                        self.discovery[class_name] = str(cls._path_name())
                    for name in candidates:
                        self._install_one(cls, name)
                except Exception as exc:
                    self.pending[class_name] = safe_text(f"{type(exc).__name__}: {exc}")
        finally:
            self._installing = False

    def _install_one(self, cls, name):
        candidate = f"{cls.Name}:{name}"
        try:
            function = cls._find(name)
            if not isinstance(function, UFunction):
                raise ValueError("reflected member is not a UFunction")
            target = str(function.Outer._path_name()) + ":" + str(function.Name)
            if target.count(":") != 1 or "." not in target.partition(":")[0]:
                raise ValueError(f"unsupported reflected function owner: {target}")
            status = self.status.setdefault(target, {"reflected": True, "hits": 0, "sampled": 0, "phases": []})
            props = list(islice(function._properties(), 48))
            status["parameters"] = [{"name": str(p.Name), "type": str(p.Class.Name), "flags": int(p.PropertyFlags)} for p in props]
            input_names = [str(p.Name) for p in props if int(p.PropertyFlags) & 128 and not int(p.PropertyFlags) & 1024]
            status["has_return"] = any(int(p.PropertyFlags) & 1024 for p in props)
            phases = ["POST_UNCONDITIONAL"]
            if TRANSACTION.search(name) or COMBAT_EVENT.search(name) or re.search(r"AcceptMission|ReceiveMissionStatus|UpdateMissionStatus|GetExpectedGameStage|GetLevelForMission|GetGameStageFromRegion|^SetGameStage$", name):
                phases.insert(0, "PRE")
            for phase in phases:
                ident = f"one_playthrough:{phase}"
                if not has_hook(target, getattr(Type, phase), ident):
                    add_hook(target, getattr(Type, phase), ident, self._callback(target, name, phase, input_names))
                if has_hook(target, getattr(Type, phase), ident):
                    if phase not in status["phases"]:
                        status["phases"].append(phase)
                else:
                    status["registration_error"] = "SDK did not confirm hook registration"
            self.pending.pop(candidate, None)
        except Exception as exc:
            self.pending[candidate] = safe_text(f"{type(exc).__name__}: {exc}")

    def _callback(self, target, name, phase, input_names=None):
        def observe(obj, args, ret, _func):
            if not self.enabled or self.collecting or self._observing:
                return None
            status = self.status[target]
            status["hits"] += 1
            started = time.perf_counter()
            # Reject hot repeated calls BEFORE reflection, snapshots or player reads.
            key = (target, phase)
            now = time.monotonic()
            if not CRITICAL.search(name) and now - self._last.get(key, -1) < 0.3:
                status["throttled"] = status.get("throttled", 0) + 1
                return None
            self._last[key] = now
            self._observing = True
            try:
                if name == "NotifyAtMainMenu" or (name == "WillowClientShowLoadingMovie" and read(args, "bShowMovie") is True):
                    self.recorder.clear_context()
                snap = Snapshot(max_nodes=80, max_depth=4, max_fields=12, max_array=3)
                names = input_names if input_names is not None else property_names(args, 24)
                values = {n: snap.value(read(args, n)) for n in names[:12] if n != "ReturnValue"}
                paths = mission_paths(args) | mission_paths(ret)
                if not paths:
                    paths = mission_paths(obj)
                pc = get_pc(possibly_loading=True)
                pri = read(pc, "PlayerReplicationInfo")
                payload = {"target": target, "phase": phase, "object": identity(obj), "arguments": values,
                           "observed_return": (snap.value(ret) if status.get("has_return", ret is not None and not isinstance(ret, type))
                                               else {"kind": "void_or_unset"}) if phase != "PRE" else None,
                           "return_provenance": "observed SDK pipeline; other mods may override it",
                           "mission_state_at_event": self._mission_state(paths),
                           "player_xp_level_at_event": snap.value(read(pri, "ExpLevel")),
                           "errors": snap.errors, "truncations": snap.truncations}
                if TRANSACTION.search(name):
                    payload["player_resources_at_event"] = transaction_resources(pc)
                kind = "ui:" if UI.search(target) else "engine:"
                if "Inventory" in target or "ReceiveWeaponReward" in name or "ReceiveItemReward" in name:
                    kind = "equipment:"
                if ECONOMY.search(name):
                    kind = "economy:"
                if COMBAT_EVENT.search(name):
                    kind = "combat:"
                    payload["event_object_state"] = {"object": identity(obj), "fields": {
                        field: snap.value(read(obj, field)) for field in ("ExpLevel", "GameStage")}}
                    payload["combat_participants"] = [{"argument": n, "actor": {"object": identity(read(args, n)),
                        "fields": {"ExpLevel": snap.value(read(read(args, n), "ExpLevel"))}}}
                        for n in names[:12] if re.search(r"instigat|killer|pawn", n, re.I) and isinstance(read(args, n), UObject)][:3]
                self.recorder.record(kind + name, payload, sorted(paths))
                status["sampled"] += 1
                elapsed = (time.perf_counter() - started) * 1000
                status["max_sample_ms"] = round(max(status.get("max_sample_ms", 0), elapsed), 3)
                if name in RETRY:
                    self.install()
                    if self.tuning is not None:
                        self.tuning.install()
                if self.armed and self._is_mission_screen(target, paths) and phase != "PRE":
                    self.armed = False
                    if self.capture_callback is not None:
                        self.capture_callback("armed_mission_screen")
            except Exception as exc:
                status["last_observer_error"] = safe_text(f"{type(exc).__name__}: {exc}")
            finally:
                self._observing = False
            return None
        return observe

    @staticmethod
    def _is_mission_screen(target, paths):
        return (bool(paths) and "PopulateMissionDataFromStatus" in target) or "QuestAcceptGFxMovie:SetRewardCard" in target or bool(re.search(
            r"(?:Mission.*(?:GFxMovie|Provider)|GFxMovie.*Mission).*?(?:Display|Populate|Set|Show|Init|Update)", target, re.I))

    @staticmethod
    def _mission_state(paths):
        results = []
        for path in sorted(paths)[:3]:
            try:
                mission = unrealsdk.find_object("MissionDefinition", path)
                snap = Snapshot(max_nodes=12)
                results.append({"mission_path": safe_text(path), "definition_stage": snap.value(read(mission, "GameStage")),
                                "definition_locked": snap.value(read(mission, "bGameStageLocked")),
                                "region": snap.value(read(mission, "GameStageRegion"))})
            except Exception as exc:
                results.append({"mission_path": safe_text(path), "error": safe_text(exc)})
        return results

    def snapshot(self):
        registered = {}
        for target, status in self.status.items():
            result = dict(status)
            result["registered_now"] = {phase: has_hook(target, getattr(Type, phase), f"one_playthrough:{phase}") for phase in status["phases"]}
            registered[target] = result
        hits = sum(v["hits"] for v in self.status.values())
        tuning = self.tuning.snapshot() if self.tuning is not None else None
        changed = bool(tuning and tuning["owns_edit"])
        active = changed and tuning["current"] == 1
        missions = self.mission_scaling.snapshot() if self.mission_scaling is not None else None
        mission_active = bool(missions and missions["enabled"] and missions["scope"] == "UVHM/OP0")
        differences = ([{"object": tuning["object"], "field": tuning["field"],
                         "original": tuning["original"], "current": tuning["current"]}] if changed else [])
        return {"enabled": self.enabled, "hooks": registered, "pending_or_unavailable": dict(self.pending),
                "discovered_mission_classes": dict(self.discovery), "discovered_ui_classes": dict(self.discovery),
                "native_pipeline_hits": hits, "hook_health": "events observed" if hits else "no events observed yet",
                "active_corrections": (["UVHM tuning activation threshold 50 to 1"] if active else [])
                                      + (["accepted mission stages follow player level"] if mission_active else []),
                "original_current_differences": differences,
                "gameplay_writes": changed or bool(missions and missions["change_count"]),
                "uvhm_threshold": tuning,
                "mission_scaling": missions,
                "capture_next_ui_armed": self.armed,
                "capture_policy": "exact targets; no pickup polling/physics hooks; compact event snapshots"}
