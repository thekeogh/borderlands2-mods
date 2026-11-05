"""Observational collection. No stage setters, package loads, saves, or mutations."""

from __future__ import annotations

import hashlib
import re
import sys
from itertools import islice

import mods_base
import unrealsdk
from mods_base import get_pc
from unrealsdk.hooks import prevent_hooking_direct_calls
from unrealsdk.unreal import UObject

from .core import atomic_json, compact_report, new_report_path, safe_text, unavailable, utc_now
from .activity import equipped_gear, player_resources
from .reflection import Snapshot, identity, property_names, read
from .version import AUTHOR, MOD_ID, VERSION

STAGES = re.compile(r"stage|level|region|balance|boost|formula|mission", re.I)
INITIALIZER_FIELDS = re.compile(r"^(?:BaseValueMode|RoundingMode|ValueFormula|ConditionalInitialization|RandomVariance|RangeRestriction)$")
ACTOR = re.compile(r"stage|level|balance|health|shield|regen|badass|boss|damage", re.I)
EQUIPMENT = re.compile(r"stage|level|grade|balance|definition|price|cost|cash|money", re.I)
UI_FIELDS = re.compile(r"mission|reward|difficulty|level|stage|displayed|title", re.I)


def known_query(obj, name):
    """Only used for the independently documented zero-argument playthrough query."""
    if obj is None:
        return unavailable("player controller not loaded")
    try:
        obj.Class._find(name)
        with prevent_hooking_direct_calls():
            return getattr(obj, name)()
    except Exception as exc:
        return unavailable(f"{name}: {type(exc).__name__}: {exc}")


def sample_class(class_name, pattern, limit=8, scan_limit=96, reference_location=None, live_only=False):
    """Samples loaded instances only; no forced loads or full actor graph traversal."""
    items = []
    scanned = 0
    excluded = 0
    try:
        unrealsdk.find_class(class_name)
        candidates = []
        for obj in islice(unrealsdk.find_all(class_name, exact=False), scan_limit):
            scanned += 1
            path = str(obj._path_name())
            if "Default__" in path or (live_only and ".TheWorld:" not in path):
                excluded += 1
                continue
            distance = None
            if reference_location is not None:
                location = read(obj, "Location")
                if not isinstance(location, dict):
                    distance = sum((float(getattr(location, axis)) - reference_location[i]) ** 2
                                   for i, axis in enumerate(("X", "Y", "Z")))
            candidates.append((distance, obj))
        if reference_location is not None:
            candidates.sort(key=lambda pair: float("inf") if pair[0] is None else pair[0])
        elif re.search(r"GFxMovie|HUDWidget", class_name):
            candidates.sort(key=lambda pair: int(re.search(r"_(\d+)$", str(pair[1]._path_name())).group(1))
                            if re.search(r"_(\d+)$", str(pair[1]._path_name())) else -1, reverse=True)
        for distance, obj in candidates[:limit]:
            item = Snapshot().object(obj, pattern)
            if reference_location is not None:
                item["distance_squared"] = Snapshot().value(distance)
            items.append(item)
        return {"items": items, "scanned": scanned, "sample_limit": limit,
                "excluded_templates_or_non_world_objects": excluded,
                "scan_limit": scan_limit, "scan_limit_reached": scanned == scan_limit,
                "truncated": len(candidates) > limit or scanned == scan_limit,
                "coverage": "loaded objects within bounded scan; not every object in the map"}
    except Exception as exc:
        return {"items": items, "scanned": scanned, **unavailable(f"{class_name}: {type(exc).__name__}: {exc}")}


