#!/usr/bin/env python3
"""Keep test12 active until the player chooses a recipient in-game."""
from __future__ import annotations

import copy
import json
import shutil
import tempfile
from pathlib import Path

import build_pack
import verify_pack


def revised_readme(previous, records):
    """Preserve the user's completed-test strikeouts and removed spoiler section."""
    generated = build_pack.instructions(records)
    marker = "## Test 12: OP 12 Alt Reward"
    footer = "## Validation and references"
    section = generated.split(marker, 1)[1].split(footer, 1)[0]
    text = previous.split(marker, 1)[0] + marker + section + footer + previous.split(footer, 1)[1]
    text = text.replace("# One Playthrough — test saves 0.2.1",
                        "# One Playthrough — test saves " + build_pack.VERSION, 1)
    revision = generated.split("**Revision 0.2.2:**", 1)[1].split("**Earlier revision", 1)[0]
    text = text.replace("\n\n", "\n\n**Revision 0.2.2:**" + revision, 1)
    text = text.replace("replace only those three saves; the others are byte-identical.",
                        "replace 05/06/07 and the corrected 12.")
    return text


def repair():
    old = build_pack.ROOT / "dist/TestSaves-0.2.1"
    new = build_pack.DESTINATION
    if new.exists() or (old.parent / (old.name + ".zip")).exists():
        raise RuntimeError("Refusing to overwrite release/archive")
    builder = build_pack.PackBuilder()
    manifest = json.loads((old / "manifest.json").read_text())
    config = next(s for s in json.loads((build_pack.HERE / "scenarios.json").read_text())
                  if s["number"] == 12)
    row = next(r for r in manifest["checkpoints"] if r["number"] == 12)
    original = (old / "saves" / row["save_file"]).read_bytes()
    assert build_pack.common.sha(original) == row["sha256"]
    previous = builder.read(builder.unwrap(original))
    player = copy.deepcopy(previous)
    pt = builder.read(player[18][2][1])
    changes = 0
    for entry in pt[3]:
        mission = builder.read(entry[1])
        if mission[1][0][1].decode() != config["target"]:
            continue
        before = copy.deepcopy(mission)
        assert mission[2][0][1] == 3
        assert builder.read_packed(mission[5][0][1], 0) == [10, 0, 0]
        assert mission[6][0][1] == 1 and mission[11][0][1] == 20
        mission[2] = [[0, 1]]
        assert {k for k in mission if mission[k] != before[k]} == {2}
        entry[1] = builder.write(mission)
        changes += 1
    assert changes == 1
    player[18][2] = [2, builder.write(pt)]
    assert {k for k in player if player[k] != previous[k]} == {18}
    output = builder.app.wrap_player_data(builder.write(player))
    assert builder.read(builder.unwrap(output)) == player
    old_hash = row["sha256"]
    row.update(sha256=build_pack.common.sha(output), steps=config["steps"])
    next(m for m in row["missions"] if m["path"] == config["target"])["status"] = 1
    manifest.update(version=build_pack.VERSION, revision={
        "previous_version": "0.2.1", "test": 12,
        "reason": "Ready status with neither recipient objective complete is a suspect synthetic state; Mordecai interaction selected alternative Rubi",
        "previous_sha256": old_hash, "changed_save_field": 18,
        "nested_change": "UVHM Rakkaholics mission status 3 (ready) -> 1 (active)",
        "missions_gear_levels_identity_other_than_status_unchanged": True,
        "other_ten_saves_byte_identical": True,
        "in_game_validation": "pending"})
    with tempfile.TemporaryDirectory(dir=build_pack.common.WORK, prefix="recipient-repair-") as tmp:
        stage = Path(tmp) / new.name
        shutil.copytree(old, stage)
        (stage / "saves" / row["save_file"]).write_bytes(output)
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        (stage / "README.md").write_text(revised_readme(
            (old / "README.md").read_text(), manifest["checkpoints"]))
        build_pack.DESTINATION = stage
        try:
            verify_pack.verify()
        finally:
            build_pack.DESTINATION = new
        for r in manifest["checkpoints"]:
            if r["number"] != 12:
                assert (stage / "saves" / r["save_file"]).read_bytes() == (
                    old / "saves" / r["save_file"]).read_bytes()
        build_pack.archive_previous()
        shutil.copytree(stage, new)
    print(f"Released {new}: replace only Save7F0C.sav; recipient-state game test pending.")


if __name__ == "__main__":
    repair()
