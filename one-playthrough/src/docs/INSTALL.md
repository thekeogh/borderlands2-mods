# One Playthrough 1.1.0 — keogh

Ultimate Vault Hunter Mode from level 1, with accepted missions following your level. Solo Borderlands 2, genuine UVHM, OP0.

## Install or update

1. Fully close Borderlands 2.
2. Keep your working patched `Borderlands2.exe` installed. This mod does not patch the executable.
3. Replace the existing `one_playthrough.sdkmod` in `<game>/sdk_mods/` with this release. Remove duplicate installed copies; do not unzip the `.sdkmod`.
4. Enable **One Playthrough** in the Mods menu before loading your character. Check that the version is **1.1.0**.
5. Continue your existing UVHM character. Updating the mod does not require a save reset.

To start a new playthrough, use a genuine UVHM character prepared at level 1. Ordinary **New Game** still starts Normal mode. The mod does not convert saves, reset missions or unlock weapon slots automatically.

## Playing

The game controls enemy level variation, boss offsets, regeneration, combat, loot, vendors and the installed character-level cap. Already-owned equipment keeps its level. Enemy scaling and the UVHM tuning module are unchanged from 1.0.0.

**Accepted missions now follow your level automatically, with no option.** Active and ready-to-turn-in missions are raised to at least your current level. A mission already above your level stays higher. Both its live definition and native saved record are updated; native reward generation uses the raised stage, including equipment, XP and cash subject to native exceptions. Completed missions are left alone.

This also applies to missions already accepted when you install 1.1.0. Raised stages persist when the game saves. Removing/downgrading the mod does not reconstruct original acceptance levels; keep a save copy if you want to return to the old policy.

A turn-in that levels you up keeps its in-flight reward stage stable while payment runs. Other unfinished missions can follow the new player level. Existing items and already-generated pending rewards are not rewritten.

**Presentation:** the turn-in screen still uses its native level display. It will usually agree when mission and player stages match; this feature does not patch the UI or guarantee agreement for higher-stage missions or a level-up during turn-in.

## Diagnostics

Press **F10** if an issue occurs. Reports are JSON files under the SDK settings directory, normally:

`<game>/sdk_mods/settings/one_playthrough/diagnostics/`

No console commands or automatic startup exports. **Capture next mission screen** and **Export JSON now** remain in mod options. See [Troubleshooting](TROUBLESHOOTING.md).

## Disable or remove

Disable the mod, then fully quit/restart the game to clear effects already applied to loaded actors. Disabling attempts to restore the threshold owned by the mod. The external executable patch remains installed separately.

Multiplayer, non-zero OP difficulty and TPS are outside this release's supported scope. See [Release notes](RELEASE_NOTES.md) for validation coverage.
