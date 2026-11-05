#!/usr/bin/env python3
"""Revise the first candidate by changing only save fields 16/17; archive it."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import zipfile
from pathlib import Path

import build_plan_b as builder


def repair():
    old = builder.ROOT / "dist/TestSaves-0.1.0"
    new = builder.ROOT / "dist/TestSaves-0.1.1"
    archive = old.parent / (old.name + ".zip")
    if new.exists() or archive.exists():
        raise RuntimeError("Refusing to overwrite a test-save release or archive")
    original = (old / "Save7F01.sav").read_bytes()
    manifest = json.loads((old / "manifest.json").read_text())
    if builder.sha(original) != "abda0d3cbb26ef4e5bd200d57fb875b0827c89f26e2d7010e7e3378508a66237":
        raise RuntimeError("Previous candidate differs from the file actually tested")
    sys.path.insert(0, str(builder.EDITOR))
    from borderlands.bl2 import AppBL2
    from borderlands.savefile import BaseApp
    from borderlands.datautil.protobuf import read_protobuf, write_protobuf

    old_player = read_protobuf(BaseApp.unwrap_player_data(original))
    player = copy.deepcopy(old_player)
    station_id = builder.saved_station()
    for field in (16, 17):
        if player[field] != [[2, builder.STATION.encode()]]:
            raise RuntimeError("Previous candidate has an unexpected travel field")
        player[field] = [[2, station_id.encode()]]
    changes = {k for k in player if player[k] != old_player[k]}
    assert changes == {16, 17}
    assert builder.expansion_state(player, read_protobuf) == manifest["effective_expansion_state"]
    output = AppBL2([str(old / "Save7F01.sav")]).wrap_player_data(write_protobuf(player))
    assert read_protobuf(BaseApp.unwrap_player_data(output)) == player
    assert builder.sha((builder.ROOT / "saves/Save0001.sav").read_bytes()) == manifest["input_sha256"]

    manifest.update(version="0.1.1", output_sha256=builder.sha(output),
                    travel_station=station_id, travel_station_definition=builder.STATION)
    manifest["revision"] = {
        "previous_output_sha256": builder.sha(original),
        "changed_fields_from_0_1_0": [16, 17],
        "from": builder.STATION, "to": station_id,
        "previous_game_result": "Invalid travel ID: missing-DLC message, fallback to Windshear Waste",
        "reason": "Gibbed saves station.ResourceName; candidate 0.1.0 wrote ResourcePath",
        "guid_name_missions_inventory_unchanged": True}
    manifest["checks"]["saved_destination_matches_gibbed_resource_name"] = True
    manifest["sources"].update(travel_station_table=builder.TRAVEL_TABLE_URL,
                               travel_station_table_sha256=builder.TRAVEL_TABLE_HASH,
                               fast_travel_writer="https://github.com/gibbed/Gibbed.Borderlands2/blob/master/projects/Gibbed.Borderlands2.SaveEdit/Tabs/FastTravelViewModel.cs")

    with tempfile.TemporaryDirectory(dir=builder.WORK, prefix="test-save-release-") as temporary:
        stage = Path(temporary)
        (stage / "Save7F01.sav").write_bytes(output)
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        (stage / "README.txt").write_bytes((Path(__file__).parent / "plan_b_instructions.txt").read_bytes())
        assert read_protobuf(BaseApp.unwrap_player_data((stage / "Save7F01.sav").read_bytes())) == player
        old_files = sorted(p for p in old.iterdir() if p.is_file())
        temp_archive = stage / archive.name
        with zipfile.ZipFile(temp_archive, "w", zipfile.ZIP_DEFLATED) as z:
            for p in old_files:
                z.write(p, old.name + "/" + p.name)
        with zipfile.ZipFile(temp_archive) as z:
            assert z.testzip() is None
            for p in old_files:
                assert z.read(old.name + "/" + p.name) == p.read_bytes()
        new.mkdir()
        for name in ("Save7F01.sav", "manifest.json", "README.txt"):
            (new / name).write_bytes((stage / name).read_bytes())
        archive.write_bytes(temp_archive.read_bytes())
        for p in old_files:
            p.unlink()
        old.rmdir()
    print(f"Corrected candidate: {new / 'Save7F01.sav'}")
    print("Verified: only protobuf destination fields 16/17 changed; original candidate archived.")


if __name__ == "__main__":
    repair()
