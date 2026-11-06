"""Raise unfinished UVHM mission stages; keep native rewards and encounter scaling."""
from __future__ import annotations

from collections import deque
from itertools import islice

import unrealsdk
from mods_base import get_pc
from unrealsdk.hooks import Type, add_hook, has_hook, prevent_hooking_direct_calls, remove_hook
from unrealsdk.unreal import UFunction, UObject

from .core import safe_text
from .reflection import read

ACCEPTED = (1, 2, 3)
SCAN_LIMIT = 2048
LOAD = {"ApplyMissionSaveGameData", "PopulateGameMissionDataFromSavegame",
        "SpawningProcessComplete", "WillowClientDisableLoadingMovie"}
POST = sorted(LOAD | {"AcceptMission", "ClientReceiveMissionStatus", "UpdateMissionStatus", "OnExpLevelChange"})
TARGETS = {
    "WillowPlayerController": {name: ("POST_UNCONDITIONAL",) for name in POST},
    "QuestAcceptGFxMovie": {"SetRewardCard": ("PRE",)},
}
TARGETS["WillowPlayerController"].update({
    "UpdateMissionStatus": ("PRE", "POST_UNCONDITIONAL"),
    "ServerCompleteMission": ("PRE",),
    "ServerGrantMissionRewards": ("PRE", "POST_UNCONDITIONAL"),
    "WillowClientShowLoadingMovie": ("PRE",),
})