class Diagnostics:
    def __init__(self, observers, notify):
        self.observers = observers
        self.notify = notify
        self.directory = mods_base.SETTINGS_DIR / MOD_ID / "diagnostics"
        self.last_result = "No report exported yet."
        self.last_press = float("-inf")

    def export(self, trigger="F10"):
        if self.observers.collecting:
            return None
        self.observers.collecting = True
        path = new_report_path(self.directory, VERSION)
        report = {
            "schema_version": 4, "utc": utc_now(), "mod_version": VERSION, "author": AUTHOR,
            "trigger": trigger, "build_kind": "native UVHM from level 1; early access; external EXE patch required",
            "capture_mode": "observational",
            "export_complete": False, "partial": True, "errors": [],
            "limitations": ["Only the first UVHM tuning activation threshold is corrected by this build.",
                            "Observed query returns may include other mods' overrides; no native bypass is claimed.",
                            "Gameplay, hook firing, UI routing and scaling require in-game validation.",
                            "The executable's patch status cannot be established by this report."],
            "versions": {"python": sys.version.split()[0],
                         "mods_base": getattr(mods_base, "__version__", unavailable("not exposed")),
                         "unrealsdk": getattr(unrealsdk, "__version__", unavailable("not exposed")),
                         "game_build": unavailable("not exposed by a verified API")},
            "sections": {},
        }
        phase = "initial_checkpoint"
        try:
            # Commit useful evidence before touching optional engine objects.
            report["implementation"] = self.observers.snapshot()
            report["history"] = self.observers.recorder.snapshot()
            atomic_json(path, compact_report(report))
            phase = "collection"
            try:
                pc = get_pc(possibly_loading=True)
            except Exception as exc:
                pc = None
                report["errors"].append(safe_text(f"get_pc: {exc}"))
            collectors = {
                "player_session": lambda: self.player(pc),
                "player_resources": lambda: player_resources(pc),
                "equipped_gear": lambda: equipped_gear(pc),
                "mission_comparison": lambda: self.missions(pc, report["history"]),
                "mission_ui": lambda: self.ui(report["history"]),
                "regional_scaling": lambda: self.regions(pc),
                "uvhm_tuning": self.tuning,
                "nearby_enemies": lambda: self.enemies(pc),
                "equipment_economy": lambda: self.economy(report["history"]),
                "combat": lambda: {"recent_events": report["history"]["recent_combat"],
                                    "provenance": "observed damage/death arguments and reflected state; no damage calculation override"},
                "rewards": lambda: {"recent_reward_and_equipment_events": report["history"]["recent_equipment"],
                                    "configuration": "See Reward fields for each mission in mission_comparison.",
                                    "xp_currency_events": report["history"]["recent_economy"],
                                    "xp_cash_paid": unavailable("inspect observed PRE/POST values and payloads; no inferred payout or payout function called")},
            }
            for section, collect in collectors.items():
                try:
                    report["sections"][section] = collect()
                except Exception as exc:
                    error = safe_text(f"{section}: {type(exc).__name__}: {exc}")
                    report["errors"].append(error)
                    report["sections"][section] = unavailable(error)
                # The initial valid history checkpoint survives interruption. Avoid
                # rewriting the entire report after every optional section.
            report["export_complete"] = True
            # Distinguish a functioning export from functioning engine observers.
            report["hook_health"] = self.observers.snapshot()["hook_health"]
            report["partial"] = bool(report["errors"]) or self._has_unavailable(report["sections"])
            report["finished_utc"] = utc_now()
            phase = "final_commit"
            atomic_json(path, compact_report(report))
            self.last_result = f"Saved {path}" + (" (partial evidence)" if report["partial"] else "")
            self.notify("JSON saved", f"{path.name}\nsdk_mods/settings/{MOD_ID}/diagnostics/", False)
            return path
        except Exception as exc:
            # Preserve the checkpoint. A new filename can bypass a locked existing
            # destination and records the actual failure, including Windows codes.
            failure = {"phase": phase, "type": type(exc).__name__, "message": safe_text(exc),
                       "errno": getattr(exc, "errno", None), "winerror": getattr(exc, "winerror", None)}
            report["errors"].append(failure)
            report["partial"] = True
            report["export_complete"] = phase == "final_commit"
            report["export_recovery"] = {"original_filename": path.name, "used_new_filename": True}
            recovery = path.with_name(path.stem + "-recovered.json")
            try:
                atomic_json(recovery, compact_report(report))
                self.last_result = f"JSON recovered after {type(exc).__name__} during {phase}: {recovery}"
                self.notify("JSON recovered (export warning)", self.last_result, False)
                return recovery
            except Exception as recovery_exc:
                self.last_result = (f"JSON export failed: {safe_text(type(exc).__name__ + ': ' + str(exc))}. "
                                    f"Recovery failed: {safe_text(recovery_exc)}. Destination: {path}")
            self.notify("JSON export failed", self.last_result, True)
            return None
        finally:
            self.observers.collecting = False

    @staticmethod
    def _has_unavailable(value):
        if isinstance(value, dict):
            if value.get("available") is False or value.get("errors") or value.get("error") or value.get("truncations") or value.get("truncated"):
                return True
            return any(Diagnostics._has_unavailable(v) for v in value.values())
        if isinstance(value, list):
            return any(Diagnostics._has_unavailable(v) for v in value)
        return False

    def player(self, pc):
        if pc is None:
            return unavailable("No local player controller: menu or loading state")
        snap = Snapshot()
        pri = read(pc, "PlayerReplicationInfo")
        playthrough = known_query(pc, "GetCurrentPlaythrough")
        exp_level = snap.value(read(pri, "ExpLevel")) if isinstance(pri, UObject) else pri
        op = snap.value(read(pc, "OverpowerChoiceValue"))
        character = read(pc, "SaveGameId")
        character = ("sha256:" + hashlib.sha256(("one-playthrough:" + str(character)).encode()).hexdigest()[:16]
                     if isinstance(character, int) else unavailable("stable local character ID not exposed in verified controller field"))
        world = read(pc, "WorldInfo")
        status = "UVHM confirmed" if playthrough == 2 else "Outside UVHM or playthrough unavailable"
        if isinstance(op, int) and op != 0:
            status = "Non-zero OP selection: outside first-version scope"
        return {"actual_xp_level": exp_level, "playthrough_index": playthrough,
                "selected_op": op, "scope": status, "character_fingerprint": character,
                "map_world": identity(world) if isinstance(world, UObject) else world,
                "player_pawn": Snapshot().value(read(pc, "Pawn")),
                "controller_scaling_fields": Snapshot().fields(pc, pattern=re.compile(
                    r"stage|level|playthrough|overpower|weapon.*slot|slot.*weapon", re.I)),
                "owned_inventory": "intentionally not dumped",
                "maximum_level": unavailable("no cap edits; installed cap not established by a verified read")}

    def missions(self, pc, history):
        records = {}
        total = None
        note = None
        if pc is not None:
            playthrough = known_query(pc, "GetCurrentPlaythrough")
            entries = read(pc, "MissionPlaythroughs")
            if isinstance(playthrough, int) and not isinstance(entries, dict) and 0 <= playthrough < len(entries):
                mission_list = read(entries[playthrough], "MissionList")
                if not isinstance(mission_list, dict):
                    total = len(mission_list)
                    for entry in islice(mission_list, 512):
                        mission = read(entry, "MissionDef")
                        if isinstance(mission, UObject):
                            records[str(mission._path_name())] = {
                                "status": Snapshot().value(read(entry, "Status")),
                                "stored_stage": Snapshot().value(read(entry, "GameStage")),
                            }
                else:
                    note = mission_list
            else:
                note = unavailable("current playthrough mission records unavailable")
        # Most recently observed mission first, then active records, then other records.
        paths = list(reversed(history["mission_observations"]))
        paths += [p for p, r in records.items() if r["status"] in (1, 2, 3)]
        paths += list(records)
        selected = list(dict.fromkeys(paths))[:32]
        items = []
        for path in selected:
            item = {"mission_path": safe_text(path),
                    "player_record": records.get(path, unavailable("no saved record found within bounded scan")),
                    "correction": unavailable("no mission correction; observing native records"),
                    "observed_events_for_same_mission": history["mission_observations"].get(path, []),
                    "lifecycle_events": history.get("mission_lifecycle", {}).get(path, []),
                    "displayed_level": unavailable("read the same mission's captured UI payload; not inferred from definition"),
                    "native_unmodified_query": unavailable("no verified bypass of other SDK hooks")}
            observations = history["mission_observations"].get(path, [])
            item["observed_level_queries"] = [
                {"target": e["data"].get("target"), "phase": e["data"].get("phase"),
                 "return": e["data"].get("observed_return"),
                 "mission_state": e["data"].get("mission_state_at_event"), "utc": e["utc"]}
                for e in observations if re.search(r"Get.*(?:Stage|Level)", e["data"].get("target", ""))
                and not e["data"].get("target", "").endswith(":GetLevelForMission")]
            try:
                mission = unrealsdk.find_object("MissionDefinition", path)
                item["definition_stage"] = Snapshot().value(read(mission, "GameStage"))
                item["definition_stage_locked"] = Snapshot().value(read(mission, "bGameStageLocked"))
                item["definition_and_rewards"] = Snapshot().object(mission)
                region_fields = {}
                for name in property_names(mission):
                    if "region" in name.lower():
                        region = read(mission, name)
                        region_fields[name] = (Snapshot().object(region, STAGES) if isinstance(region, UObject)
                                               else Snapshot().value(region))
                        if len(region_fields) >= 4:
                            break
                item["regions"] = region_fields or unavailable("no reflected mission region reference")
                item["acceptance_lock"] = records.get(path, unavailable("not in captured player records"))
            except Exception as exc:
                item["definition"] = unavailable(f"{type(exc).__name__}: {exc}")
            items.append(item)
        return {"items": items, "saved_record_count": total,
                "record_scan_limit": 512, "mission_sample_limit": 32,
                "truncated": (total is not None and total > 512) or len(set(paths)) > 32,
                "record_access_note": note,
                "acceptance_policy": "observing existing game records only; no writes, migration or sidecar locks"}

    def ui(self, history):
        screens = [name for name in self.observers.discovery if re.search(r"GFxMovie|GFxObject|Provider", name, re.I)]
        screens = list(dict.fromkeys(["QuestAcceptGFxMovie", "HUDWidget_Missions"] + screens))[:16]
        return {"recent_events": history["recent_ui"], "current_screens": {
            name: sample_class(name, UI_FIELDS, 2, 12) for name in
            screens},
            "discovery": dict(self.observers.discovery),
            "input_route": "SDK keybind: WillowGame.WillowUIInteraction:InputKey PRE",
            "screen_input_verified": False,
            "fallback": "Arm Capture next mission screen in mod options, then open the affected screen.",
            "flash_rendered_text": unavailable("no verified read of the rendered Flash text; event payloads are evidence, not proof of displayed text")}


    def regions(self, pc):
        # 0.1.0 found only a saved PT0 region stage (1) while actual UVHM missions
        # were 50. Keep the playthrough index and relevant region bounds explicit.
        saved = read(pc, "RegionGameStages")
        paths = set()
        if not isinstance(saved, dict):
            for entry in islice(saved, 128):
                region = read(entry, "RegionDef")
                if isinstance(region, UObject):
                    paths.add(str(region._path_name()))
        for observations in self.observers.recorder.missions.values():
            for event in list(observations)[-2:]:
                for mission in event["data"].get("mission_state_at_event", []):
                    region = mission.get("region")
                    if isinstance(region, dict) and "path" in region and len(paths) < 16:
                        paths.add(region["path"])
        bounds, definitions = [], []
        scanned = 0
        errors = []
        try:
            for definition in islice(unrealsdk.find_all("GameBalanceDefinition"), 96):
                scanned += 1
                definitions.append(identity(definition))
                entries = read(definition, "BalanceByRegion")
                if isinstance(entries, dict):
                    continue
                for entry in islice(entries, 128):
                    region = read(entry, "Region")
                    if isinstance(region, UObject) and str(region._path_name()) in paths and len(bounds) < 32:
                        bounds.append({"balance": identity(definition), "region": identity(region),
                                       "values": Snapshot().fields(entry, pattern=None)})
        except Exception as exc:
            errors.append(safe_text(exc))
        return {"saved_region_records": Snapshot().value(saved), "relevant_region_paths": sorted(paths),
                "matching_region_bounds": bounds, "loaded_balance_definitions": definitions,
                "scanned": scanned, "scan_limit": 96, "errors": errors,
                "truncated": scanned == 96 or len(bounds) == 32,
                "note": "Saved region records include their own PlaythroughIdx; do not assume a PT0 record is UVHM's stage."}

    def tuning(self):
        path = "GD_Playthrough3Tuning.Balance.BalanceMod_PT3"
        tables = {}
        try:
            obj = unrealsdk.find_object("BalanceModifierDefinition", path)
            result = {"object": identity(obj)}
            for name in property_names(obj):
                if name.startswith("BalanceModifiers"):
                    snap = Snapshot()
                    tables[name] = {"entries": snap.value(read(obj, name)),
                                    "errors": snap.errors, "truncations": snap.truncations}
        except Exception as exc:
            result = unavailable(f"native UVHM tuning not loaded: {type(exc).__name__}: {exc}")
        formulas = {}
        for suffix in ("", "_MinLevel61", "_Overpowered"):
            name = "GD_Playthrough3Tuning.Formulas.Init_EnemyHealthRegenFormula" + suffix
            try:
                regen = unrealsdk.find_object("AttributeInitializationDefinition", name)
                # ValueFormula alone omits the initializer's other calculation paths.
                formulas[name] = Snapshot().object(regen, pattern=INITIALIZER_FIELDS)
            except Exception as exc:
                formulas[name] = unavailable(f"UVHM regeneration formula not loaded: {type(exc).__name__}: {exc}")
        return {"pt3_balance": result,
                "balance_tables": tables,
                "active_table": unavailable("all reflected cap/OP variants recorded; actual native selection not inferred"),
                "regeneration_formula": formulas["GD_Playthrough3Tuning.Formulas.Init_EnemyHealthRegenFormula"],
                "regeneration_formulas": formulas,
                "original_current_differences": self.observers.snapshot()["original_current_differences"],
                "provenance": "runtime values; this build changes only the first UVHM tuning threshold; other mods may also edit these objects",
                "later_thresholds": "BalanceModifiers array is sampled with explicit truncation"}

    def enemies(self, pc):
        location = None
        if pc is not None:
            pawn = read(pc, "Pawn")
            loc = read(pawn, "Location") if isinstance(pawn, UObject) else None
            if loc is not None and not isinstance(loc, dict):
                location = tuple(float(getattr(loc, axis)) for axis in ("X", "Y", "Z"))
        return {"pawns": sample_class("WillowAIPawn", ACTOR, 12, 256, location, live_only=True),
                "vehicles": sample_class("WillowVehicle", ACTOR, 6, 96, location, live_only=True),
                "effective_health_regen": unavailable("only reflected fields sampled; no unverified attribute evaluator called")}

    def economy(self, history):
        vendors = sample_class("WillowVendingMachine", EQUIPMENT, 6, 64, live_only=True)
        stock = []
        try:
            for vendor in islice(unrealsdk.find_all("WillowVendingMachine", exact=False), 12):
                if ".TheWorld:" not in str(vendor._path_name()):
                    continue
                inventory = read(vendor, "ShopInventory")
                if not isinstance(inventory, dict):
                    stock.append({"vendor": identity(vendor), "stock_count": len(inventory),
                                  "sample": [Snapshot().object(item, EQUIPMENT) for item in islice(inventory, 4)
                                             if isinstance(item, UObject)], "sample_limit": 4,
                                  "featured_item": Snapshot().value(read(vendor, "FeaturedItem"))})
        except Exception as exc:
            stock.append(unavailable(f"vendor stock: {type(exc).__name__}: {exc}"))
        return {"vendors": vendors, "stock": stock,
                "recent_generation_events": history["recent_equipment"],
                "recent_pickup_xp_currency_ammo_events": history["recent_economy"],
                "drops": sample_class("WillowPickup", EQUIPMENT, 8, 128, live_only=True),
                "price_evaluation": unavailable("configured fields only; no purchase, sale or pricing function invoked")}
