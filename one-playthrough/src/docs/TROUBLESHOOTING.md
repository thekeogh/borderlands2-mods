# Reporting a playthrough issue

Play normally; constant captures are unnecessary.

1. Press **F10** when something looks wrong, ideally while the affected enemy, item or screen is visible.
2. If useful, capture again after the action or after save-quit/reload.
3. Move those JSON files from `sdk_mods/settings/one_playthrough/diagnostics/` into this project's `logs/` folder. Use a separate issue folder to keep reports together.
4. Describe the character level, mission/map, expected behaviour and what happened. Mention other relevant enabled mods.

## Mission screens

If the screen consumes F10, open One Playthrough's options and press **Capture next mission screen** before opening that screen. It exports once on the next observed mission-card event. **Export JSON now** is another manual export option.

## Finding the report

A HUD message confirms a saved JSON when available. In menus or during loading, check **JSON export status / location** in mod options instead. Exports use the actual SDK settings directory, not the game's current working directory.

A report can be marked partial because optional values are unavailable or samples are bounded. This does not by itself mean gameplay or the JSON export failed. Report export failures with the message shown in the status option.

## Known level-label mismatch

The turn-in card may display the player's current level even when the journal and accepted mission level are lower. The tested equipment rewards retain the accepted stage. This cosmetic discrepancy is known; capture a report if the actual reward or saved mission level changes unexpectedly.

F10 observes current state and bounded recent events. It does not rescale actors, change mission state, grant rewards or force a game save. Reports include stages, tuning, nearby actors, sampled vendor/equipped gear and recent mission/reward/UI activity; they do not dump the full inventory or account identifiers.
