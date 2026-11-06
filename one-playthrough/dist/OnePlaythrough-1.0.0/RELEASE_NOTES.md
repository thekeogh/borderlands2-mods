# One Playthrough 1.0.0

Author: **keogh**. First stable release, following in-game testing of 0.1.7.

## Changes from 0.1.7

- Version and public descriptions updated for release.
- F10 JSON, manual export and one-shot mission-screen capture retained.
- Removed the repeated attempt to reflect the SDK-unsupported `ResourcePoolMap` property during F10 collection. Supported pool/value samples remain.
- Release includes install and troubleshooting guides; historical investigation and test records remain in the source workspace.

The gameplay tuning module and observer hooks are unchanged from tested 0.1.7. Experiments, discovery dumps and automatic startup exports remain excluded. Files are written only on a manual export or an explicitly armed mission-screen capture; recent diagnostic history is bounded in memory.

## In-game evidence

The preceding build was tested for low-level UVHM and regeneration; accepted mission/reward stages across level changes and reloads; native third/fourth weapon-slot SDUs; enemies, vendors and loot observations; level boundaries 49→50, 60→61 and 72→73; Scarlett and Tina DLC introductions; level 80 at OP0; and the corrected Mordecai/Sloth reward checkpoint.

These were focused tests, not a full campaign or a controlled comparison of every combat multiplier. The optional DLC boss checkpoint was skipped at the user's request. Synthetic DLC saves initially spawned in Windshear; normal fast travel allowed the DLC tests to proceed. An incorrectly prepared recipient-choice test save was corrected without changing runtime reward logic.

## Known issue and prerequisites

The turn-in card can show player level instead of accepted mission level. Tested mission data and rewards remain correct; no presentation workaround was added.

Keep the working patched executable and use a genuine UVHM save. The SDK mod does not apply or verify the EXE patch. The user's verified patched EXE SHA-256 is:

`8bbe6e31f3bf5c9f83f9943c7c643ad4a950388ee03e4f4d705f4f10e9c3f1eb`

Normal New Game remains Normal mode. Solo BL2/OP0 only.
