"""One Playthrough: native UVHM tuning below 50, with disk diagnostics."""

from __future__ import annotations

import time

from mods_base import ButtonOption, CoopSupport, Game, build_mod, keybind

from .diagnostics import Diagnostics
from .observers import Observers
from .missions import MissionScaling
from .tuning import UVHMTuning
from .version import AUTHOR, DISPLAY_NAME, VERSION

__version__ = VERSION
__author__ = AUTHOR

export_status = ButtonOption(
    "export_status", display_name="JSON export status / location",
    description="Reports go to sdk_mods/settings/one_playthrough/diagnostics/. No console needed.",
)


def notify(title, message, failed=False):
    export_status.description = f"{title}: {message}"
    try:
        from ui_utils import show_hud_message
        show_hud_message(DISPLAY_NAME, title + "\n" + message, duration=7.0 if failed else 4.0)
    except Exception:
        # HUD may not exist in menus/loading. The mod-menu status remains available.
        pass


observers = Observers()
tuning = UVHMTuning()
observers.tuning = tuning
missions = MissionScaling(observers.recorder.record)
observers.mission_scaling = missions
diagnostics = Diagnostics(observers, notify)
observers.capture_callback = diagnostics.export


@keybind("export_diagnostics", "F10", display_name="Export JSON diagnostics")
def capture():
    now = time.monotonic()
    if now - diagnostics.last_press >= 0.5:
        diagnostics.last_press = now
        diagnostics.export()


def arm(_option):
    if not observers.enabled:
        notify("Enable One Playthrough first", "Then arm capture and open the mission screen.", True)
        return
    observers.armed = True
    notify("Capture armed", "Open the affected mission screen. The next observed mission UI event exports JSON.")


capture_next_screen = ButtonOption(
    "capture_next_screen", display_name="Capture next mission screen",
    description="If F10 is intercepted: arm this, then open the affected mission screen. "
                "Captures the next observed mission card automatically.",
    on_press=arm,
)
export_now = ButtonOption(
    "export_now", display_name="Export JSON now",
    description="Same disk export as F10. Recent mission UI events remain in the report.",
    on_press=lambda _option: diagnostics.export("mod_options"),
)
def on_enable():
    tuning.enable()
    observers.enable()
    missions.enable()


def on_disable():
    missions.disable()
    observers.disable()
    tuning.disable()
    notify("Restart required", "UVHM threshold restoration attempted. Quit/restart to clear existing actor effects.",
           failed=tuning.restart_required)


mod = build_mod(
    name=DISPLAY_NAME, author=AUTHOR, version=VERSION,
    supported_games=Game.BL2, coop_support=CoopSupport.Incompatible,
    description=f"{VERSION}: native UVHM from level 1; accepted missions follow your level. "
                "Requires a patched EXE and genuine UVHM save. F10 exports JSON. "
                "Enable before loading; restart after disabling. Solo only.",
    keybinds=[capture], options=[capture_next_screen, export_now, export_status],
    hooks=[], commands=[], on_enable=on_enable, on_disable=on_disable,
)
