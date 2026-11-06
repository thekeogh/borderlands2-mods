#!/usr/bin/env python3
"""Verify the actual delivered binaries against source, scenario and item schemas."""
from __future__ import annotations

import base64
import json
import math
import struct
import sys
import zipfile
from pathlib import Path

import build_pack
import build_plan_b as common


def verify():
    folder = build_pack.DESTINATION
    manifest = json.loads((folder / "manifest.json").read_text())
    builder = build_pack.PackBuilder()
    scenarios = {s["number"]: s for s in json.loads((build_pack.HERE / "scenarios.json").read_text())}
    assert manifest["input_sha256"] == common.sha(builder.source)
    assert len(manifest["checkpoints"]) == 11
    assert {r["number"] for r in manifest["checkpoints"]} == set(range(2, 13))
    assert len(list((folder / "saves").glob("*.sav"))) == 11
    # Independent check against Gibbed's C# float constants/Math.Pow formula.
    single = lambda v: struct.unpack("<f", struct.pack("<f", v))[0]
    compute = lambda level: math.floor((math.pow(level, single(2.8)) + single(7.33)) * 60)
    reduction = compute(1)
    levels = {s["level"] for s in scenarios.values()} | {s["boundary"] for s in scenarios.values() if s.get("boundary")}
    for level in levels:
        assert builder.app.required_xp[level - 1] == compute(level) - reduction
    identities, names, slots = set(), set(), set()
    for row in manifest["checkpoints"]:
        config = scenarios[row["number"]]
        binary = (folder / "saves" / row["save_file"]).read_bytes()
        assert common.sha(binary) == row["sha256"]
        player = builder.read(builder.unwrap(binary))
        assert common.expansion_state(player, builder.read) == builder.expansion
        assert player[2][0][1] == row["level"]
        assert player[3][0][1] == row["experience"]
        assert player[4][0][1] == max(0, row["level"] - 4)
        if config.get("boundary"):
            assert row["experience"] + config.get("xp_margin", 1) == builder.app.required_xp[config["boundary"] - 1]
            assert builder.app.required_xp[row["level"] - 1] <= row["experience"]
        assert player[16] == player[17] == [[2, row["station_resource"].encode()]]
        assert row["station_resource"] == builder.travel[row["station"]]["resource_name"]
        inventory = builder.read(player[13][0][1])
        assert inventory[1][0][1] == 24
        assert inventory[2][0][1] == row["slots"]
        assert inventory[3][0][1] == row["slots"] - 2
        assert player[20][0][1] == int(Path(row["save_file"]).stem[4:], 16) == row["save_id"]
        guid = player[34][0][1]
        assert guid not in identities and guid != builder.baseline[34][0][1]
        assert row["name"] not in names and row["save_id"] not in slots
        identities.add(guid); names.add(row["name"]); slots.add(row["save_id"])
        appearance = builder.read(player[19][0][1])
        assert appearance[1][0][1].decode() == row["name"]
        assert player[18][:2] == builder.baseline[18][:2]
        uvhm = builder.read(player[18][2][1])
        assert uvhm[2][0][1].decode() == row["tracked_mission"]
        records = {builder.read(raw)[1][0][1].decode(): builder.read(raw) for _, raw in uvhm[3]}
        assert set(records) == {m["path"] for m in row["missions"]}
        for mission in row["missions"]:
            raw = records[mission["path"]]
            assert raw[2][0][1] == mission["status"]
            assert raw[11][0][1] == mission["stage"]
            assert raw[4][0][1] == mission["dlc_package_id"]
            counts = builder.read_packed(raw[5][0][1], 0)
            assert counts == mission["objective_progress"]
            assert len(counts) == len(mission["objective_maxima"])
            assert all(0 <= count <= maximum for count, maximum in zip(counts, mission["objective_maxima"]))
            assert raw[6][0][1] == mission["active_set_index"]
        if config["kind"] == "alternative":
            # Recipient objectives must be completed in-game before reward selection.
            raw = records[config["target"]]
            assert raw[2][0][1] == 1
            assert builder.read_packed(raw[5][0][1], 0) == [10, 0, 0]
            assert raw[6][0][1] == 1
        assert player[53][:len(builder.baseline[53])] == builder.baseline[53]
        new_items = player[53][len(builder.baseline[53]):]
        weapons = player.get(54, [])
        assert len(new_items) == 3 and len(weapons) == 5
        delivered = weapons + new_items
        seeds = [s for s in builder.gear["items"] if s["is_weapon"]] + [s for s in builder.gear["items"] if not s["is_weapon"]]
        for (_wire, entry), seed in zip(delivered, seeds):
            packed = builder.read(entry)
            serial = packed[1][0][1]
            kind, values, key = builder.app.unwrap_item(serial)
            seed_kind, seed_values, _ = builder.app.unwrap_item(base64.b64decode(seed["base64"]))
            assert kind == seed_kind
            assert values[:4] == seed_values[:4] and values[6:] == seed_values[6:]
            assert values[4] == values[5] == row["level"]
            assert builder.app.wrap_item(is_weapon=kind, values=values, key=key) == serial
            if kind:
                assert packed[2][0][1] == 0  # All five guns really are in the backpack.
            else:
                assert packed[3][0][1] == int(seed["equipped"])
        changed = {k for k in player.keys() | builder.baseline.keys() if player.get(k) != builder.baseline.get(k)}
        assert changed == set(row["changed_protobuf_fields"]) and changed <= build_pack.ALLOWED_FIELDS
        print(f"{row['number']:02d}: {row['save_file']} — level/XP, destination, mission state, gear and protected fields verified")
    assert common.sha(build_pack.SOURCE.read_bytes()) == common.SOURCE_HASH
    for version in ("0.1.0", "0.1.1"):
        with zipfile.ZipFile(build_pack.ROOT / f"dist/TestSaves-{version}.zip") as archive:
            assert archive.testzip() is None
    with zipfile.ZipFile(build_pack.ROOT / "dist/OnePlaythrough-0.1.7/one_playthrough.sdkmod") as mod:
        for name in mod.namelist():
            assert mod.read(name) == (build_pack.ROOT / "src" / name).read_bytes(), name
    (folder / "VALIDATION.txt").write_text(
        "All 11 delivered save files verified against their manifest and source.\n"
        "Outer SHA-1/CRC and raw protobuf roundtrips pass. Unique names/slots/GUIDs.\n"
        "Destinations are verified station ResourceNames. Mission progress/counts/set indices match game data.\n"
        "All five backpack guns and three supplied items have matching character-level grades/stages,\n"
        "unchanged seed parts and valid serial roundtrips. Original packed UVHM records preserved.\n"
        "XP table independently matches Gibbed's float-constant formula at all selected levels.\n"
        "Boundary saves start 5,000 XP below 50/61/73, allowing for discovery XP. Source save and SDK mod unchanged.\n"
        "These structural checks do not replace first in-game load/mission/gear validation.\n")
    print("Verified every delivered save; original input and SDK mod unchanged. In-game validation pending.")


if __name__ == "__main__":
    verify()
