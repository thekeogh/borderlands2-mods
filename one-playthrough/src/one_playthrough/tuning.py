"""Activate the existing UVHM tuning entry below 50; retain all native values."""
from __future__ import annotations

import unrealsdk
from unrealsdk.hooks import Type, add_hook, has_hook, remove_hook
from unrealsdk.unreal import UFunction

from .core import safe_text
from .reflection import read

PATH = "GD_Playthrough3Tuning.Balance.BalanceMod_PT3"
TARGETS = {
    "WillowPlayerController": ("ApplyMissionSaveGameData", "PopulateGameMissionDataFromSavegame",
                               "SpawningProcessComplete", "WillowClientDisableLoadingMovie"),
    "PopulationFactoryBalancedAIPawn": ("CreatePopulationActor", "RestorePopulatedAIPawn"),
    "PopulationFactoryWillowVehicle": ("CreatePopulationActor",),
    "WillowAIPawn": ("SetExpLevel",),
}


class UVHMTuning:
    def __init__(self):
        self.enabled = False
        self.owns_edit = False
        self.state = "disabled"
        self.hooks = {}
        self.errors = {}
        self.original = None
        self.last_boundary = None
        self.restart_required = False

    def enable(self):
        self.enabled = True
        self.install()
        self.apply("mod_enabled")

    def install(self):
        for cls_name, names in TARGETS.items():
            for name in names:
                key = cls_name + ":" + name
                try:
                    function = unrealsdk.find_class(cls_name)._find(name)
                    if not isinstance(function, UFunction):
                        raise ValueError("member is not a UFunction")
                    target = str(function.Outer._path_name()) + ":" + str(function.Name)
                    # Before spawn/restore consumers, and once more after load boundaries
                    # if their asset wasn't loaded when the PRE callback ran.
                    for phase in ("PRE", "POST_UNCONDITIONAL"):
                        ident = "one_playthrough:tuning:" + phase
                        if not has_hook(target, getattr(Type, phase), ident):
                            add_hook(target, getattr(Type, phase), ident, self._callback(target, phase))
                        self.hooks[(target, phase)] = has_hook(target, getattr(Type, phase), ident)
                    self.errors.pop(key, None)
                except Exception as exc:
                    self.errors[key] = safe_text(exc)

    def _callback(self, target, phase):
        def callback(_obj, _args, _ret, _func):
            if self.enabled:
                self.apply(target + ":" + phase)
            return None
        return callback

    @staticmethod
    def rows():
        obj = unrealsdk.find_object("BalanceModifierDefinition", PATH)
        rows = read(obj, "BalanceModifiers")
        if isinstance(rows, dict) or len(rows) != 3:
            raise ValueError("UVHM tuning layout differs from captured build")
        if [read(row, "MinEffectiveLevel") for row in rows][1:] != [61, 73]:
            raise ValueError("UVHM later thresholds differ from captured build")
        return rows

    def apply(self, boundary):
        if not self.enabled:
            return
        self.last_boundary = boundary
        try:
            rows = self.rows()
            current = read(rows[0], "MinEffectiveLevel")
            if current == 1:
                self.state = "active" if self.owns_edit else "already 1; owned by another source"
                return
            if current != 50:
                self.state = "conflict; unexpected first threshold left untouched"
                return
            # This asset belongs to UVHM. No other playthrough table is edited.
            # A reloaded copy of the asset may need the same one-field correction.
            self.original = 50
            self.owns_edit = True  # Set before writing so a failed readback can restore.
            rows[0].MinEffectiveLevel = 1
            if read(rows[0], "MinEffectiveLevel") != 1:
                raise RuntimeError("threshold write did not read back as 1")
            self.state = "active"
            self.errors.pop("apply", None)
        except Exception as exc:
            self.state = "pending or unavailable"
            self.errors["apply"] = safe_text(exc)

    def disable(self):
        self.enabled = False
        for (target, phase), _registered in self.hooks.items():
            try:
                remove_hook(target, getattr(Type, phase), "one_playthrough:tuning:" + phase)
            except Exception as exc:
                self.errors["remove:" + target + ":" + phase] = safe_text(exc)
        if self.owns_edit:
            try:
                rows = self.rows()
                current = read(rows[0], "MinEffectiveLevel")
                if current == 1:
                    rows[0].MinEffectiveLevel = self.original
                elif current != self.original:
                    raise RuntimeError("another source changed the threshold; not overwritten")
                if read(rows[0], "MinEffectiveLevel") != self.original:
                    raise RuntimeError("threshold restoration readback failed")
                self.owns_edit = False
            except Exception as exc:
                self.restart_required = True
                self.errors["restore"] = safe_text(exc)
        self.state = "disabled; restart game before continuing"

    def snapshot(self):
        current = None
        try:
            current = read(self.rows()[0], "MinEffectiveLevel")
        except Exception:
            pass
        return {"enabled": self.enabled, "state": self.state,
                "object": PATH, "field": "BalanceModifiers[0].MinEffectiveLevel",
                "original": self.original, "current": current, "owns_edit": self.owns_edit,
                "last_boundary": self.last_boundary, "errors": dict(self.errors),
                "registered_hooks": [{"target": target, "phase": phase, "registered": registered}
                                     for (target, phase), registered in self.hooks.items()],
                "restart_required": self.restart_required,
                "disable_policy": "restore owned threshold; restart to clear existing actor effects",
                "exe_patch": "external prerequisite; not applied or verified by this module"}
