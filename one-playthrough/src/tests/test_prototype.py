"""Offline contracts only. Fakes do not prove real game hooks or layouts."""

from __future__ import annotations

import importlib
import importlib.util
import json
import shutil
import sys
import tempfile
import types
import unittest
import zipfile
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

SRC = Path(__file__).resolve().parents[1]

# Import pure/runtime modules without running SDK registration in package __init__.
namespace = types.ModuleType("one_playthrough")
namespace.__path__ = [str(SRC / "one_playthrough")]
sys.modules["one_playthrough"] = namespace


class FakeProperty:
    def __init__(self, name):
        self.Name = name
        self.Class = types.SimpleNamespace(Name="Property")
        self.PropertyFlags = 0


class FakeClass:
    def __init__(self, name, fields=(), functions=None):
        self.Name = name
        self.names = tuple(fields)
        self.functions = functions or {}

    def _find_prop(self, name):
        if name not in self.names:
            raise ValueError(name)
        return FakeProperty(name)

    def _properties(self):
        return iter(FakeProperty(n) for n in self.names)

    def _fields(self):
        return iter(self.functions.values())

    def _find(self, name):
        if name not in self.functions:
            raise ValueError(name)
        return self.functions[name]

    def _inherits(self, cls):
        return self.Name == cls.Name

    def _path_name(self):
        return "WillowGame." + self.Name


class FakeObject:
    def __init__(self, path="Map.Object", cls="Object", **fields):
        object.__setattr__(self, "Class", FakeClass(cls, fields))
        object.__setattr__(self, "_path", path)
        for key, value in fields.items():
            object.__setattr__(self, key, value)

    def _path_name(self):
        return self._path

    def __setattr__(self, name, value):
        raise AssertionError(f"unexpected engine write: {name}")


class FakeStruct:
    def __init__(self, **fields):
        object.__setattr__(self, "_type", FakeClass("Struct", fields))
        for key, value in fields.items():
            object.__setattr__(self, key, value)

    def __setattr__(self, name, value):
        raise AssertionError(f"unexpected argument write: {name}")


class FakeArray(list):
    pass


class FakeFunction(FakeObject):
    def __init__(self, path, name, params, flags=None):
        super().__init__(path)
        object.__setattr__(self, "Name", name)
        object.__setattr__(self, "params", params)
        owner = path.rpartition(":" if ":" in path else ".")[0]
        object.__setattr__(self, "Outer", FakeObject(owner))
        object.__setattr__(self, "FunctionFlags", 0)
        object.__setattr__(self, "flags", flags or {})

    def _properties(self):
        props = []
        for name in self.params:
            prop = FakeProperty(name)
            prop.PropertyFlags = self.flags.get(name, 1408 if name == "ReturnValue" else 128)
            props.append(prop)
        return iter(props)


sdk = types.ModuleType("unrealsdk")
unreal = types.ModuleType("unrealsdk.unreal")
unreal.UObject, unreal.WrappedStruct = FakeObject, FakeStruct
unreal.WrappedArray, unreal.UFunction = FakeArray, FakeFunction
hooks = types.ModuleType("unrealsdk.hooks")
hooks.Type = types.SimpleNamespace(PRE="PRE", POST_UNCONDITIONAL="POST_UNCONDITIONAL")
hooks.prevent_hooking_direct_calls = nullcontext
registry = {}
classes = {}
objects = {}


def lookup_class(name):
    if name not in classes:
        raise ValueError("class not loaded: " + name)
    return classes[name]


def lookup_object(cls, path):
    if path not in objects:
        raise ValueError("object not loaded: " + path)
    return objects[path]


def add_hook(target, phase, ident, callback):
    registry[(target, phase, ident)] = callback
    return True


def remove_hook(target, phase, ident):
    return registry.pop((target, phase, ident), None) is not None


hooks.add_hook = add_hook
hooks.remove_hook = remove_hook
hooks.has_hook = lambda target, phase, ident: (target, phase, ident) in registry
sdk.find_class = lookup_class
sdk.find_object = lookup_object
sdk.find_all = lambda cls, exact=True: (iter(classes.values()) if cls == "Class" else
    iter(o for o in objects.values() if o.Class.Name == cls))
sdk.__version__ = "test-fake"
base = types.ModuleType("mods_base")
base.SETTINGS_DIR = Path(tempfile.gettempdir()) / "not-used-sdk-settings"
base.get_pc = lambda **kwargs: None
base.__version__ = "test-fake"
sys.modules.update({"unrealsdk": sdk, "unrealsdk.unreal": unreal,
                    "unrealsdk.hooks": hooks, "mods_base": base})

