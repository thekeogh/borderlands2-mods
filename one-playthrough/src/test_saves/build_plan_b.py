#!/usr/bin/env python3
"""Create one isolated Plan B turn-in candidate; never modify the supplied save.

Uses a pinned, unmodified loot-midget/borderlands2 checkout for compression/protobuf.
Reads objective counts and set indices from the public OpenBLCMM BL2 datapack.
All packed inventory records, including Gearbox's UVHM expansion records, remain opaque.
"""
from __future__ import annotations

import argparse
import binascii
import copy
import hashlib
import json
import re
import struct
import subprocess
import sys
import urllib.request
import uuid
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EDITOR = ROOT / "src/research/save-editor"
EDITOR_COMMIT = "2f9f17d4a159d64a962c8f998d679c860293da7a"
WORK = ROOT / "src/research/save-work"
DATAPACK = "https://github.com/BLCM/OpenBLCMM-Data/releases/download/2023-04-21-01/blcmm_data_BL2-2023-04-20-01.jar"
DIRECTORY_START, DIRECTORY_SIZE = 344273543, 340008
TARGET = "GD_Episode04.M_Ep4_WelcomeToSanctuary"
STATION = "GD_FastTravelStations.Sanctuary.Sanctuary"
TRAVEL_TABLE_URL = "https://raw.githubusercontent.com/gibbed/Borderlands2Dumps/08c9a885e5939cc62ca82e9277e2f95580bf7850/Travel%20Stations.json"
TRAVEL_TABLE_HASH = "13597a2e29e6bc4ef34cb70ccb5db2b59ab9872b9c916cbe88c5ff03b02198ab"
SAVE_ID = 0x7F01
NAME = "OP Test 01 Plan B"
SOURCE_HASH = "56184c07d675707f44f8c75c1e9f309cd97169ab1dfc7b5965e1af8e15034be8"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify_editor():
    """Verify the pinned sources even when the checkout is vendored without .git."""
    hashes = Path(__file__).with_name("editor_snapshot_hashes.json")
    if hashes.exists():
        manifest = json.loads(hashes.read_text())
        if manifest["commit"] != EDITOR_COMMIT:
            raise RuntimeError("Unreviewed editor source manifest")
        actual = {str(p.relative_to(EDITOR)) for p in EDITOR.rglob("*.py")}
        if actual != set(manifest["files"]):
            raise RuntimeError("Editor source file list differs from pinned upstream")
        for name, digest in manifest["files"].items():
            if sha((EDITOR / name).read_bytes()) != digest:
                raise RuntimeError("Editor source differs from pinned upstream: " + name)
        return
    if not (EDITOR / ".git").exists() or subprocess.check_output(
            ["git", "-C", str(EDITOR), "rev-parse", "HEAD"], text=True).strip() != EDITOR_COMMIT:
        raise RuntimeError("Unreviewed save-editor checkout")


def saved_station():
    """Save fields use ResourceName, not a definition's UObject path."""
    cache = WORK / "gibbed-travel-stations.json"
    if cache.exists():
        data = cache.read_bytes()
    else:
        with urllib.request.urlopen(TRAVEL_TABLE_URL, timeout=30) as response:
            data = response.read()
        cache.write_bytes(data)
    if sha(data) != TRAVEL_TABLE_HASH:
        raise RuntimeError("Travel station reference differs from reviewed data")
    station = json.loads(data)[STATION]
    if station["level_name"] != "Sanctuary_P" or station.get("dlc_expansion"):
        raise RuntimeError("Expected the base-game Sanctuary station")
    if station["resource_name"] != "Sanctuary":
        raise RuntimeError("Unexpected Sanctuary save identifier")
    return station["resource_name"]


def remote_range(start, end):
    req = urllib.request.Request(DATAPACK, headers={"Range": f"bytes={start}-{end}"})
    with urllib.request.urlopen(req, timeout=30) as response:
        if response.status != 206:
            raise RuntimeError("Datapack server did not honor the bounded range request")
        data = response.read(end - start + 2)
    if len(data) != end - start + 1:
        raise RuntimeError("Unexpected datapack range length")
    return data


