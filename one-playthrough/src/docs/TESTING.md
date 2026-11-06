# 1.1.0 — missions follow your level

Keep the patched EXE; fully close the game and replace the installed `.sdkmod` with 1.1.0. Enable before loading. Use fresh copies of the same prepared saves from `dist/TestSaves-0.2.2/saves/`. Do not use the older incorrectly prepared save 12.

The save files need no edits. Their older build-time manifest still describes the original stored stages; 1.1.0 should raise those stages when loaded. Close the game before re-copying a test save. No completed tests need repeating beyond the focused checks below. Test 10 remains skipped.

## First batch: 02 and 12

| Test | Original saved mission | Player | New expected mission stage | Action |
| --- | --- | --- | --- | --- |
| 02 — Save7F02.sav | Cleaning up the Berg: 5 | 10 | 10 | Turn in to Hammerlock; collect shield |
| 12 — Save7F0C.sav | Rakkaholics Anonymous: 20 | 25 | 25 | Complete handover to Mordecai; expect Sloth route |

For each:

1. Load and wait for HUD; F10. Check the journal mission level.
2. Arm **Capture next mission screen** before opening the reward card. Note displayed mission/reward levels, XP and cash.
3. Collect reward; F10 promptly. Expect native item variation around the raised mission stage; report exact observed level rather than assuming every item equals it.
4. Save-quit/reload; F10. Mission should retain the raised stage. Existing kit should retain its original level.
5. Upload JSONs to `logs/02` or `logs/12`. Captured mod version separates the new batch from earlier reports.

## Weapon-slot safeguard: 03

Re-copy Save7F03.sav. Player20, original mission16; expect mission20 on load. Capture the Bright Lights turn-in, collect and F10, then reload/F10. Check that the native fourth-slot SDU is still awarded. Mission-stage-dependent reward conditions are a reason to test this explicitly; do not insert an SDU if a different reward appears.

## Level-up and reload: 05

Re-copy Save7F05.sav. F10 at49 after arrival XP. Kill nearby XP enemies until50; F10. Hunting the Firehawk should now rise from49 to50. The original kit must remain49. Save-quit/reload; F10. Keep OP0.

06 and07 can repeat the same check at60→61 and72→73 if useful after the first batch. No need to repeat DLC introductions or the level80 baseline immediately unless a concrete issue appears.

F10 should include `implementation.mission_scaling` with scope UVHM/OP0, registered hooks and recent stage changes. It must not itself apply the change. If a mission never rises, capture before doing more and report the test number. These are candidate expectations pending in-game verification.
