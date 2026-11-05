#!/usr/bin/env python3
"""Build isolated test characters from the supplied clean Axton; no mod changes."""
from __future__ import annotations

import base64
import copy
import csv
import hashlib
import json
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import uuid
import zipfile
from pathlib import Path

import build_plan_b as common

HERE = Path(__file__).resolve().parent
ROOT = common.ROOT
VERSION = "0.2.1"
DESTINATION = ROOT / "dist" / ("TestSaves-" + VERSION)
SOURCE = ROOT / "saves/Save0001.sav"
ALLOWED_FIELDS = {2, 3, 4, 6, 11, 13, 16, 17, 18, 19, 20, 21, 34, 36, 37, 53, 54}


def refs(block, field):
    values = re.findall(r"^" + re.escape(field) + r"\((\d+)\)=\w+'([^']+)'", block, re.M)
    if [int(i) for i, _ in values] != list(range(len(values))):
        raise RuntimeError("Noncontiguous reference array: " + field)
    return [path for _, path in values]


def ref_value(block, field):
    value = common.scalar(block, field)
    if value == "None":
        return None
    return value.partition("'")[2].rpartition("'")[0]


class PackBuilder:
    def __init__(self):
        revision = subprocess.check_output(["git", "-C", str(common.EDITOR), "rev-parse", "HEAD"], text=True).strip()
        if revision != common.EDITOR_COMMIT:
            raise RuntimeError("Unreviewed save-editor checkout")
        sys.path.insert(0, str(common.EDITOR))
        from borderlands.bl2 import AppBL2
        from borderlands.savefile import BaseApp
        from borderlands.datautil.protobuf import read_protobuf, write_protobuf
        from borderlands.datautil.protobuf import read_repeated_protobuf_value, write_repeated_protobuf_value
        self.app = AppBL2([str(SOURCE)])
        self.unwrap = BaseApp.unwrap_player_data
        self.read, self.write = read_protobuf, write_protobuf
        self.read_packed, self.write_packed = read_repeated_protobuf_value, write_repeated_protobuf_value
        self.source = SOURCE.read_bytes()
        if common.sha(self.source) != common.SOURCE_HASH:
            raise RuntimeError("Input differs from inspected clean Axton")
        decoded = self.unwrap(self.source)
        if self.unwrap(self.app.wrap_player_data(decoded)) != decoded:
            raise RuntimeError("Unmodified save roundtrip failed")
        self.baseline = self.read(decoded)
        self.expansion = common.expansion_state(self.baseline, self.read)
        if self.expansion["playthrough"] != 2 or self.expansion["op_choice"] != 0:
            raise RuntimeError("Expected UVHM/OP0")
        common.WORK.mkdir(parents=True, exist_ok=True)
        common.saved_station()  # Fetch/verify the pinned table on a fresh checkout.
        self.travel = json.loads((common.WORK / "gibbed-travel-stations.json").read_bytes())
        if common.sha((common.WORK / "gibbed-travel-stations.json").read_bytes()) != common.TRAVEL_TABLE_HASH:
            raise RuntimeError("Unreviewed station table")
        index = common.dump_index()
        self.data, self.dump_hashes = {}, {}
        for cls in ("MissionDefinition", "MissionObjectiveDefinition", "MissionObjectiveSetDefinition",
                    "MissionObjectiveSetBranchingDefinition", "DownloadableExpansionDefinition",
                    "DownloadablePackageDefinition"):
            self.data[cls], self.dump_hashes[cls] = common.get_dump(cls, index)
        self.missions = self.data["MissionDefinition"]
        self.objectives = self.data["MissionObjectiveDefinition"]
        self.sets = {**self.data["MissionObjectiveSetDefinition"], **self.data["MissionObjectiveSetBranchingDefinition"]}
        self.gear = json.loads((HERE / "gear_seeds.json").read_text())
        self.verify_gear_seeds()

    def verify_gear_seeds(self):
        names = set()
        for seed in self.gear["items"]:
            raw = base64.b64decode(seed["base64"], validate=True)
            kind, values, key = self.app.unwrap_item(raw)
            if kind != seed["is_weapon"] or len(values) != 17:
                raise RuntimeError("Unexpected gear layout: " + seed["name"])
            if self.app.wrap_item(is_weapon=kind, values=values, key=key) != raw:
                raise RuntimeError("Gear seed CRC/serialization mismatch: " + seed["name"])
            if seed["name"] in names:
                raise RuntimeError("Duplicate gear name")
            names.add(seed["name"])

    def mission(self, path, status, stage, *, special=None):
        block = self.missions[path]
        objectives = refs(block, "ObjectiveDefs")
        sets = refs(block, "ObjectiveSetDefs")
        maxima = [int(common.scalar(self.objectives[p], "ObjectiveCount")) for p in objectives]
        completion = [i for i, p in enumerate(sets) if common.scalar(self.sets[p], "bCanCompleteMission") == "True"]
        if status in (3, 4):
            if not completion:
                raise RuntimeError("No completion set: " + path)
            counts, active_set = list(maxima), completion[-1]
        else:
            counts = [0] * len(objectives)
            active_set = sets.index(ref_value(block, "InitialObjectiveSet"))
        if special and special["kind"] == "boss":
            counts = [n if i < special["complete_objectives_before"] else 0 for i, n in enumerate(maxima)]
            active_set = sets.index(path + special["active_set_suffix"])
        if special and special["kind"] == "alternative":
            # Collected boxes; interaction with either recipient must choose the branch.
            counts = [maxima[0]] + [0] * (len(maxima) - 1)
        dlc = ref_value(block, "DlcExpansion")
        package_id = 0
        if dlc:
            package = ref_value(self.data["DownloadableExpansionDefinition"][dlc], "PackageDef")
            package_id = int(common.scalar(self.data["DownloadablePackageDefinition"][package], "PackageId"))
        record = {1: [[2, path.encode()]], 2: [[0, status]], 3: [[0, int(dlc is not None)]],
                  4: [[0, package_id]], 5: [[2, self.write_packed(counts, 0)]],
                  6: [[0, active_set]], 8: [[0, 0]], 9: [[0, 0]], 10: [[0, 1]], 11: [[0, stage]]}
        audit = {"path": path, "name": common.scalar(block, "MissionName"), "status": status,
                 "stage": stage, "objective_progress": counts, "objective_maxima": maxima,
                 "active_set_index": active_set, "active_set": sets[active_set],
                 "dlc_package_id": package_id, "dlc_expansion": dlc}
        return [2, self.write(record)], audit

    def setup_missions(self, player, scenario):
        records, audits, visiting = {}, {}, set()
        def ensure(path, status=4, stage=None, special=None):
            if path in records:
                if status != 4:
                    raise RuntimeError("Duplicate active mission: " + path)
                return
            if path in visiting:
                raise RuntimeError("Cyclic mission dependencies")
            visiting.add(path)
            stage = scenario["stage"] if stage is None else stage
            for dependency in refs(self.missions[path], "Dependencies"):
                ensure(dependency, 4, stage)
            records[path], audits[path] = self.mission(path, status, stage, special=special)
            visiting.remove(path)

        kind, target = scenario["kind"], scenario["target"]
        if kind == "alternative":
            ensure(target, 3, special=scenario)
            main = scenario["main"]
            ensure(main, 1, scenario["level"])
            tracked = target
        else:
            main = target
            ensure(main, 3 if kind == "reward" else 1)
            tracked = main
            if kind == "boss":
                ensure(scenario["side"], 1, special=scenario)
                tracked = scenario["side"]
        uvhm = self.read(player[18][2][1])
        uvhm[2], uvhm[3] = [[2, tracked.encode()]], list(records.values())
        player[18][2] = [2, self.write(uvhm)]
        player[21] = [[0, int(common.scalar(self.missions[main], "MissionNumber"))]]
        player[37] = [[0, int(common.scalar(self.missions[tracked], "MissionNumber"))]]
        return list(audits.values()), tracked

    def inject_gear(self, player, scenario):
        audit = []
        for seed in self.gear["items"]:
            raw = base64.b64decode(seed["base64"], validate=True)
            kind, values, _ = self.app.unwrap_item(raw)
            values[4] = values[5] = scenario["level"]
            key = int.from_bytes(hashlib.sha256(f"{scenario['number']}:{seed['name']}".encode()).digest()[:4], "big") & 0x7FFFFFFF
            serial = self.app.wrap_item(is_weapon=kind, values=values, key=key)
            actual_kind, actual_values, actual_key = self.app.unwrap_item(serial)
            if (actual_kind, actual_values, actual_key) != (kind, values, key):
                raise RuntimeError("Rescaled gear did not roundtrip")
            if self.app.wrap_item(is_weapon=kind, values=actual_values, key=actual_key) != serial:
                raise RuntimeError("Rescaled gear CRC mismatch")
            if kind:
                entry = {1: [[2, serial]], 2: [[0, 0]], 3: [[0, 1]], 4: [[0, 1]]}
                player.setdefault(54, []).append([2, self.write(entry)])
            else:
                entry = {1: [[2, serial]], 2: [[0, 1]], 3: [[0, int(seed["equipped"])]], 4: [[0, 1]]}
                player.setdefault(53, []).append([2, self.write(entry)])
            audit.append({"name": seed["name"], "level": scenario["level"], "game_stage": scenario["level"],
                          "weapon": bool(kind), "equipped": bool(seed["equipped"]),
                          "purpose": seed["purpose"], "serial_sha256": common.sha(serial),
                          "source": seed["source"]})
        return audit

    def resources(self, player):
        market = self.read_packed(player[36][0][1], 0)
        market += [0] * (len(self.app.black_market_keys) - len(market))
        for i in range(7):
            market[i] = 7
        market[7] = 4  # 12 + 4*3 = 24 backpack spaces; bank unchanged.
        player[36] = [[2, self.write_packed(market, 0)]]
        player[11] = []
        for ammo, (resource, pool) in self.app.ammo_resources.items():
            if ammo == "laser":
                continue
            amount = float(self.app.black_market_ammo[ammo][7])
            amount_bits = struct.unpack("<I", struct.pack("<f", amount))[0]
            record = {1: [[2, resource.encode()]], 2: [[2, pool.encode()]],
                      3: [[5, amount_bits]], 4: [[0, 7]]}
            player[11].append([2, self.write(record)])
        currency = self.read_packed(player[6][0][1], 0)
        currency[0] = 10000
        player[6] = [[2, self.write_packed(currency, 0)]]

    def create(self, scenario):
        player = copy.deepcopy(self.baseline)
        level = scenario["level"]
        experience = self.app.required_xp[level - 1]
        if scenario.get("boundary"):
            if scenario["boundary"] != level + 1:
                raise RuntimeError("Non-adjacent level boundary")
            margin = scenario.get("xp_margin", 1)
            if not isinstance(margin, int) or margin < 1:
                raise RuntimeError("Invalid boundary XP margin")
            experience = self.app.required_xp[level] - margin
            if experience < self.app.required_xp[level - 1]:
                raise RuntimeError("XP margin would put character below starting level")
        player[2], player[3], player[4] = [[0, level]], [[0, experience]], [[0, max(0, level - 4)]]
        station = self.travel[scenario["station"]]
        resource_name = station["resource_name"]
        if not resource_name or resource_name.startswith("GD_"):
            raise RuntimeError("Invalid saved travel resource name")
        player[16], player[17] = [[2, resource_name.encode()]], [[2, resource_name.encode()]]
        missions, tracked = self.setup_missions(player, scenario)
        appearance = self.read(player[19][0][1]); appearance[1] = [[2, scenario["name"].encode()]]
        player[19] = [[2, self.write(appearance)]]
        save_id = 0x7F00 + scenario["number"]
        player[20] = [[0, save_id]]
        identity = uuid.uuid5(uuid.NAMESPACE_URL, f"one-playthrough-test-save:{common.SOURCE_HASH}:{VERSION}:{save_id}")
        guid = {i + 1: [[5, value]] for i, value in enumerate(struct.unpack("<4I", identity.bytes_le))}
        player[34] = [[2, self.write(guid)]]
        slots = self.read(player[13][0][1])
        slots[1], slots[2], slots[3] = [[0, 24]], [[0, scenario["slots"]]], [[0, scenario["slots"] - 2]]
        player[13] = [[2, self.write(slots)]]
        gear = self.inject_gear(player, scenario)
        self.resources(player)
        changed = {k for k in self.baseline.keys() | player.keys() if self.baseline.get(k) != player.get(k)}
        if not changed <= ALLOWED_FIELDS:
            raise RuntimeError("Unexpected changed protobuf fields")
        if player[18][:2] != self.baseline[18][:2]:
            raise RuntimeError("Other playthrough mission data changed")
        if player[53][:len(self.baseline[53])] != self.baseline[53]:
            raise RuntimeError("Original packed items/UVHM expansion records changed")
        if common.expansion_state(player, self.read) != self.expansion:
            raise RuntimeError("UVHM/OP selection changed")
        output = self.app.wrap_player_data(self.write(player))
        if self.read(self.unwrap(output)) != player:
            raise RuntimeError("Complete save roundtrip mismatch")
        result = dict(scenario)
        result.update(save_file=f"Save{save_id:04X}.sav", save_id=save_id, experience=experience,
                      map=station["level_name"], station_resource=resource_name,
                      station_dlc=station.get("dlc_expansion"), tracked_mission=tracked,
                      missions=missions, gear=gear, sha256=common.sha(output),
                      changed_protobuf_fields=sorted(changed), game_verified=False,
                      checks={"sha1_crc_and_raw_roundtrip": True, "station_resource_verified": True,
                              "original_inventory_expansion_records_preserved": True,
                              "other_playthrough_missions_preserved": True, "uvhm2_op0_preserved": True,
                              "all_kit_gear_on_level_and_serial_roundtrips": True})
        return output, result


