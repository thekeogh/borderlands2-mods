"""Mission policy contracts; actual hook/mission behavior still needs game testing."""
import importlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_prototype as f

missions = importlib.import_module("one_playthrough.missions")


class MutableMission(f.FakeObject):
    def __setattr__(self, name, value):
        if name not in {"GameStage", "bGameStageLocked"}:
            raise AssertionError("unexpected mission write: " + name)
        object.__setattr__(self, name, value)


class MutableRecord(f.FakeStruct):
    def __setattr__(self, name, value):
        if name != "GameStage":
            raise AssertionError("unexpected saved-record write: " + name)
        object.__setattr__(self, name, value)


class MissionPolicyTests(unittest.TestCase):
    def setUp(self):
        f.registry.clear(); f.classes.clear(); f.objects.clear()
        self.pc = None
        self.local = patch.object(missions, "get_pc", side_effect=lambda **kw: self.pc)
        self.local.start()
        self.addCleanup(self.local.stop)

    def fixture(self, level=10, stages=(5,), statuses=None, playthrough=2, op=0):
        definitions, records = [], []
        for i, stage in enumerate(stages):
            mission = MutableMission(f"Mission.{i}", "MissionDefinition", GameStage=stage,
                                     bGameStageLocked=True, Reward="native reward pools unchanged")
            definitions.append(mission)
            records.append(MutableRecord(MissionDef=mission, GameStage=stage,
                                          Status=(statuses or [1] * len(stages))[i],
                                          ObjectivesProgress=f.FakeArray([10, 0, 0])))
        self.pc = f.FakeObject("Map.TheWorld:PersistentLevel.PC_1", "WillowPlayerController",
                               GetCurrentPlaythrough=lambda: playthrough,
                               OverpowerChoiceValue=op, PlayerReplicationInfo=f.FakeObject(ExpLevel=level),
                               MissionPlaythroughs=f.FakeArray([
                                   f.FakeStruct(MissionList=f.FakeArray()),
                                   f.FakeStruct(MissionList=f.FakeArray()),
                                   f.FakeStruct(MissionList=f.FakeArray(records))]))
        manager = missions.MissionScaling()
        manager.enabled = True
        return manager, definitions, records

    def test_accepted_and_ready_records_raise_together_without_reward_or_objective_writes(self):
        manager, defs, records = self.fixture(stages=(5, 5, 5, 5, 5), statuses=[0, 1, 2, 3, 4])
        manager.sync(self.pc, "load")
        self.assertEqual([m.GameStage for m in defs], [5, 10, 10, 10, 5])
        self.assertEqual([r.GameStage for r in records], [5, 10, 10, 10, 5])
        self.assertEqual([r.Status for r in records], [0, 1, 2, 3, 4])
        self.assertTrue(all(r.ObjectivesProgress == [10, 0, 0] for r in records))
        self.assertTrue(all(m.Reward == "native reward pools unchanged" for m in defs))

    def test_legitimate_higher_mission_and_item_variants_not_flattened(self):
        manager, defs, records = self.fixture(stages=(15,))
        manager.sync(self.pc, "load")
        self.assertEqual((defs[0].GameStage, records[0].GameStage), (15, 15))
        self.assertEqual(manager.changes, 0)

    def test_loaded_definition_zero_can_reconcile_from_positive_saved_stage(self):
        manager, defs, records = self.fixture()
        object.__setattr__(defs[0], "GameStage", 0)
        object.__setattr__(defs[0], "bGameStageLocked", False)
        manager.sync(self.pc, "load")
        self.assertEqual((defs[0].GameStage, records[0].GameStage), (10, 10))
        self.assertTrue(defs[0].bGameStageLocked)

    def test_missing_saved_stage_is_not_invented(self):
        manager, defs, records = self.fixture()
        object.__setattr__(records[0], "GameStage", 0)
        manager.sync(self.pc, "load")
        self.assertEqual((defs[0].GameStage, records[0].GameStage), (5, 0))
        self.assertIn("write", manager.errors)

    def test_normal_tvhm_and_op_contexts_never_write(self):
        for pt, op in [(0, 0), (1, 0), (2, 1)]:
            with self.subTest(pt=pt, op=op):
                manager, defs, records = self.fixture(playthrough=pt, op=op)
                manager.sync(self.pc, "load")
                self.assertEqual((defs[0].GameStage, records[0].GameStage), (5, 5))

    def test_missing_or_nonlocal_controller_never_writes(self):
        manager, defs, records = self.fixture()
        local = self.pc
        manager.sync(None, "menu")
        manager.sync(f.FakeObject("Other.Controller"), "remote")
        self.assertEqual((defs[0].GameStage, records[0].GameStage), (5, 5))
        self.pc = None
        manager.sync(local, "loading")
        self.assertEqual(defs[0].GameStage, 5)

    def test_native_level_up_updates_all_accepted_missions_but_ignores_load_notification(self):
        manager, defs, records = self.fixture()
        cb = manager.callback("OnExpLevelChange", "POST_UNCONDITIONAL")
        self.assertIsNone(cb(self.pc, f.FakeStruct(bFeedback=False, bNaturalLevelup=False), None, None))
        self.assertEqual(defs[0].GameStage, 5)
        cb(self.pc, f.FakeStruct(bFeedback=False, bNaturalLevelup=True), None, None)
        self.assertEqual(defs[0].GameStage, 10)
        object.__setattr__(self.pc.PlayerReplicationInfo, "ExpLevel", 11)
        cb(self.pc, f.FakeStruct(bFeedback=True, bNaturalLevelup=True), None, None)
        self.assertEqual((defs[0].GameStage, records[0].GameStage), (11, 11))

    def test_ui_event_uses_explicit_mission_not_tracked_or_unrelated_mission(self):
        manager, defs, records = self.fixture(stages=(5, 5))
        args = f.FakeStruct(MissionDef=defs[1], WPC=self.pc)
        manager.callback("SetRewardCard", "PRE")(f.FakeObject(), args, None, None)
        self.assertEqual([m.GameStage for m in defs], [5, 10])
        self.assertIs(args.MissionDef, defs[1])
        manager.callback("SetRewardCard", "PRE")(f.FakeObject(), f.FakeStruct(WPC=self.pc), None, None)
        self.assertEqual(defs[0].GameStage, 5)

    def test_scripted_acceptance_updates_only_the_notified_mission(self):
        manager, defs, records = self.fixture(stages=(5, 5))
        data = f.FakeStruct(Mission=defs[1], Status=1)
        manager.callback("ClientReceiveMissionStatus", "POST_UNCONDITIONAL")(
            self.pc, f.FakeStruct(MissionStatusData=data), None, None)
        self.assertEqual([r.GameStage for r in records], [5, 10])

    def test_before_completion_backstop_raises_before_native_reward_and_preserves_branch_arg(self):
        manager, defs, records = self.fixture(level=25, stages=(20,), statuses=[3])
        manager.callback("UpdateMissionStatus", "PRE")(
            self.pc, f.FakeStruct(Mission=defs[0], NewMissionStatus=4), None, None)
        args = f.FakeStruct(Mission=defs[0], bGrantAltReward=True)
        manager.callback("ServerGrantMissionRewards", "PRE")(self.pc, args, None, None)
        self.assertEqual((defs[0].GameStage, records[0].GameStage), (25, 25))
        self.assertTrue(args.bGrantAltReward)

    def test_payout_level_up_does_not_change_current_reward_stage_mid_transaction(self):
        manager, defs, records = self.fixture(level=20, stages=(20, 19), statuses=[3, 1])
        grant = f.FakeStruct(Mission=defs[0], bGrantAltReward=False)
        manager.callback("ServerGrantMissionRewards", "PRE")(self.pc, grant, None, None)
        object.__setattr__(self.pc.PlayerReplicationInfo, "ExpLevel", 21)
        manager.callback("OnExpLevelChange", "POST_UNCONDITIONAL")(
            self.pc, f.FakeStruct(bNaturalLevelup=True), None, None)
        self.assertEqual([m.GameStage for m in defs], [20, 21])
        self.assertEqual([r.GameStage for r in records], [20, 21])
        manager.callback("ServerGrantMissionRewards", "POST_UNCONDITIONAL")(self.pc, grant, None, None)
        object.__setattr__(records[0], "Status", 4)  # Native completion after grant returns.
        manager.callback("UpdateMissionStatus", "POST_UNCONDITIONAL")(
            self.pc, f.FakeStruct(Mission=defs[0], NewMissionStatus=4), None, None)
        self.assertEqual(defs[0].GameStage, 20)
        self.assertFalse(manager.payouts)

    def test_nested_payouts_preserve_guard_until_outer_return(self):
        manager, defs, records = self.fixture()
        args = f.FakeStruct(Mission=defs[0])
        pre = manager.callback("ServerGrantMissionRewards", "PRE")
        post = manager.callback("ServerGrantMissionRewards", "POST_UNCONDITIONAL")
        pre(self.pc, args, None, None); pre(self.pc, args, None, None)
        post(self.pc, args, None, None)
        self.assertEqual(manager.payouts["Mission.0"], 1)
        post(self.pc, args, None, None)
        self.assertFalse(manager.payouts)

    def test_partial_write_failure_restores_definition_and_keeps_record(self):
        manager, defs, records = self.fixture()
        class LockedRecord(MutableRecord):
            def __setattr__(self, name, value):
                raise RuntimeError("record write failed")
        failed = LockedRecord(MissionDef=defs[0], GameStage=5, Status=1)
        self.pc.MissionPlaythroughs[2].MissionList[0] = failed
        manager.sync(self.pc, "load")
        self.assertEqual((defs[0].GameStage, failed.GameStage), (5, 5))
        self.assertIn("record write failed", manager.errors["write"])

    def test_repeated_load_is_idempotent_and_disable_does_not_undo_saved_stages(self):
        manager, defs, records = self.fixture()
        manager.sync(self.pc, "load")
        manager.sync(self.pc, "load_again")
        self.assertEqual(manager.changes, 1)
        manager.disable()
        self.assertEqual((defs[0].GameStage, records[0].GameStage), (10, 10))
        object.__setattr__(self.pc.PlayerReplicationInfo, "ExpLevel", 11)
        manager.sync(self.pc, "disabled")
        self.assertEqual(records[0].GameStage, 10)

    def test_hooks_registered_using_reflected_owner_and_removed(self):
        manager, defs, records = self.fixture()
        fn = f.FakeFunction("WillowGame.WillowPlayerController:OnExpLevelChange", "OnExpLevelChange", [])
        f.classes["WillowPlayerController"] = f.FakeClass("WillowPlayerController", functions={"OnExpLevelChange": fn})
        manager.install()
        target = ("WillowGame.WillowPlayerController:OnExpLevelChange", "POST_UNCONDITIONAL", "one_playthrough:missions:POST_UNCONDITIONAL")
        self.assertIn(target, f.registry)
        manager.disable()
        self.assertNotIn(target, f.registry)

    def test_diagnostics_reports_policy_but_cannot_trigger_mission_write(self):
        manager, defs, records = self.fixture()
        observer = f.observation.Observers()
        observer.mission_scaling = manager
        with tempfile.TemporaryDirectory() as directory:
            exporter = f.diagnostics.Diagnostics(observer, lambda *args: None)
            exporter.directory = Path(directory)
            with patch.object(manager, "sync", side_effect=AssertionError("F10 must not change missions")):
                report = json.loads(exporter.export().read_text())
        self.assertTrue(report["implementation"]["mission_scaling"]["enabled"])
        self.assertEqual((defs[0].GameStage, records[0].GameStage), (5, 5))


if __name__ == "__main__":
    unittest.main()
