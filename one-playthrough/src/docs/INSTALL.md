# One Playthrough 0.1.7 — keogh

Solo BL2 early access: genuine UVHM from level 1, using native scaling and balance.
The opening encounters, enemy regeneration and a mission lock across level 1->2 have
in-game evidence. Later content and a complete campaign have not been validated.

1. Keep the verified patched executable installed as Borderlands2.exe. SHA-256:
   `8bbe6e31f3bf5c9f83f9943c7c643ad4a950388ee03e4f4d705f4f10e9c3f1eb`.
   The SDK mod does not apply or verify that external patch.
2. Fully quit. Replace one_playthrough.sdkmod under `<game>/sdk_mods/` with this release;
   remove older/duplicate installed copies. Do not unzip the SDK mod.
3. Enable One Playthrough before loading the tested genuine UVHM character (playthrough
   index 2, OP selection 0). Ordinary New Game still starts Normal mode.
4. Continue with your tested character; keep periodic copies of its save during early access.
   See TESTING.md for the remaining checks and how to report an issue.

The only SDK gameplay edit remains BalanceMod_PT3 BalanceModifiers[0].MinEffectiveLevel,
50->1. The tuning module is byte-identical to the tested 0.1.6 module. The game controls
native enemy levels/offsets, regeneration, combat values, loot, XP, mission locks and the
installed maximum level. No custom enemy/item scaling or additional balance profile is used.

0.1.7 removes the completed experiment options and excludes their modules from the SDK mod.
It removes 23 diagnostic hook targets (59->36), including general stage queries, pawn-stage
tracing, population tracing, inventory initialization and pickup callbacks. Tuning's own
load/spawn hooks remain unchanged. A bounded recent history of mission/reward, inventory,
currency, damage/death and UI events remains available for investigating problems.

No automatic startup JSON is produced. Press F10 when needed; or use Export JSON now.
Capture next mission screen exports once when the next mission card appears. No console
is used. Files go under the actual SDK settings directory:
`<game>/sdk_mods/settings/one_playthrough/diagnostics/`.
Move relevant JSONs to this project's logs folder. The mod never writes to project logs.
The status/location option reports export success/failure when HUD messages are unavailable.

F10 remains observational. Reports retain actual tuning values, player/mission stages,
nearby actor samples, equipped weapons, reward/UI history and explicit unavailable values.
The broad class/function discovery catalogue and irrelevant initializer internals are removed.
This reduces diagnostic work; frame-time impact of 0.1.7 has not been measured in-game.

The original prepared save contains a stale first-mission level-50 record. Its reward was
observed at level 1 in the initial session; its completed record later reloads as 50.
It is not automatically migrated. Continue with the tested character rather than assuming
any fresh edited save is clean. Weapon-slot SDU rewards in UVHM also remain unverified;
0.1.7 does not alter those reward conditions or unlock slots automatically.

Disable attempts to restore the owned threshold. Fully quit/restart afterward because
native effects already applied to actors may persist. The external EXE patch is separate
and stays installed. Normal-mode/TPS/multiplayer compatibility is not claimed.
