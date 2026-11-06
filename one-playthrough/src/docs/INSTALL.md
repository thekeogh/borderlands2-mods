# One Playthrough 1.0.0 — keogh

Vanilla Ultimate Vault Hunter Mode from level 1. Solo Borderlands 2, genuine UVHM, OP0.

## Install or update

1. Fully close Borderlands 2.
2. Keep your working patched `Borderlands2.exe` installed. This mod does not patch the executable.
3. Replace the existing `one_playthrough.sdkmod` in `<game>/sdk_mods/` with this release. Remove duplicate installed copies; do not unzip the `.sdkmod`.
4. Enable **One Playthrough** in the Mods menu before loading your character. Check that the version is **1.0.0**.
5. Continue your existing UVHM character. Updating the mod does not require a save reset.

To start a new playthrough, use a genuine UVHM character prepared at level 1. Ordinary **New Game** still starts Normal mode. The mod does not convert saves, reset missions or unlock weapon slots automatically.

## Playing

The game controls enemy level variation, boss offsets, regeneration, combat, mission levels and rewards, loot, vendors, XP and the installed character-level cap. Already-owned equipment keeps its level. The SDK change is the same tested UVHM tuning activation threshold adjustment as 0.1.7; no new gameplay changes were introduced for 1.0.0.

**Known cosmetic issue:** the mission turn-in screen can show your character's level instead of the mission's accepted level. Tested mission records and rewards retain the accepted level. This display is deliberately left unchanged.

## Diagnostics

Press **F10** if an issue occurs. Reports are JSON files under the SDK settings directory, normally:

`<game>/sdk_mods/settings/one_playthrough/diagnostics/`

No console commands or automatic startup exports. **Capture next mission screen** and **Export JSON now** remain in mod options. See [Troubleshooting](TROUBLESHOOTING.md).

## Disable or remove

Disable the mod, then fully quit/restart the game to clear effects already applied to loaded actors. Disabling attempts to restore the threshold owned by the mod. The external executable patch remains installed separately.

Multiplayer, non-zero OP difficulty and TPS are outside this release's supported scope. See [Release notes](RELEASE_NOTES.md) for validation coverage.