def instructions(records):
    intro = f"""# One Playthrough — test saves {VERSION}

**11 new checkpoints · Keep One Playthrough 0.1.7 and your patched EXE.**

**Revision 0.2.1:** boundary saves **05, 06 and 07** now start **5,000 XP below** the next level to allow for arrival/discovery XP. If you installed 0.2.0, replace only those three saves; the others are byte-identical. No earlier tests need repeating.

Original `saves/Save0001.sav` is untouched. These are synthetic test characters with unique names/IDs. The already-passed Plan B save 01 is not repeated.

## Start here

1. **Fully close the game.** Copy only the `.sav` files from [saves](saves/) beside your Windows character saves. Do not overwrite an unrelated character if a filename collides.
2. Select the **OP test character by name**, choosing **UVHM** if prompted.
3. Start with **02 → 03 → 04**. Then try **08 / 09 / 10 / 12**, followed by **05 / 06 / 07 / 11**.

You can report a partial batch; no need to finish all eleven at once.

> **Filename numbering is hexadecimal:** `Save7F0A.sav` = test **10**, `Save7F0B.sav` = **11**, `Save7F0C.sav` = **12**. In-game character names use ordinary test numbers.

## Every test

1. Wait for the HUD after loading; press **F10 before the test**.
2. Follow that character's steps below; press **F10 after the relevant action/reward**.
3. Where requested, **save-quit → reload → F10**.
4. Move the exported JSONs into `logs/`, optionally grouped as `logs/02/`, `logs/03/`, etc. Report the test number, what happened, reward/item/enemy levels and anything odd.

> **Broken checkpoint?** If the spawn, mission, NPC or door is wrong, press **F10 and stop that character's test**. No need to replay missing story or keep attempting it.

## Gear and survival

All supplied gear matches the character's starting level.

| Gear | Location / use |
| --- | --- |
| Double Penetrating Unkempt Harold | Backpack; equip for damage |
| Grog Nozzle | Backpack; equip for slag/healing |
| Shock Norfleet + fire Norfleet | Backpack; optional heavy weapons |
| Infinity | Backpack; spare gun |
| The Sham + Magic Missile ×4 | Initially equipped |
| Grounded The Bee | Backpack; spare shield |

- **Equip Harold and Grog before fighting.** Fire launchers from a safe distance to avoid your own blast damage.
- You have generous ammo, **24 backpack spaces** and **$10,000**.
- Normal level-earned skill points are unspent; allocate them if useful. No extra skill points or OP unlocks.
- Spend some ammo before testing ammo pickups; initially stocked pools may be full.
- Do not sell the kit, count it as a random drop or expect owned gear to level with you.

The kit is stronger than normal progression, but does not grant invincibility. Native enemy scaling and the mod are untouched; this is not a vanilla combat-balance benchmark.

## Mission rewards

**Arm “Capture next mission screen” before opening a turn-in card.** Note the visible mission level and reward item level, collect, then press **F10 promptly**.

Native item variation is allowed: a locked mission stage does not guarantee all equipment matches that stage exactly.

**Redo a test:** fully quit and re-copy only that test's `.sav`. This resets that test character.

## Checkpoint overview

| Test | Character | Player level | Save file |
| --- | --- | --- | --- |"""
    lines = [intro]
    for row in records:
        lines.append(f"| {row['number']:02d} | {row['name']} | {row['level']} | [{row['save_file']}](saves/{row['save_file']}) |")
    lines.append("")
    for row in records:
        lines += [f"## Test {row['number']:02d}: {row['name']}", "",
                  f"**{row['goal']}**", "",
                  f"**Player:** {row['level']} · **Mission stage:** {row['stage']} · **Weapon slots:** {row['slots']}", "",
                  f"**Save:** `{row['save_file']}` · **Destination ID:** `{row['station_resource']}`", ""]
        for i, step in enumerate(row["steps"], 1):
            step = step.replace("Capture next mission screen", "**Capture next mission screen**")
            step = step.replace("F10", "**F10**")
            lines.append(f"{i}. {step}")
        lines.append("")
    lines += ["## Validation and references", "",
              "Each binary passes SHA-1/CRC, raw-protobuf and rescaled-gear serial roundtrips. UVHM expansion records and the original save are preserved. Travel IDs use Gibbed's verified ResourceName strings; mission objectives and package IDs use game-data dumps.", "",
              "**These new checkpoints and gift gear still need your first in-game test.** The earlier Plan B checkpoint validates the approach, not every NPC, door, DLC or scripted state here.", "",
              "No EXE, mod, enemy definitions, loot pools or native reward definitions were edited.", "",
              "[Full setup and sources](manifest.json) · [Validation details](VALIDATION.txt) · [Optional checklist](CHECKLIST.csv) · [Item-code attribution](ITEM-CODES-LICENSE.txt)", ""]
    return "\n".join(lines)