core = importlib.import_module("one_playthrough.core")
reflection = importlib.import_module("one_playthrough.reflection")
observation = importlib.import_module("one_playthrough.observers")
diagnostics = importlib.import_module("one_playthrough.diagnostics")
activity = importlib.import_module("one_playthrough.activity")
probes = importlib.import_module("one_playthrough.probes")
region_probe = importlib.import_module("one_playthrough.region_probe")
tuning_module = importlib.import_module("one_playthrough.tuning")
spec = importlib.util.spec_from_file_location("prototype_build", SRC / "build.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class CoreTests(unittest.TestCase):
    def test_atomic_replace_retries_transient_permission_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            real_replace = core.os.replace
            calls = []
            def locked_then_available(source, destination):
                calls.append(destination)
                if len(calls) <= 2:
                    raise PermissionError(13, "destination locked")
                return real_replace(source, destination)
            with patch.object(core.os, "replace", side_effect=locked_then_available), patch.object(core.time, "sleep") as sleep:
                core.atomic_json(path, {"complete": True})
            self.assertEqual(len(calls), 3)
            self.assertEqual(sleep.call_args_list, [unittest.mock.call(0.05), unittest.mock.call(0.10)])
            self.assertTrue(json.loads(path.read_text())["complete"])

    def test_permanent_permission_error_preserves_checkpoint_after_bounded_retries(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            core.atomic_json(path, {"complete": False})
            with patch.object(core.os, "replace", side_effect=PermissionError(13, "locked")) as replace, patch.object(core.time, "sleep") as sleep:
                with self.assertRaises(PermissionError):
                    core.atomic_json(path, {"complete": True})
            self.assertEqual(replace.call_count, 4)
            self.assertEqual(sleep.call_count, 3)
            self.assertFalse(json.loads(path.read_text())["complete"])
    def test_compact_report_interns_events_without_losing_payloads(self):
        event = {"sequence": 17, "utc": "test", "kind": "engine:query", "data": {"stage": 50, "body": "x" * 3000}}
        report = {"history": {"events": [event], "recent_ui": [event]},
                  "sections": {"mission": {"observations": [event]}}}
        result = core.compact_report(report)
        self.assertEqual(result["event_table"]["17"], event)
        self.assertEqual(result["sections"]["mission"]["observations"], [{"event_ref": 17}])
        self.assertLess(len(json.dumps(result)), len(json.dumps(report)) * 0.45)

    def test_scaling_queries_survive_pickup_churn(self):
        recorder = core.Recorder()
        recorder.record("engine:GetRegionGameStage", {"stage": 50})
        for _ in range(250):
            recorder.record("economy:HandlePickup", {})
        self.assertEqual(recorder.snapshot()["scaling_queries"][0]["data"]["stage"], 50)
        recorder.clear_context()
        self.assertFalse(recorder.snapshot()["scaling_queries"])
    def test_recording_bounded_and_no_live_objects(self):
        recorder = core.Recorder()
        for i in range(250):
            recorder.record("event", {"level": i}, [f"Mission.{i}"])
        self.assertEqual(len(recorder.events), core.MAX_EVENTS)
        self.assertEqual(len(recorder.missions), 32)
        self.assertEqual(recorder.dropped_events, 58)
        self.assertEqual(recorder.dropped_missions, 218)
        with self.assertRaises(TypeError):
            recorder.record("bad", {"object": FakeObject()})
        with self.assertRaises(ValueError):
            recorder.record("bad", {"value": float("nan")})

    def test_json_copy_detaches_event_arguments(self):
        recorder = core.Recorder()
        payload = {"nested": {"stage": 3}}
        recorder.record("accept", payload)
        payload["nested"]["stage"] = 50
        self.assertEqual(recorder.events[0]["data"]["nested"]["stage"], 3)

    def test_context_reset_retains_no_character_events(self):
        recorder = core.Recorder()
        recorder.record("ui:offer", {"stage": 3}, ["Mission.A"])
        recorder.clear_context()
        self.assertFalse(recorder.snapshot()["events"])
        self.assertFalse(recorder.snapshot()["recent_ui"])
        self.assertFalse(recorder.snapshot()["mission_observations"])

    def test_mission_acceptance_survives_repeated_level_queries(self):
        recorder = core.Recorder()
        recorder.record("engine:AcceptMission", {"stage": 3}, ["Mission.A"])
        for i in range(250):
            recorder.record("engine:GetLevelForMission", {"stage": 3}, ["Mission.A"])
        report = recorder.snapshot()
        self.assertEqual(report["mission_lifecycle"]["Mission.A"][0]["kind"], "engine:AcceptMission")
        self.assertEqual(len(report["mission_observations"]["Mission.A"]), 8)
        recorder.clear_context()
        self.assertFalse(recorder.snapshot()["mission_lifecycle"])

    def test_activity_histories_survive_query_churn_and_stay_bounded(self):
        recorder = core.Recorder()
        for i in range(100):
            recorder.record("economy:AddCurrency", {"amount": i})
            recorder.record("combat:TakeDamage", {"damage": i})
        for _ in range(250):
            recorder.record("engine:GetGameStage", {"stage": 50})
        report = recorder.snapshot()
        self.assertEqual(len(report["recent_economy"]), 32)
        self.assertEqual(len(report["recent_combat"]), 24)
        recorder.clear_context()
        self.assertFalse(recorder.snapshot()["recent_economy"])
        self.assertFalse(recorder.snapshot()["recent_combat"])

    def test_atomic_failure_keeps_previous_report_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            core.atomic_json(path, {"partial": True})
            with patch.object(core.os, "replace", side_effect=OSError("disk failure")):
                with self.assertRaises(OSError):
                    core.atomic_json(path, {"partial": False})
            self.assertTrue(json.loads(path.read_text())["partial"])
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_nonfinite_export_never_replaces_valid_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            core.atomic_json(path, {"ok": True})
            with self.assertRaises(ValueError):
                core.atomic_json(path, {"invalid": float("inf")})
            self.assertEqual(json.loads(path.read_text()), {"ok": True})

    def test_unique_paths_and_privacy(self):
        self.assertNotEqual(core.new_report_path("/tmp", "0.1.0"), core.new_report_path("/tmp", "0.1.0"))
        text = core.safe_text("bad /Users/person/private/file 76561198012345678 C:\\Users\\person\\file")
        self.assertNotIn("person", text)
        self.assertNotIn("76561198012345678", text)


class SnapshotTests(unittest.TestCase):
    def test_arrays_structs_and_objects_have_distinct_shapes(self):
        snap = reflection.Snapshot()
        result = snap.value(FakeArray([FakeStruct(GameStage=3, Mission=FakeObject("Mission.A"))]))
        self.assertEqual(result["items"][0]["GameStage"], 3)
        self.assertEqual(result["items"][0]["Mission"]["path"], "Mission.A")

    def test_bounds_and_nonfinite(self):
        snap = reflection.Snapshot()
        result = snap.value(FakeArray(range(1000)))
        self.assertEqual(len(result["items"]), 12)
        self.assertTrue(result["truncated"])
        self.assertIn("array length", snap.truncations)
        self.assertFalse(snap.value(float("nan"))["available"])

    def test_formula_struct_keeps_base_values_and_effect_attributes(self):
        result = reflection.Snapshot().value(FakeStruct(
            BaseValueConstant=1.0, BaseValueScaleConstant=2.0,
            AttributeToModify=FakeObject("Attributes.HealthRegen")))
        self.assertEqual(result["BaseValueConstant"], 1.0)
        self.assertEqual(result["BaseValueScaleConstant"], 2.0)
        self.assertEqual(result["AttributeToModify"]["path"], "Attributes.HealthRegen")

    def test_private_fields_excluded(self):
        obj = FakeObject(GameStage=3, AccountId="secret", SteamId="secret", SaveGameId=10)
        result = reflection.Snapshot().fields(obj, pattern=None)
        self.assertEqual(result, {"GameStage": 3})

    def test_stage_priority_avoids_noise_hiding_authoritative_values(self):
        noise = {f"DamageNoise{i}": i for i in range(60)}
        obj = FakeObject(**noise, GameStage=50, ExpLevel=50, PawnBalanceDefinition=None,
                         VfTable_IIDamageable=FakeStruct(Dummy=123456))
        result = reflection.Snapshot().fields(obj)
        self.assertEqual(result["GameStage"], 50)
        self.assertEqual(result["ExpLevel"], 50)
        self.assertIn("PawnBalanceDefinition", result)
        self.assertNotIn("VfTable_IIDamageable", result)

    def test_nested_regeneration_effect_formula_not_truncated_at_old_depth(self):
        obj = FakeObject(BalanceModifiers=FakeArray([FakeStruct(
            MinEffectiveLevel=50, AttributeEffectsForSpawnedEnemies=FakeArray([FakeStruct(
                BaseModifierValue=FakeStruct(BaseValueConstant=1.0))]))]))
        result = reflection.Snapshot().fields(obj)
        modifier = result["BalanceModifiers"]["items"][0]
        self.assertEqual(modifier["AttributeEffectsForSpawnedEnemies"]["items"][0]
                         ["BaseModifierValue"]["BaseValueConstant"], 1.0)

    def test_missing_values_not_zero(self):
        result = reflection.read(FakeObject(), "ExpLevel")
        self.assertFalse(result["available"])
        self.assertIn("ExpLevel", result["reason"])


class EngineContractTests(unittest.TestCase):
    def setUp(self):
        registry.clear()
        classes.clear()
        objects.clear()

    def test_pickup_polling_and_physics_hooks_are_not_registered(self):
        names = {name for candidates in observation.TARGETS.values() for name in candidates}
        self.assertFalse(names & {"HandlePickupQuery", "GetPickupableInventory", "GetPickupableInventoryDefinition",
                                 "PickupQuery", "TouchPickupTrace", "SpawnPickupParticles", "SawPickupable"})

    def test_normal_play_does_not_trace_scaling_or_pickup_initialization(self):
        names = {name for candidates in observation.TARGETS.values() for name in candidates}
        self.assertFalse(names & {"GetCurrentPlaythrough", "GetRegionGameStage", "GetDefaultRegionGameStage",
                                 "GetGameStage", "SetGameStage", "SetExpLevel", "CreatePopulationActor",
                                 "RestorePopulatedAIPawn", "ClientInitializeInventoryFromDefinition",
                                 "HandlePickup", "PickedUpBy", "GiveTo"})
        self.assertTrue({"AcceptMission", "ServerGrantMissionRewards", "SetRewardCard", "ReceiveItemReward"} <= names)

    def test_f10_rejects_retired_experiments_and_skips_discovery_catalogue(self):
        exporter = diagnostics.Diagnostics(observation.Observers(), lambda *args: None)
        with tempfile.TemporaryDirectory() as directory:
            exporter.directory = Path(directory)
            for keyword in ("probe", "threshold_probe", "region_probe"):
                with self.assertRaises(TypeError):
                    exporter.export(**{keyword: True})
            self.assertFalse(list(Path(directory).iterdir()))
            report = json.loads(exporter.export().read_text())
        self.assertNotIn("runtime_class_catalogue", report["sections"])
        self.assertEqual(report["capture_mode"], "observational")

    def test_throttled_calls_do_not_reflect_or_read_player(self):
        observers = observation.Observers()
        observers.enabled = True
        target = "WillowGame.WillowPawn:GetGameStage"
        observers.status[target] = {"hits": 0, "sampled": 0}
        callback = observers._callback(target, "GetGameStage", "POST_UNCONDITIONAL")
        with patch.object(observation.time, "monotonic", return_value=100), patch.object(observation, "get_pc", return_value=None) as get_pc:
            callback(FakeObject(), FakeStruct(), 50, None)
            with patch.object(observation, "mission_paths", side_effect=AssertionError("hot reflection")):
                for _ in range(1000):
                    callback(FakeObject(), FakeStruct(), 50, None)
        self.assertEqual(get_pc.call_count, 1)
        self.assertEqual(observers.status[target]["throttled"], 1000)
        self.assertNotIn("last_observer_error", observers.status[target])

    def test_loading_movie_close_preserves_startup_stage_events(self):
        observers = observation.Observers()
        observers.enabled = True
        target = "WillowGame.WillowPlayerController:WillowClientShowLoadingMovie"
        observers.status[target] = {"hits": 0, "sampled": 0}
        observers.recorder.record("engine:GetRegionGameStage", {"stage": 50})
        callback = observers._callback(target, "WillowClientShowLoadingMovie", "POST_UNCONDITIONAL")
        callback(FakeObject(), FakeStruct(bShowMovie=False), None, None)
        self.assertEqual(len(observers.recorder.scaling), 1)
        callback(FakeObject(), FakeStruct(bShowMovie=True), None, None)
        self.assertFalse(observers.recorder.scaling)

    def test_default_f10_never_runs_explicit_scaling_probe(self):
        exporter = diagnostics.Diagnostics(observation.Observers(), lambda *args: None)
        with tempfile.TemporaryDirectory() as directory:
            exporter.directory = Path(directory)
            with patch.object(probes, "scaling_probe", side_effect=AssertionError("unexpected probe")) as probe, patch.object(probes, "threshold_experiment", side_effect=AssertionError("unexpected data edit")) as threshold, patch.object(region_probe, "region_override_experiment", side_effect=AssertionError("unexpected override")) as region:
                self.assertIsNotNone(exporter.export())
                probe.assert_not_called()
                threshold.assert_not_called()
                region.assert_not_called()

    def _region_fixture(self, global_override=True, fail_after_write=False):
        calls = []
        override = {}
        class Region(FakeObject):
            def SetGameStageOverride(self, NewGameStageOverride):
                calls.append((self._path_name(), NewGameStageOverride))
                override["all" if global_override else self._path_name()] = NewGameStageOverride
                if fail_after_write:
                    raise RuntimeError("native setter failed after write")
        class SetterFunction(FakeFunction):
            def _properties(self):
                prop = FakeProperty("NewGameStageOverride")
                prop.Class = types.SimpleNamespace(Name="IntProperty")
                prop.PropertyFlags = 128
                return iter([prop])
        setter = SetterFunction("WillowGame.WillowRegionDefinition:SetGameStageOverride", "SetGameStageOverride", [])
        object.__setattr__(setter, "FunctionFlags", 140288)
        paths = ["GD_GameStages.Zone1." + n for n in ("StartOfGame", "Waterfront_A", "Ice_A")]
        for path in paths:
            obj = Region(path, "WillowRegionDefinition")
            obj.Class.functions["SetGameStageOverride"] = setter
            objects[path] = obj
        pc = FakeObject(OverpowerChoiceValue=0, PlayerReplicationInfo=FakeObject(ExpLevel=10))
        baseline = {"regions": [{"region": {"path": paths[0]}}]}
        def fake_query(obj, name, arguments, out_names=()):
            if name == "GetCurrentPlaythrough":
                return {"return_value": 2}
            if name == "GetDefaultRegionGameStage":
                return {"return_value": True, "outputs_valid": True, "out_parameters": {"MinGameStage": 1, "MaxGameStage": 2}}
            if name == "GetRegionGameStage":
                value = override.get("all", override.get(obj._path_name(), 50))
                return {"return_value": True, "outputs_valid": True, "out_parameters": {"GameStage": value, "AwesomeLevel": 1}}
            raise AssertionError(name)
        return pc, baseline, fake_query, calls, paths, setter

    def test_region_override_calls_native_setter_once_and_measures_global_scope(self):
        pc, baseline, getter, calls, paths, _ = self._region_fixture()
        with patch.object(region_probe, "scaling_probe", return_value=baseline), patch.object(region_probe, "query", side_effect=getter):
            report = region_probe.region_override_experiment(pc)
        self.assertEqual(calls, [(paths[0], 10)])
        self.assertTrue(report["setter_attempted"])
        self.assertTrue(report["restart_required"])
        self.assertTrue(report["target_returned_requested_stage"])
        self.assertEqual(set(report["regions_with_changed_current_outputs"]), set(paths))
        self.assertFalse(report["original_override"]["available"])
        self.assertNotIn("restored", report)

    def test_region_override_does_not_assume_global_effect(self):
        pc, baseline, getter, calls, paths, _ = self._region_fixture(global_override=False)
        with patch.object(region_probe, "scaling_probe", return_value=baseline), patch.object(region_probe, "query", side_effect=getter):
            report = region_probe.region_override_experiment(pc)
        self.assertEqual(report["regions_with_changed_current_outputs"], [paths[0]])
        self.assertEqual(len(calls), 1)

    def test_region_setter_failure_after_write_still_requires_restart(self):
        pc, baseline, getter, calls, _, _ = self._region_fixture(fail_after_write=True)
        with patch.object(region_probe, "scaling_probe", return_value=baseline), patch.object(region_probe, "query", side_effect=getter):
            report = region_probe.region_override_experiment(pc)
        self.assertTrue(report["restart_required"])
        self.assertIn("failed after write", report["error"])
        self.assertEqual(len(calls), 1)

    def test_region_setter_changed_signature_is_not_executed(self):
        pc, baseline, getter, calls, _, setter = self._region_fixture()
        object.__setattr__(setter, "FunctionFlags", 0)
        with patch.object(region_probe, "scaling_probe", return_value=baseline), patch.object(region_probe, "query", side_effect=getter):
            report = region_probe.region_override_experiment(pc)
        self.assertFalse(report["setter_attempted"])
        self.assertFalse(report["restart_required"])
        self.assertEqual(calls, [])

    def test_region_override_rejects_nonzero_op_and_level_50(self):
        pc, baseline, getter, calls, _, _ = self._region_fixture()
        object.__setattr__(pc, "OverpowerChoiceValue", 1)
        with patch.object(region_probe, "scaling_probe", return_value=baseline), patch.object(region_probe, "query", side_effect=getter):
            report = region_probe.region_override_experiment(pc)
            self.assertFalse(report["setter_attempted"])
            object.__setattr__(pc, "OverpowerChoiceValue", 0)
            object.__setattr__(pc.PlayerReplicationInfo, "ExpLevel", 50)
            report = region_probe.region_override_experiment(pc)
            self.assertFalse(report["setter_attempted"])
        self.assertEqual(calls, [])


    def test_final_export_failure_recovers_complete_data_and_records_errno(self):
        exporter = diagnostics.Diagnostics(observation.Observers(), lambda *args: None)
        calls = []
        def checkpoint_locked_final(path, report):
            calls.append(path)
            if len(calls) == 2:
                raise PermissionError(13, "checkpoint locked")
            core.atomic_json(path, report)
        with tempfile.TemporaryDirectory() as directory:
            exporter.directory = Path(directory)
            with patch.object(diagnostics, "atomic_json", side_effect=checkpoint_locked_final):
                recovered = exporter.export()
            report = json.loads(recovered.read_text())
            checkpoint = json.loads(calls[0].read_text())
        self.assertTrue(report["export_complete"])
        self.assertTrue(report["partial"])
        self.assertEqual(report["errors"][0]["phase"], "final_commit")
        self.assertEqual(report["errors"][0]["errno"], 13)
        self.assertFalse(checkpoint["export_complete"])
        self.assertIn("player_session", report["sections"])
        self.assertTrue(recovered.name.endswith("-recovered.json"))

    def _threshold_fixture(self, fail_restore=False):
        writes = []
        class Threshold(FakeStruct):
            def __setattr__(self, name, value):
                if name != "MinEffectiveLevel":
                    raise AssertionError(name)
                if fail_restore and value == 50:
                    raise ValueError("restore refused")
                writes.append(value)
                object.__setattr__(self, name, value)
        row = Threshold(MinEffectiveLevel=50, EnemyHealthMultiplier=4.0)
        later = [FakeStruct(MinEffectiveLevel=61), FakeStruct(MinEffectiveLevel=73)]
        objects["GD_Playthrough3Tuning.Balance.BalanceMod_PT3"] = FakeObject(BalanceModifiers=FakeArray([row] + later))
        return row, later, writes

    def test_threshold_experiment_restores_first_row_and_preserves_later_rows(self):
        row, later, writes = self._threshold_fixture()
        def result(_pc):
            return {"regions": [{"observed_threshold": row.MinEffectiveLevel}]}
        with patch.object(probes, "scaling_probe", side_effect=result):
            report = probes.threshold_experiment(FakeObject())
        self.assertEqual(writes, [1, 50])
        self.assertTrue(report["restored"])
        self.assertTrue(report["tuning_snapshot_matches_after_restore"])
        self.assertTrue(report["later_thresholds_unchanged"])
        self.assertEqual([r.MinEffectiveLevel for r in later], [61, 73])
        self.assertEqual(row.EnemyHealthMultiplier, 4.0)

    def test_threshold_experiment_restores_even_if_query_raises(self):
        row, _, writes = self._threshold_fixture()
        with patch.object(probes, "scaling_probe", side_effect=[{"regions": [1]}, RuntimeError("query failed")]):
            report = probes.threshold_experiment(FakeObject())
        self.assertEqual(writes, [1, 50])
        self.assertEqual(row.MinEffectiveLevel, 50)
        self.assertTrue(report["restored"])
        self.assertIn("query failed", report["error"])

    def test_threshold_experiment_flags_failed_restore(self):
        row, _, _ = self._threshold_fixture(fail_restore=True)
        with patch.object(probes, "scaling_probe", return_value={"regions": [1]}):
            report = probes.threshold_experiment(FakeObject())
        self.assertFalse(report["restored"])
        self.assertTrue(report["restart_required"])
        self.assertEqual(row.MinEffectiveLevel, 1)

    def test_threshold_layout_mismatch_never_edits_data(self):
        row, _, writes = self._threshold_fixture()
        object.__setattr__(row, "MinEffectiveLevel", 40)
        with patch.object(probes, "scaling_probe", return_value={"regions": [1]}):
            report = probes.threshold_experiment(FakeObject())
        self.assertFalse(report["available"])
        self.assertFalse(report["restoration_attempted"])
        self.assertEqual(writes, [])
        self.assertEqual(row.MinEffectiveLevel, 40)



    def test_native_output_tuple_is_named_and_validated(self):
        calls = []
        class Region(FakeObject):
            def GetRegionGameStage(self, **kwargs):
                calls.append(kwargs)
                return True, 50, 2
        region = Region()
        region.Class.functions["GetRegionGameStage"] = FakeFunction(
            "WillowGame.WillowRegionDefinition:GetRegionGameStage", "GetRegionGameStage",
            ["GameStage", "AwesomeLevel", "bDefaultGameStage", "ReturnValue"],
            {"GameStage": 384, "AwesomeLevel": 384})
        result = probes.query(region, "GetRegionGameStage", {"GameStage": 0, "AwesomeLevel": 0, "bDefaultGameStage": False},
                              ("GameStage", "AwesomeLevel"))
        self.assertEqual(result["out_parameters"], {"GameStage": 50, "AwesomeLevel": 2})
        self.assertTrue(result["outputs_valid"])
        self.assertEqual(len(calls), 1)
        rejected = probes.query(region, "GetRegionGameStage", {"WrongArg": 0}, ())
        self.assertFalse(rejected["available"])
        self.assertEqual(len(calls), 1)

    def test_hook_reflection_registration_pass_through_and_removal(self):
        function = FakeFunction("WillowGame.WillowPlayerController:AcceptMission", "AcceptMission", ["Mission"])
        classes["WillowPlayerController"] = FakeClass("WillowPlayerController", functions={"AcceptMission": function})
        classes["MissionDefinition"] = FakeClass("MissionDefinition")
        observers = observation.Observers()
        observers.enable()
        target = "WillowGame.WillowPlayerController:AcceptMission"
        self.assertTrue(observers.snapshot()["hooks"][target]["registered_now"]["PRE"])
        mission = FakeObject("Mission.A", "MissionDefinition", GameStage=50)
        args = FakeStruct(Mission=mission)
        for key, callback in list(registry.items()):
            self.assertIsNone(callback(FakeObject(), args, 42, None))
        self.assertEqual(mission.GameStage, 50)
        self.assertIs(args.Mission, mission)
        self.assertEqual(len(observers.recorder.events), 3)
        self.assertIn("Mission.A", observers.recorder.missions)
        observers.disable()
        self.assertFalse(registry)

    def test_real_colon_function_paths_and_legacy_dotted_paths_register_identically(self):
        for path in ("WillowGame.WillowPlayerController:AcceptMission",
                     "WillowGame.WillowPlayerController.AcceptMission"):
            with self.subTest(path=path):
                registry.clear()
                function = FakeFunction(path, "AcceptMission", ["Mission"])
                observers = observation.Observers()
                observers.enabled = True
                cls = FakeClass("WillowPlayerController", functions={"AcceptMission": function})
                observers._install_one(cls, "AcceptMission")
                # The actual SDK accepts a malformed string too. Simulate native
                # dispatch to the exact known path, not an arbitrary stored callback.
                canonical = "WillowGame.WillowPlayerController:AcceptMission"
                callback = registry[(canonical, "PRE", "one_playthrough:PRE")]
                callback(FakeObject(), FakeStruct(), None, None)
                self.assertEqual(observers.status[canonical]["hits"], 1)
                self.assertNotIn("WillowGame:WillowPlayerController:AcceptMission", observers.status)

    def test_inherited_function_uses_its_actual_owner(self):
        function = FakeFunction("Engine.WillowInventory:GetGameStage", "GetGameStage", ["ReturnValue"])
        cls = FakeClass("SomeDerivedInventory", functions={"GetGameStage": function})
        observers = observation.Observers()
        observers._install_one(cls, "GetGameStage")
        self.assertIn("Engine.WillowInventory:GetGameStage", observers.status)

    def test_real_mstatus_argument_name_and_return_struct_keep_mission_identity(self):
        classes["MissionDefinition"] = FakeClass("MissionDefinition")
        mission = FakeObject("Mission.A", "MissionDefinition")
        self.assertEqual(observation.mission_paths(FakeStruct(MStatus=FakeStruct(Mission=mission))), {"Mission.A"})
        self.assertEqual(observation.mission_paths(FakeStruct(MissionDef=mission)), {"Mission.A"})

    def test_live_actor_samples_exclude_templates(self):
        classes["WillowAIPawn"] = FakeClass("WillowAIPawn")
        objects["template"] = FakeObject("GD_PrimalBeast.Character.Pawn_PrimalBeast", "WillowAIPawn", ExpLevel=0)
        objects["actual"] = FakeObject("Glacial_Dynamic.TheWorld:PersistentLevel.WillowAIPawn_1", "WillowAIPawn", ExpLevel=50)
        result = diagnostics.sample_class("WillowAIPawn", diagnostics.ACTOR, live_only=True)
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["fields"]["ExpLevel"], 50)
        self.assertEqual(result["excluded_templates_or_non_world_objects"], 1)

    def test_armed_capture_ignores_hud_refresh_and_supports_completion_screen(self):
        observers = observation.Observers()
        observers.enabled = observers.armed = True
        classes["MissionDefinition"] = FakeClass("MissionDefinition")
        mission = FakeObject("Mission.A", "MissionDefinition", GameStage=50)
        calls = []
        observers.capture_callback = calls.append
        hud_target = "WillowGame.HUDWidget_Missions:SetDisplayedMission"
        reward_target = "WillowGame.MissionCompleteGFxMovie:SetMissionData"
        for target in (hud_target, reward_target):
            observers.status[target] = {"hits": 0, "sampled": 0}
        observers._callback(hud_target, "SetDisplayedMission", "POST_UNCONDITIONAL")(
            FakeObject(), FakeStruct(MissionDef=mission), None, None)
        self.assertTrue(observers.armed)
        observers._callback(reward_target, "SetMissionData", "POST_UNCONDITIONAL")(
            FakeObject(), FakeStruct(MissionDef=mission), None, None)
        self.assertEqual(calls, ["armed_mission_screen"])

    def test_no_player_export_is_valid_and_does_not_write_engine_state(self):
        observers = observation.Observers()
        notifications = []
        exporter = diagnostics.Diagnostics(observers, lambda *args: notifications.append(args))
        with tempfile.TemporaryDirectory() as directory:
            exporter.directory = Path(directory)
            path = exporter.export()
            report = json.loads(path.read_text())
        self.assertTrue(report["export_complete"])
        self.assertTrue(report["partial"])
        self.assertFalse(report["implementation"]["gameplay_writes"])
        self.assertFalse(report["sections"]["player_session"]["available"])
        self.assertTrue(notifications)

    def test_interrupted_collection_leaves_valid_checkpoint(self):
        observers = observation.Observers()
        exporter = diagnostics.Diagnostics(observers, lambda *args: None)
        with tempfile.TemporaryDirectory() as directory:
            exporter.directory = Path(directory)
            with patch.object(exporter, "missions", side_effect=KeyboardInterrupt()):
                with self.assertRaises(KeyboardInterrupt):
                    exporter.export()
            files = list(Path(directory).glob("*.json"))
            self.assertEqual(len(files), 1)
            report = json.loads(files[0].read_text())
        self.assertFalse(report["export_complete"])
        self.assertIn("implementation", report)
        self.assertIn("history", report)
        self.assertIn("event_table", report)
        self.assertFalse(observers.collecting)

    def test_optional_failure_preserves_other_sections(self):
        observers = observation.Observers()
        exporter = diagnostics.Diagnostics(observers, lambda *args: None)
        with tempfile.TemporaryDirectory() as directory:
            exporter.directory = Path(directory)
            with patch.object(exporter, "missions", side_effect=ValueError("stale object")):
                path = exporter.export()
            report = json.loads(path.read_text())
        self.assertTrue(report["export_complete"])
        self.assertIn("mission_comparison", report["errors"][0])
        self.assertIn("equipment_economy", report["sections"])

    def test_full_capture_reads_level_playthrough_and_character_without_writes(self):
        class Player(FakeObject):
            def GetCurrentPlaythrough(self):
                return 2

        mission = FakeObject("Mission.A", "MissionDefinition", GameStage=50, bGameStageLocked=True)
        objects["Mission.A"] = mission
        pc = Player(PlayerReplicationInfo=FakeObject(ExpLevel=1), OverpowerChoiceValue=0,
                    SaveGameId=1234, WorldInfo=FakeObject("Glacial_P.TheWorld"),
                    MissionPlaythroughs=FakeArray([FakeStruct(), FakeStruct(),
                        FakeStruct(MissionList=FakeArray([FakeStruct(MissionDef=mission, GameStage=50, Status=1)]))]))
        pc.Class.functions["GetCurrentPlaythrough"] = FakeFunction(
            "WillowGame.WillowPlayerController.GetCurrentPlaythrough", "GetCurrentPlaythrough", [])
        exporter = diagnostics.Diagnostics(observation.Observers(), lambda *args: None)
        with tempfile.TemporaryDirectory() as directory:
            exporter.directory = Path(directory)
            with patch.object(diagnostics, "get_pc", return_value=pc):
                path = exporter.export()
            report = json.loads(path.read_text())
        session = report["sections"]["player_session"]
        self.assertEqual(session["actual_xp_level"], 1)
        self.assertEqual(session["playthrough_index"], 2)
        self.assertEqual(session["scope"], "UVHM confirmed")
        self.assertTrue(session["character_fingerprint"].startswith("sha256:"))
        self.assertEqual(pc.PlayerReplicationInfo.ExpLevel, 1)
        self.assertEqual(mission.GameStage, 50)

    def test_write_failure_is_reported_without_console(self):
        notifications = []
        exporter = diagnostics.Diagnostics(observation.Observers(), lambda *args: notifications.append(args))
        with patch.object(diagnostics, "atomic_json", side_effect=OSError("read only disk")):
            self.assertIsNone(exporter.export())
        self.assertTrue(notifications[0][2])
        self.assertIn("read only disk", exporter.last_result)
        self.assertFalse(exporter.observers.collecting)

    def test_package_entrypoint_registers_author_version_and_f10(self):
        class Option:
            def __init__(self, identifier, **kwargs):
                self.identifier = identifier
                self.__dict__.update(kwargs)

        def keybind(identifier, key, **kwargs):
            return lambda callback: types.SimpleNamespace(identifier=identifier, key=key, callback=callback)

        registrations = []
        def build_mod(**kwargs):
            registrations.append(kwargs)
            kwargs["on_enable"]()
            return types.SimpleNamespace(**kwargs)

        entry_spec = importlib.util.spec_from_file_location("one_playthrough", SRC / "one_playthrough" / "__init__.py")
        entry = importlib.util.module_from_spec(entry_spec)
        with tempfile.TemporaryDirectory() as directory:
            fields = {"ButtonOption": Option, "keybind": keybind, "build_mod": build_mod,
                      "Game": types.SimpleNamespace(BL2=1),
                      "CoopSupport": types.SimpleNamespace(Incompatible=1),
                      "SETTINGS_DIR": Path(directory)}
            with patch.dict(base.__dict__, fields), patch.dict(sys.modules, {"one_playthrough": entry}):
                entry_spec.loader.exec_module(entry)
                self.assertEqual(len(list(Path(directory).rglob("*.json"))), 0)
                entry.capture.callback()
                self.assertEqual(len(list(Path(directory).rglob("*.json"))), 1, entry.diagnostics.last_result)
                self.assertEqual({o.identifier for o in registrations[0]["options"]},
                                 {"capture_next_screen", "export_now", "export_status"})
                entry.on_disable()
        registration = registrations[0]
        self.assertEqual(registration["author"], "keogh")
        self.assertEqual(registration["version"], "0.1.7")
        self.assertEqual(registration["keybinds"][0].key, "F10")
        self.assertFalse(registration["commands"])

    def test_same_mission_stored_and_definition_stage_compared_without_rewriting(self):
        mission = FakeObject("Mission.A", "MissionDefinition", GameStage=50, bGameStageLocked=True)
        objects["Mission.A"] = mission
        entry = FakeStruct(MissionDef=mission, GameStage=3, Status=1)
        pc = FakeObject(MissionPlaythroughs=FakeArray([FakeStruct(), FakeStruct(), FakeStruct(MissionList=FakeArray([entry]))]))
        exporter = diagnostics.Diagnostics(observation.Observers(), lambda *args: None)
        with patch.object(diagnostics, "known_query", return_value=2):
            result = exporter.missions(pc, core.Recorder().snapshot())
        item = result["items"][0]
        self.assertEqual(item["definition_stage"], 50)
        self.assertEqual(item["player_record"]["stored_stage"], 3)
        self.assertEqual(mission.GameStage, 50)
        self.assertEqual(entry.GameStage, 3)

    def test_armed_ui_capture_preserves_payload_and_disarms(self):
        observers = observation.Observers()
        observers.enabled = observers.armed = True
        target = "WillowGame.WillowPlayerController:PopulateMissionDataFromStatus"
        observers.status[target] = {"hits": 0, "sampled": 0}
        calls = []
        observers.capture_callback = calls.append
        classes["MissionDefinition"] = FakeClass("MissionDefinition")
        mission = FakeObject("Mission.A", "MissionDefinition", GameStage=50)
        callback = observers._callback(target, "PopulateMissionDataFromStatus", "POST_UNCONDITIONAL")
        self.assertIsNone(callback(FakeObject(), FakeStruct(MStatus=FakeStruct(Mission=mission), MissionLevel=50), None, None))
        self.assertEqual(calls, ["armed_mission_screen"])
        self.assertFalse(observers.armed)
        self.assertEqual(observers.recorder.ui[0]["data"]["arguments"]["MissionLevel"], 50)

    def test_xp_currency_pre_post_capture_does_not_call_setters(self):
        pri = FakeObject(ExpLevel=1, ExpPoints=0)
        pc = FakeObject(PlayerReplicationInfo=pri, CurrencyTotals=FakeArray([5]), Pawn=None)
        observers = observation.Observers()
        observers.enabled = True
        target = "WillowGame.WillowPlayerController:AddExperience"
        observers.status[target] = {"hits": 0, "sampled": 0}
        with patch.object(observation, "get_pc", return_value=pc):
            observers._callback(target, "AddExperience", "PRE")(pc, FakeStruct(Amount=100), None, None)
            # Simulate the game's own XP update, outside either observer.
            object.__setattr__(pri, "ExpPoints", 100)
            object.__setattr__(pri, "ExpLevel", 2)
            observers._callback(target, "AddExperience", "POST_UNCONDITIONAL")(pc, FakeStruct(Amount=100), None, None)
        events = list(observers.recorder.economy)
        self.assertEqual([e["data"]["phase"] for e in events], ["PRE", "POST_UNCONDITIONAL"])
        values = [e["data"]["player_resources_at_event"]["replication_info"]["fields"] for e in events]
        self.assertEqual([v["ExpPoints"] for v in values], [0, 100])
        self.assertEqual([v["ExpLevel"] for v in values], [1, 2])

    def test_combat_payload_keeps_damage_and_participant_levels(self):
        observers = observation.Observers()
        observers.enabled = True
        target = "WillowGame.WillowPawn:TakeDamage"
        observers.status[target] = {"hits": 0, "sampled": 0}
        victim = FakeObject("Glacial.TheWorld:PersistentLevel.Bullymong", ExpLevel=50)
        instigator = FakeObject("Glacial.TheWorld:PersistentLevel.Player", ExpLevel=1)
        args = FakeStruct(Damage=10, InstigatedBy=instigator)
        self.assertIsNone(observers._callback(target, "TakeDamage", "PRE")(victim, args, None, None))
        data = observers.recorder.combat[0]["data"]
        self.assertEqual(data["arguments"]["Damage"], 10)
        self.assertEqual(data["event_object_state"]["fields"]["ExpLevel"], 50)
        self.assertEqual(data["combat_participants"][0]["actor"]["fields"]["ExpLevel"], 1)

    def test_equipped_gear_capture_does_not_dump_inventory(self):
        weapon = FakeObject("Weapon.Reward", GameStage=50, ExpLevel=50,
                            DefinitionData=FakeStruct(ManufacturerGradeIndex=50))
        pawn = FakeObject(Weapon=weapon, OffHandWeapon=None, InventoryChain="must not traverse")
        result = activity.equipped_gear(FakeObject(Pawn=pawn))
        self.assertEqual(result["equipped"]["Weapon"]["fields"]["GameStage"], 50)
        self.assertNotIn("InventoryChain", str(result))

    def test_specific_quest_reward_card_is_reflected_and_can_arm_capture(self):
        function = FakeFunction("WillowGame.QuestAcceptGFxMovie:SetRewardCard", "SetRewardCard", ["MissionDef", "WPC"])
        classes["QuestAcceptGFxMovie"] = FakeClass("QuestAcceptGFxMovie", functions={"SetRewardCard": function})
        classes["MissionDefinition"] = FakeClass("MissionDefinition")
        observers = observation.Observers()
        observers.enable()
        observers.armed = True
        calls = []
        observers.capture_callback = calls.append
        callback = registry[("WillowGame.QuestAcceptGFxMovie:SetRewardCard", "POST_UNCONDITIONAL", "one_playthrough:POST_UNCONDITIONAL")]
        args = FakeStruct(MissionDef=FakeObject("Mission.FirstGun", "MissionDefinition"), WPC=None)
        callback(FakeObject(), args, None, None)
        self.assertEqual(calls, ["armed_mission_screen"])

    def test_explicit_reward_mission_wins_over_other_missions_on_screen(self):
        classes["MissionDefinition"] = FakeClass("MissionDefinition")
        wanted = FakeObject("Mission.FirstGun", "MissionDefinition")
        other = FakeObject("Mission.Unrelated", "MissionDefinition")
        movie = FakeObject(cls="QuestAcceptGFxMovie", Mission=other)
        observers = observation.Observers()
        observers.enabled = True
        target = "WillowGame.QuestAcceptGFxMovie:SetRewardCard"
        observers.status[target] = {"hits": 0, "sampled": 0}
        observers._callback(target, "SetRewardCard", "POST_UNCONDITIONAL")(
            movie, FakeStruct(MissionDef=wanted), None, None)
        self.assertIn("Mission.FirstGun", observers.recorder.missions)
        self.assertNotIn("Mission.Unrelated", observers.recorder.missions)


class TuningTests(unittest.TestCase):
    def setUp(self):
        registry.clear()
        classes.clear()
        objects.clear()

    def fixture(self, first=50, later=(61, 73)):
        class Row(FakeStruct):
            def __setattr__(self, name, value):
                if name != "MinEffectiveLevel":
                    raise AssertionError("only threshold may be written")
                object.__setattr__(self, name, value)
        rows = FakeArray(Row(MinEffectiveLevel=n, EnemyHealthMultiplier=4.0,
                             XPGainedFromQuestsMultiplier=0.66) for n in (first, *later))
        asset = FakeObject(tuning_module.PATH, "BalanceModifierDefinition", BalanceModifiers=rows)
        objects[tuning_module.PATH] = asset
        return rows

    def test_changes_only_first_threshold_and_restores_owned_edit(self):
        rows = self.fixture()
        before = [reflection.Snapshot().value(row) for row in rows]
        manager = tuning_module.UVHMTuning()
        manager.enable()
        self.assertEqual([r.MinEffectiveLevel for r in rows], [1, 61, 73])
        current = [reflection.Snapshot().value(row) for row in rows]
        before[0]["MinEffectiveLevel"] = 1
        self.assertEqual(current, before)
        manager.disable()
        self.assertEqual([r.MinEffectiveLevel for r in rows], [50, 61, 73])
        self.assertFalse(manager.owns_edit)

    def test_preexisting_threshold_is_not_claimed_or_restored(self):
        rows = self.fixture(first=1)
        manager = tuning_module.UVHMTuning()
        manager.enable()
        self.assertFalse(manager.owns_edit)
        manager.disable()
        self.assertEqual(rows[0].MinEffectiveLevel, 1)

    def test_unsupported_layout_is_not_changed(self):
        rows = self.fixture(later=(60, 73))
        manager = tuning_module.UVHMTuning()
        manager.enable()
        self.assertEqual(rows[0].MinEffectiveLevel, 50)
        self.assertFalse(manager.owns_edit)
        self.assertIn("apply", manager.errors)

    def test_pending_asset_is_corrected_in_spawn_pre_hook_without_changing_arguments(self):
        target = "WillowGame.PopulationFactoryBalancedAIPawn:CreatePopulationActor"
        fn = FakeFunction(target, "CreatePopulationActor", ["GameStage"])
        classes["PopulationFactoryBalancedAIPawn"] = FakeClass("PopulationFactoryBalancedAIPawn", functions={"CreatePopulationActor": fn})
        manager = tuning_module.UVHMTuning()
        manager.enable()
        self.assertFalse(manager.owns_edit)
        rows = self.fixture()
        callback = registry[(target, "PRE", "one_playthrough:tuning:PRE")]
        args = FakeStruct(GameStage=3)
        self.assertIsNone(callback(None, args, None, fn))
        self.assertEqual(rows[0].MinEffectiveLevel, 1)
        self.assertEqual(args.GameStage, 3)
        manager.disable()
        self.assertFalse(registry)

    def test_external_change_is_preserved_on_disable_and_reported(self):
        rows = self.fixture()
        manager = tuning_module.UVHMTuning()
        manager.enable()
        rows[0].MinEffectiveLevel = 12
        manager.disable()
        self.assertEqual(rows[0].MinEffectiveLevel, 12)
        self.assertTrue(manager.restart_required)
        self.assertIn("restore", manager.errors)

    def test_f10_reports_tuning_but_never_applies_it(self):
        rows = self.fixture()
        manager = tuning_module.UVHMTuning()
        manager.enabled = True
        observer = observation.Observers()
        observer.tuning = manager
        with tempfile.TemporaryDirectory() as directory:
            exporter = diagnostics.Diagnostics(observer, lambda *args: None)
            exporter.directory = Path(directory)
            with patch.object(manager, "apply", side_effect=AssertionError("F10 must not apply tuning")):
                path = exporter.export()
                report = json.loads(path.read_text())
        self.assertEqual(rows[0].MinEffectiveLevel, 50)
        self.assertEqual(report["implementation"]["uvhm_threshold"]["current"], 50)


class PackagingTests(unittest.TestCase):
    def test_missing_module_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "src"
            shutil.copytree(SRC, source, ignore=shutil.ignore_patterns("__pycache__"))
            (source / "one_playthrough" / "core.py").unlink()
            with self.assertRaisesRegex(RuntimeError, "Missing required"):
                builder.build(source, Path(directory) / "dist")
            self.assertFalse((Path(directory) / "dist").exists())

    def test_build_layout_same_version_protection_and_archive_previous(self):
        with tempfile.TemporaryDirectory() as directory:
            dist = Path(directory) / "dist"
            old = dist / "OnePlaythrough-0.0.9"
            old.mkdir(parents=True)
            (old / "old.sdkmod").write_bytes(b"previous release")
            destination = builder.build(SRC, dist)
            self.assertFalse(old.exists())
            with zipfile.ZipFile(dist / "OnePlaythrough-0.0.9.zip") as archive:
                self.assertEqual(archive.read("OnePlaythrough-0.0.9/old.sdkmod"), b"previous release")
            with zipfile.ZipFile(destination / "one_playthrough.sdkmod") as archive:
                self.assertEqual(set(archive.namelist()), {"one_playthrough/" + n for n in builder.REQUIRED})
                self.assertFalse({"one_playthrough/probes.py", "one_playthrough/region_probe.py"} & set(archive.namelist()))
                self.assertIsNone(archive.testzip())
            with self.assertRaisesRegex(RuntimeError, "already exists"):
                builder.build(SRC, dist)


if __name__ == "__main__":
    unittest.main()
