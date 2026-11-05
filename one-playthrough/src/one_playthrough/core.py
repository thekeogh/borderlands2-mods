"""Bounded, engine-independent recording and crash-resistant JSON export."""

from __future__ import annotations

import json
import math
import os
import re
import tempfile
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

MAX_EVENTS = 192
MAX_TEXT = 384


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def safe_text(value):
    # Exceptions and engine strings can contain local paths/account identifiers.
    text = str(value)
    text = re.sub(r"(?:[A-Za-z]:[\\/]|/Users/|/home/)[^\s\"<>]*", "<local-path>", text)
    text = re.sub(r"\b\d{15,20}\b", "<identifier>", text)
    return text[:MAX_TEXT] + ("…[truncated]" if len(text) > MAX_TEXT else "")


def unavailable(reason):
    return {"available": False, "reason": safe_text(reason)}


def finite_number(value):
    if isinstance(value, float) and not math.isfinite(value):
        return unavailable("non-finite float")
    return value


class Recorder:
    """Stores JSON snapshots only: never engine objects."""

    def __init__(self):
        self.events = deque(maxlen=MAX_EVENTS)
        self.missions = {}  # path -> bounded recent observations for that mission
        self.mission_lifecycle = {}  # preserve accept/reward events against query churn
        self.ui = deque(maxlen=24)
        self.equipment = deque(maxlen=16)
        self.economy = deque(maxlen=32)
        self.combat = deque(maxlen=24)
        self.scaling = deque(maxlen=32)
        self.sequence = 0
        self.dropped_events = 0
        self.dropped_missions = 0

    def record(self, kind, payload, mission_paths=()):
        # Round-trip rejects live Unreal objects and non-finite floats at the boundary.
        payload = json.loads(json.dumps(payload, allow_nan=False))
        self.sequence += 1
        event = {"sequence": self.sequence, "utc": utc_now(), "kind": kind, "data": payload}
        if len(self.events) == MAX_EVENTS:
            self.dropped_events += 1
        self.events.append(event)
        if kind.startswith("ui:"):
            self.ui.append(event)
        if kind.startswith("equipment:"):
            self.equipment.append(event)
        if kind.startswith("economy:"):
            self.economy.append(event)
        if kind.startswith("combat:"):
            self.combat.append(event)
        if re.search(r"GetRegionGameStage|GetDefaultRegionGameStage|GetExpectedGameStage|GetGameStageFromRegion|GetLevelForMission", kind):
            self.scaling.append(event)
        for path in mission_paths:
            if path not in self.missions and len(self.missions) >= 32:
                oldest = next(iter(self.missions))
                del self.missions[oldest]
                self.mission_lifecycle.pop(oldest, None)
                self.dropped_missions += 1
            self.missions.setdefault(path, deque(maxlen=8)).append(event)
            if re.search(r"AcceptMission|ReceiveMissionStatus|CompleteMission|Receive.*Reward|GrantMissionRewards|Fanfare|SetGameStage", kind):
                self.mission_lifecycle.setdefault(path, deque(maxlen=8)).append(event)
        return event

    def clear_context(self):
        # Avoid mixing characters or playthroughs. Lifecycle hooks invoke this on travel too.
        self.missions.clear()
        self.mission_lifecycle.clear()
        self.ui.clear()
        self.equipment.clear()
        self.economy.clear()
        self.combat.clear()
        self.scaling.clear()
        self.events.clear()

    def snapshot(self):
        return {
            "events": list(self.events),
            "mission_observations": {k: list(v) for k, v in self.missions.items()},
            "mission_lifecycle": {k: list(v) for k, v in self.mission_lifecycle.items()},
            "recent_ui": list(self.ui),
            "recent_equipment": list(self.equipment),
            "recent_economy": list(self.economy),
            "recent_combat": list(self.combat),
            "scaling_queries": list(self.scaling),
            "limits": {"events": MAX_EVENTS, "missions": 32, "events_per_mission": 8,
                       "ui": 24, "equipment": 16, "economy": 32, "combat": 24, "scaling": 32},
            "dropped_events": self.dropped_events,
            "dropped_mission_histories": self.dropped_missions,
        }


def atomic_json(path, report):
    """Leave the previous valid report untouched if serialization or replacement fails."""
    path = Path(path)
    data = json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".report-", suffix=".tmp", delete=False) as stream:
            temp = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        # Windows scanners/readers can briefly lock a freshly written checkpoint.
        # Retry only access/sharing errors, with a fixed 350 ms total wait budget.
        for delay in (0.05, 0.10, 0.20, None):
            try:
                os.replace(temp, path)
                break
            except PermissionError:
                if delay is None:
                    raise
                time.sleep(delay)
    finally:
        if temp is not None and temp.exists():
            try:
                temp.unlink()
            except OSError:
                pass  # Cleanup failure must not hide the original commit error.


def new_report_path(directory, version):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    return Path(directory) / f"one-playthrough-{version}-{stamp}-{uuid4().hex[:8]}.json"


def compact_report(report):
    """Intern retained events once instead of repeating payloads across every section."""
    events = {}

    def visit(value):
        if isinstance(value, dict):
            if set(value) == {"sequence", "utc", "kind", "data"}:
                key = str(value["sequence"])
                events.setdefault(key, value)
                return {"event_ref": value["sequence"]}
            return {key: visit(item) for key, item in value.items()}
        if isinstance(value, list):
            return [visit(item) for item in value]
        return value

    result = visit(report)
    result["event_table"] = events
    result["event_reference_format"] = "event_ref is a sequence key in event_table; each payload is stored once"
    return result
