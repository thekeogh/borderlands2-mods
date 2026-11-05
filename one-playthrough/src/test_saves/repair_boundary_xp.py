#!/usr/bin/env python3
"""Release discovery-XP headroom, changing only XP in three existing saves."""
from __future__ import annotations

import copy
import json
import shutil
import tempfile
from pathlib import Path

import build_pack
import verify_pack


def repair():
    old = build_pack.ROOT / "dist/TestSaves-0.2.0"
    new = build_pack.DESTINATION
    if new.exists():
        raise RuntimeError("Refusing to overwrite a release")
    if (old.parent / (old.name + ".zip")).exists():
        raise RuntimeError("Previous release already archived")
    builder = build_pack.PackBuilder()
    scenarios = {s["number"]: s for s in json.loads(
        (build_pack.HERE / "scenarios.json").read_text())}
    manifest = json.loads((old / "manifest.json").read_text())
    revisions = []
    with tempfile.TemporaryDirectory(dir=build_pack.common.WORK, prefix="xp-repair-") as tmp:
        stage = Path(tmp) / new.name
        shutil.copytree(old, stage)
        for row in manifest["checkpoints"]:
            path = stage / "saves" / row["save_file"]
            before = path.read_bytes()
            assert build_pack.common.sha(before) == row["sha256"]
            config = scenarios[row["number"]]
            if not config.get("boundary"):
                assert path.read_bytes() == (old / "saves" / row["save_file"]).read_bytes()
                continue
            previous = builder.read(builder.unwrap(before))
            player = copy.deepcopy(previous)
            experience = builder.app.required_xp[config["boundary"] - 1] - config["xp_margin"]
            assert builder.app.required_xp[config["level"] - 1] <= experience
            player[3] = [[0, experience]]
            assert {k for k in player.keys() | previous.keys()
                    if player.get(k) != previous.get(k)} == {3}
            output = builder.app.wrap_player_data(builder.write(player))
            assert builder.read(builder.unwrap(output)) == player
            path.write_bytes(output)
            revisions.append({"test": row["number"], "file": row["save_file"],
                              "previous_sha256": row["sha256"],
                              "previous_experience": row["experience"],
                              "new_experience": experience, "xp_margin": config["xp_margin"],
                              "changed_protobuf_fields": [3]})
            row.update(experience=experience, xp_margin=config["xp_margin"],
                       steps=config["steps"], sha256=build_pack.common.sha(output))
        assert [r["test"] for r in revisions] == [5, 6, 7]
        manifest.update(version=build_pack.VERSION, revision={
            "previous_version": "0.2.0",
            "reason": "Test05 arrival/discovery XP immediately crossed the one-point level boundary",
            "changes": revisions,
            "other_eight_saves_byte_identical": True,
            "identity_missions_inventory_destinations_unchanged": True})
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        (stage / "README.md").write_text(build_pack.instructions(manifest["checkpoints"]))
        build_pack.DESTINATION = stage
        try:
            verify_pack.verify()
        finally:
            build_pack.DESTINATION = new
        build_pack.archive_previous()
        shutil.copytree(stage, new)
    print(f"Released {new}: replace only Save7F05/06/07.sav; XP-only changes verified.")


if __name__ == "__main__":
    repair()