def archive_previous():
    for folder in sorted((ROOT / "dist").glob("TestSaves-*")):
        if not folder.is_dir():
            continue
        archive = folder.parent / (folder.name + ".zip")
        if archive.exists():
            raise RuntimeError("Refusing to overwrite old test-save archive")
        files = sorted(p for p in folder.rglob("*") if p.is_file())
        with tempfile.TemporaryDirectory(dir=common.WORK) as tmp:
            temp_archive = Path(tmp) / archive.name
            with zipfile.ZipFile(temp_archive, "w", zipfile.ZIP_DEFLATED) as z:
                for p in files:
                    z.write(p, p.relative_to(folder.parent))
            with zipfile.ZipFile(temp_archive) as z:
                if z.testzip() is not None:
                    raise RuntimeError("Old archive is corrupt")
                for p in files:
                    if z.read(str(p.relative_to(folder.parent))) != p.read_bytes():
                        raise RuntimeError("Old archive differs from files")
            archive.write_bytes(temp_archive.read_bytes())
        for p in files:
            p.unlink()
        for sub in sorted((p for p in folder.rglob("*") if p.is_dir()), reverse=True):
            sub.rmdir()
        folder.rmdir()


def build():
    if DESTINATION.exists():
        raise RuntimeError("Release already exists")
    builder = PackBuilder()
    scenarios = json.loads((HERE / "scenarios.json").read_text())
    if [s["number"] for s in scenarios] != list(range(2, 13)):
        raise RuntimeError("Expected exactly the reviewed checkpoints 02–12")
    with tempfile.TemporaryDirectory(dir=common.WORK, prefix="test-pack-") as tmp:
        stage = Path(tmp) / DESTINATION.name
        saves = stage / "saves"; saves.mkdir(parents=True)
        records, guids = [], set()
        for scenario in scenarios:
            binary, record = builder.create(scenario)
            (saves / record["save_file"]).write_bytes(binary)
            reread = builder.read(builder.unwrap((saves / record["save_file"]).read_bytes()))
            guid = reread[34][0][1]
            if guid in guids:
                raise RuntimeError("Duplicate save GUID")
            guids.add(guid)
            records.append(record)
        manifest = {"version": VERSION, "mod_version": "0.1.7", "game_verified": False,
                    "input_sha256": common.sha(builder.source), "effective_expansion_state": builder.expansion,
                    "checkpoints": records, "kit_source": builder.gear,
                    "sources": {"editor": "https://github.com/loot-midget/borderlands2",
                                "editor_commit": common.EDITOR_COMMIT,
                                "xp_reference": "https://github.com/gibbed/Gibbed.Borderlands2/blob/master/projects/Gibbed.Borderlands2.GameInfo/Experience.cs",
                                "travel_table": common.TRAVEL_TABLE_URL,
                                "travel_table_sha256": common.TRAVEL_TABLE_HASH,
                                "game_datapack": common.DATAPACK,
                                "dump_sha256": builder.dump_hashes},
                    "limitations": ["Synthetic mission/world setup and gift-gear acceptance need in-game validation",
                                    "DLC arrival saves intentionally let the game assign the local intro mission",
                                    "Test gear changes player performance, not enemy scaling; it is not a vanilla damage benchmark",
                                    "No changes to SDK mod or EXE"]}
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        (stage / "README.md").write_text(instructions(records))
        shutil.copyfile(HERE / "ITEM-CODES-LICENSE.txt", stage / "ITEM-CODES-LICENSE.txt")
        with (stage / "CHECKLIST.csv").open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["Test", "Character", "Save", "Player level", "Mission stage", "Goal", "Result / notes"])
            for r in records:
                writer.writerow([r["number"], r["name"], r["save_file"], r["level"], r["stage"], r["goal"], ""])
        if SOURCE.read_bytes() != builder.source:
            raise RuntimeError("Original input changed")
        archive_previous()
        shutil.copytree(stage, DESTINATION)
    print(f"Built {len(records)} checkpoints: {DESTINATION}")
    print("All saves/kit serials roundtrip; UVHM2/OP0 and opaque expansion records preserved; original unchanged.")


if __name__ == "__main__":
    build()