class MissionScaling:
    def __init__(self, record=None):
        self.enabled = self.busy = self.installing = False
        self.record = record
        self.hooks, self.errors = {}, {}
        self.recent = deque(maxlen=32)
        self.changes = 0
        self.controller = None  # String identity only; never retain engine objects.
        self.payouts = {}
        self.scope = "disabled"
        self.last_boundary = None

    def enable(self):
        self.enabled = True
        self.install()
        try:
            self.sync(get_pc(possibly_loading=True), "mod_enabled")
        except Exception as exc:
            self.errors["enable"] = safe_text(exc)

    def disable(self):
        self.enabled = False
        for target, phase in self.hooks:
            try:
                remove_hook(target, getattr(Type, phase), "one_playthrough:missions:" + phase)
            except Exception as exc:
                self.errors["remove"] = safe_text(exc)
        self.payouts.clear()
        self.scope = "disabled; raised save stages are retained"

    def install(self):
        if self.installing:
            return
        self.installing = True
        try:
            for cls, functions in TARGETS.items():
                for name, phases in functions.items():
                    key = cls + ":" + name
                    try:
                        fn = unrealsdk.find_class(cls)._find(name)
                        if not isinstance(fn, UFunction):
                            raise ValueError("member is not a UFunction")
                        target = str(fn.Outer._path_name()) + ":" + str(fn.Name)
                        for phase in phases:
                            ident = "one_playthrough:missions:" + phase
                            if not has_hook(target, getattr(Type, phase), ident):
                                add_hook(target, getattr(Type, phase), ident, self.callback(name, phase))
                            self.hooks[target, phase] = has_hook(target, getattr(Type, phase), ident)
                        self.errors.pop(key, None)
                    except Exception as exc:
                        self.errors[key] = safe_text(exc)
        finally:
            self.installing = False

    def context(self, pc):
        local = get_pc(possibly_loading=True)
        if pc is None or local is None or pc._path_name() != local._path_name():
            self.scope = "local player unavailable or different controller"
            return None
        with prevent_hooking_direct_calls():
            playthrough = pc.GetCurrentPlaythrough()
        level = read(read(pc, "PlayerReplicationInfo"), "ExpLevel")
        if playthrough != 2 or read(pc, "OverpowerChoiceValue") != 0:
            self.scope = "outside UVHM/OP0"
            return None
        if not isinstance(level, int) or isinstance(level, bool) or level < 1:
            self.scope = "player level unavailable"
            return None
        path = str(pc._path_name())
        if self.controller != path:
            self.payouts.clear()
            self.recent.clear()
            self.controller = path
        self.scope = "UVHM/OP0"
        playthroughs = read(pc, "MissionPlaythroughs")
        if isinstance(playthroughs, dict) or len(playthroughs) < 3:
            raise ValueError("UVHM mission records unavailable")
        entries = read(playthroughs[2], "MissionList")
        if isinstance(entries, dict):
            raise ValueError("UVHM mission list unavailable")
        if len(entries) > SCAN_LIMIT:
            self.errors["scan_limit"] = "Mission list exceeds bounded scan; remaining records not changed"
        else:
            self.errors.pop("scan_limit", None)
        return level, entries

    def sync(self, pc, boundary, mission=None):
        if not self.enabled or self.busy:
            return
        self.busy = True
        self.last_boundary = boundary
        try:
            context = self.context(pc)
            if context is None:
                return
            level, entries = context
            write_failed = False
            selected = str(mission._path_name()) if isinstance(mission, UObject) else None
            if mission is not None and selected is None:
                return
            for entry in islice(entries, SCAN_LIMIT):
                obj = read(entry, "MissionDef")
                if not isinstance(obj, UObject):
                    continue
                path = str(obj._path_name())
                if selected is not None and path != selected:
                    continue
                if read(entry, "Status") not in ACCEPTED or path in self.payouts:
                    continue
                try:
                    self.raise_entry(obj, entry, level, boundary, path)
                except Exception as exc:
                    write_failed = True
                    self.errors["write"] = safe_text(path + ": " + str(exc))
            if not write_failed:
                self.errors.pop("write", None)
            self.errors.pop("context", None)
        except Exception as exc:
            self.errors["context"] = safe_text(exc)
        finally:
            self.busy = False

    def raise_entry(self, mission, entry, level, boundary, path):
        old_saved, old_definition = read(entry, "GameStage"), read(mission, "GameStage")
        locked = read(mission, "bGameStageLocked")
        if (not isinstance(old_saved, int) or isinstance(old_saved, bool) or old_saved < 1
                or not isinstance(old_definition, int) or isinstance(old_definition, bool)
                or old_definition < 0 or not isinstance(locked, bool)):
            raise ValueError("accepted mission stage/lock unavailable; left untouched")
        wanted = max(level, old_saved, old_definition)
        if wanted == old_saved == old_definition and locked:
            return
        try:
            if old_definition != wanted:
                mission.GameStage = wanted
            if not locked:
                mission.bGameStageLocked = True
            if old_saved != wanted:
                entry.GameStage = wanted
            if (read(entry, "GameStage"), read(mission, "GameStage"), read(mission, "bGameStageLocked")) != (wanted, wanted, True):
                raise RuntimeError("mission stage write did not read back")
        except Exception:
            # Roll back this callback's partial write, without overwriting a competing value.
            try:
                if old_saved != wanted and read(entry, "GameStage") == wanted:
                    entry.GameStage = old_saved
                if old_definition != wanted and read(mission, "GameStage") == wanted:
                    mission.GameStage = old_definition
                if not locked and read(mission, "bGameStageLocked") is True:
                    mission.bGameStageLocked = False
            except Exception as exc:
                self.errors["rollback"] = safe_text(exc)
            raise
        change = {"mission_path": safe_text(path), "saved_before": old_saved,
                  "definition_before": old_definition, "current": wanted,
                  "player_level": level, "boundary": boundary}
        self.changes += 1
        self.recent.append(change)
        if self.record is not None:
            try:
                self.record("mission:level_follow", change, [path])
            except Exception as exc:
                self.errors["record"] = safe_text(exc)

    @staticmethod
    def event_mission(args):
        # Explicit event identity only; never guess using the tracked mission.
        for field in ("Mission", "MissionDef"):
            value = read(args, field)
            if isinstance(value, UObject):
                return value
        data = read(args, "MissionStatusData")
        value = read(data, "Mission")
        return value if isinstance(value, UObject) else None

    def callback(self, name, phase):
        def on_event(obj, args, _ret, _fn):
            if not self.enabled:
                return None
            try:
                if name == "WillowClientShowLoadingMovie":
                    if read(args, "bShowMovie") is True:
                        self.payouts.clear()
                    return None
                pc = read(args, "WPC") if name == "SetRewardCard" else obj
                if not isinstance(pc, UObject):
                    return None
                mission = self.event_mission(args)
                boundary = name + ":" + phase
                if name == "ServerGrantMissionRewards":
                    path = str(mission._path_name()) if mission is not None else None
                    if phase == "PRE":
                        self.sync(pc, boundary, mission) if mission is not None else None
                        if path is not None and self.scope == "UVHM/OP0" and len(self.payouts) < 32:
                            self.payouts[path] = self.payouts.get(path, 0) + 1
                    elif str(pc._path_name()) == self.controller and path in self.payouts:
                        self.payouts[path] -= 1
                        if self.payouts[path] == 0:
                            del self.payouts[path]
                    return None
                if phase == "PRE":
                    if name != "UpdateMissionStatus" or read(args, "NewMissionStatus") == 4:
                        if mission is not None:
                            self.sync(pc, boundary, mission)
                elif name == "OnExpLevelChange":
                    if read(args, "bFeedback") is True or read(args, "bNaturalLevelup") is True:
                        self.sync(pc, boundary)
                elif name in LOAD:
                    self.sync(pc, boundary)
                    self.install()
                elif mission is not None:
                    self.sync(pc, boundary, mission)
            except Exception as exc:
                self.errors["callback:" + name] = safe_text(exc)
            return None
        return on_event

    def snapshot(self):
        # F10 must never call sync or mutate mission records.
        return {"enabled": self.enabled, "scope": self.scope,
                "policy": "unfinished accepted missions rise to player level; never lowered",
                "saved_stages_persist": True, "last_boundary": self.last_boundary,
                "change_count": self.changes, "recent_changes": list(self.recent),
                "errors": dict(self.errors), "reward_transactions": dict(self.payouts),
                "registered_hooks": [{"target": t, "phase": p, "registered": registered}
                                     for (t, p), registered in self.hooks.items()],
                "disable_policy": "raised mission stages remain in save; no guessed rollback"}
