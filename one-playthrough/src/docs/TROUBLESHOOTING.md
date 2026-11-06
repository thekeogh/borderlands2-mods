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

## Mission-stage reports

F10 includes `implementation.mission_scaling`: scope, hook registration, errors, recent before/after stage changes and any in-flight reward transaction. Saved records and mission definitions remain side by side in the mission comparison.

In 1.1.0, unfinished missions should rise with your level and persist on reload. Completed missions and already-owned gear should stay unchanged. A mission that is already higher than you remains higher. Existing pending reward items are not regenerated.

The turn-in label still follows the game's own UI query. A remaining mismatch does not by itself establish that the actual reward stage is wrong; capture both the screen and the collected reward if unsure.

F10 observes current state and bounded recent events. It does not rescale actors, change mission state, grant rewards or force a game save. Reports include stages, tuning, nearby actors, sampled vendor/equipped gear and recent mission/reward/UI activity; they do not dump the full inventory or account identifiers.