def dump_index():
    cached = WORK / "datapack-directory.bin"
    data = cached.read_bytes() if cached.exists() else remote_range(
        DIRECTORY_START, DIRECTORY_START + DIRECTORY_SIZE - 1)
    if len(data) != DIRECTORY_SIZE:
        raise RuntimeError("Unexpected datapack directory size")
    if not cached.exists():
        cached.write_bytes(data)
    entries, pos = {}, 0
    while data[pos:pos + 4] == b"PK\x01\x02":
        v = struct.unpack_from("<4s6H3I5H2I", data, pos)
        name_len, extra_len, comment_len = v[10:13]
        name = data[pos + 46:pos + 46 + name_len].decode()
        entries[name] = {"method": v[4], "crc": v[7], "compressed": v[8],
                         "size": v[9], "offset": v[16]}
        pos += 46 + name_len + extra_len + comment_len
    if pos != len(data) or len(entries) != 3759:
        raise RuntimeError("Unexpected datapack ZIP directory layout")
    return entries


def get_dump(cls, index):
    entry = index[f"data/BL2/dumps/{cls}.dump.1"]
    cached = WORK / (cls + ".dump")
    if cached.exists():
        data = cached.read_bytes()
    else:
        header = remote_range(entry["offset"], entry["offset"] + 29)
        if header[:4] != b"PK\x03\x04" or entry["method"] != 8:
            raise RuntimeError("Unexpected datapack member format")
        name_len, extra_len = struct.unpack_from("<HH", header, 26)
        start = entry["offset"] + 30 + name_len + extra_len
        compressed = remote_range(start, start + entry["compressed"] - 1)
        data = zlib.decompress(compressed, -15)
    if len(data) != entry["size"] or binascii.crc32(data) != entry["crc"]:
        raise RuntimeError(f"Datapack integrity check failed for {cls}")
    if not cached.exists():
        cached.write_bytes(data)
    parts = re.split(r"\*\*\* Property dump for object '[^ ]+ ([^']+)' \*\*\*\r?\n",
                     data.decode("latin1"))
    return dict(zip(parts[1::2], parts[2::2])), sha(data)


def scalar(block, name):
    match = re.search(r"^" + re.escape(name) + r"=(.*)$", block, re.M)
    if not match:
        raise RuntimeError(f"Missing dump field {name}")
    return match.group(1).strip()


def references(block, field, cls):
    values = re.findall(r"^" + re.escape(field) + r"\((\d+)\)=" + cls + r"'([^']+)'", block, re.M)
    if [int(i) for i, _ in values] != list(range(len(values))):
        raise RuntimeError(f"Noncontiguous {field} in dump")
    return [path for _, path in values]


def expansion_state(player, read_protobuf):
    extras = {}
    for _wire, packed in player.get(53, []):
        item = read_protobuf(packed)
        quantity = item.get(2, [[0, 0]])[0][1] & 0xFFFFFFFF
        if quantity >= 0x80000000:
            quantity -= 0x100000000
        if quantity < 0:
            record_id = (-quantity) & 0xFF
            if record_id in extras:
                raise RuntimeError("Duplicate Gearbox expansion record")
            extras[record_id] = (((-quantity) >> 8) & 0x7FFFFF,
                                 item.get(4, [[0, 0]])[0][1])
    return {"playthrough": player[49][0][1] + extras.get(2, (0, 0))[0],
            "playthroughs_completed": player[7][0][1] + extras.get(2, (0, 0))[1],
            "has_played_uvhm": extras.get(3, (0, 0))[0],
            "op_choice": extras.get(5, (0, 0))[0]}


def build(source, destination):
    if destination.exists():
        raise RuntimeError("Destination exists; refusing to overwrite a test-save release")
    verify_editor()
    sys.path.insert(0, str(EDITOR))
    from borderlands.bl2 import AppBL2
    from borderlands.savefile import BaseApp
    from borderlands.datautil.protobuf import read_protobuf, write_protobuf, write_repeated_protobuf_value

    original = source.read_bytes()
    if sha(original) != SOURCE_HASH:
        raise RuntimeError("This first candidate is pinned to the inspected clean Axton input")
    app = AppBL2([str(source)])
    decoded = BaseApp.unwrap_player_data(original)  # verifies outer SHA-1 and inner CRC
    assert BaseApp.unwrap_player_data(app.wrap_player_data(decoded)) == decoded
    baseline = read_protobuf(decoded)
    state = expansion_state(baseline, read_protobuf)
    if state["playthrough"] != 2 or state["playthroughs_completed"] != 2 or state["op_choice"] != 0:
        raise RuntimeError("Expected a genuine UVHM/OP0 input after Gearbox expansion decoding")
    if baseline[2][0][1] != 1 or baseline[3][0][1] != 0:
        raise RuntimeError("Expected level 1, zero XP")
    if read_protobuf(baseline[13][0][1])[2][0][1] != 2:
        raise RuntimeError("Expected exactly two weapon slots")
    if len(baseline[18]) != 3 or read_protobuf(baseline[18][2][1]).get(3):
        raise RuntimeError("Expected empty UVHM mission records")

    WORK.mkdir(parents=True, exist_ok=True)
    index = dump_index()
    missions, mission_hash = get_dump("MissionDefinition", index)
    objectives, objective_hash = get_dump("MissionObjectiveDefinition", index)
    sets, set_hash = get_dump("MissionObjectiveSetDefinition", index)
    stations, station_hash = get_dump("FastTravelStationDefinition", index)
    assert scalar(stations[STATION], "StationLevelName") == "Sanctuary_P"
    station_id = saved_station()

    # Walk the actual definition dependencies, avoiding guessed/misnumbered episodes.
    chain = []
    def visit(path):
        if path in chain:
            return
        for dependency in references(missions[path], "Dependencies", "MissionDefinition"):
            visit(dependency)
        chain.append(path)
    visit(TARGET)
    if len(chain) != 6 or chain[0] != "GD_Episode01.M_Ep1_Champion":
        raise RuntimeError("Unexpected Plan B prerequisite chain")

    player = copy.deepcopy(baseline)
    records, audit = [], []
    for path in chain:
        block = missions[path]
        objective_paths = references(block, "ObjectiveDefs", "MissionObjectiveDefinition")
        objective_sets = references(block, "ObjectiveSetDefs", "MissionObjectiveSetDefinition")
        counts = [int(scalar(objectives[p], "ObjectiveCount")) for p in objective_paths]
        complete_sets = [i for i, p in enumerate(objective_sets)
                         if scalar(sets[p], "bCanCompleteMission") == "True"]
        if not complete_sets:
            raise RuntimeError(f"No completable objective set for {path}")
        active_set = complete_sets[-1]
        status = 3 if path == TARGET else 4
        # Gibbed MissionData field numbers; objective counts are packed int32 varints.
        record = {1: [[2, path.encode()]], 2: [[0, status]], 3: [[0, 0]], 4: [[0, 0]],
                  5: [[2, write_repeated_protobuf_value(counts, 0)]], 6: [[0, active_set]],
                  8: [[0, 0]], 9: [[0, 0]], 10: [[0, 1]], 11: [[0, 1]]}
        records.append([2, write_protobuf(record)])
        audit.append({"mission": path, "name": scalar(block, "MissionName"), "status": status,
                      "stage": 1, "objective_counts": counts, "active_set_index": active_set,
                      "active_set": objective_sets[active_set]})

    uvhm = read_protobuf(player[18][2][1])
    uvhm[2], uvhm[3] = [[2, TARGET.encode()]], records
    player[18][2] = [2, write_protobuf(uvhm)]
    player[16] = [[2, station_id.encode()]]
    player[17] = [[2, station_id.encode()]]
    appearance = read_protobuf(player[19][0][1])
    appearance[1] = [[2, NAME.encode()]]
    player[19] = [[2, write_protobuf(appearance)]]
    player[20] = [[0, SAVE_ID]]
    plot_number = int(scalar(missions[TARGET], "MissionNumber"))
    player[21], player[37] = [[0, plot_number]], [[0, plot_number]]
    guid = {i + 1: [[5, v]] for i, v in enumerate(struct.unpack("<4I", uuid.uuid4().bytes_le))}
    player[34] = [[2, write_protobuf(guid)]]

    changed = {key for key in baseline.keys() | player.keys() if baseline.get(key) != player.get(key)}
    if changed != {16, 17, 18, 19, 20, 21, 34, 37}:
        raise RuntimeError(f"Unexpected changed save fields: {changed}")
    assert player[18][:2] == baseline[18][:2]
    assert expansion_state(player, read_protobuf) == state
    output = app.wrap_player_data(write_protobuf(player))
    reread = read_protobuf(BaseApp.unwrap_player_data(output))
    assert reread == player
    assert reread[53] == baseline[53]  # Includes the exact special inventory serial bytes.
    assert source.read_bytes() == original

    manifest = {
        "scenario": "01 Plan B turn-in / third weapon slot", "version": "0.1.1",
        "game_verified": False, "character_name": NAME, "save_file": "Save7F01.sav",
        "save_id_decimal": SAVE_ID, "level": 1, "experience": 0, "weapon_slots": 2,
        "effective_expansion_state": state, "map": "Sanctuary_P", "travel_station": station_id,
        "travel_station_definition": STATION,
        "input_sha256": sha(original), "output_sha256": sha(output),
        "edited_protobuf_fields": sorted(changed), "missions": audit,
        "checks": {"input_unchanged": True, "unmodified_decoded_roundtrip_exact": True,
                   "edited_protobuf_roundtrip_exact": True, "sha1_and_crc_valid": True,
                   "inventory_and_expansion_records_byte_preserved": True,
                   "nvhm_tvhm_missions_byte_preserved": True, "xp_level_slots_preserved": True},
        "scope": "Synthetic checkpoint only; native reward pools and the SDK mod are not edited",
        "sources": {"editor": "https://github.com/loot-midget/borderlands2", "editor_commit": EDITOR_COMMIT,
                    "mission_schema": "https://github.com/gibbed/Gibbed.Borderlands2/blob/master/projects/Gibbed.Borderlands2.ProtoBufFormats/WillowTwoSave/MissionData.cs",
                    "expansion_schema": "https://github.com/gibbed/Gibbed.Borderlands2/blob/master/projects/Gibbed.Borderlands2.FileFormats/SaveExpansion.cs",
                    "travel_station_table": TRAVEL_TABLE_URL, "travel_station_table_sha256": TRAVEL_TABLE_HASH,
                    "datapack": DATAPACK, "dump_sha256": {"MissionDefinition": mission_hash,
                    "MissionObjectiveDefinition": objective_hash, "MissionObjectiveSetDefinition": set_hash,
                    "FastTravelStationDefinition": station_hash}},
        "limitations": ["Mission/world reconstruction needs first in-game validation",
                        "A full JSON/item re-encode was rejected because it rewrote special placeholder serials; raw protobuf editing preserves them",
                        "Candidate has synthetic story progress; it is not a campaign save"]}
    destination.mkdir(parents=True)
    (destination / "Save7F01.sav").write_bytes(output)
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (destination / "README.txt").write_bytes((Path(__file__).parent / "plan_b_instructions.txt").read_bytes())
    print(f"Built one candidate: {destination / 'Save7F01.sav'}")
    print("Checks passed: compression/integrity, raw protobuf, UVHM expansion records, untouched inventory and input.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "saves/Save0001.sav")
    parser.add_argument("--destination", type=Path, default=ROOT / "dist/TestSaves-0.1.1")
    args = parser.parse_args()
    build(args.source, args.destination)
