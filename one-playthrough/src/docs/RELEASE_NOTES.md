# One Playthrough 1.1.0

Author: **keogh**. Accepted missions now follow the player; no option or additional EXE patch.

## Mission policy

- Active, required-objectives-complete and ready-to-turn-in mission stages rise to at least the player's current level in UVHM/OP0.
- Higher mission stages are preserved. Completed missions are not rescaled.
- Writes update the mission definition and native saved mission record; stages persist through ordinary game saves/reloads, including after disabling this feature.
- Reconciles on enable, native level-up, loading, acceptance/status changes, mission cards and before reward completion.
- Native reward definitions, pools, recipient choices and item variation remain intact. Ordinary equipment/XP/cash generation sees the raised stage; already-owned or already-generated pending items are not rewritten.
- Reward payment is guarded against changing its mission stage halfway through a level-up caused by that payment.

Enemy/loot scaling, bosses, combat, regeneration and UVHM tuning are unchanged from 1.0.0. F10 remains observational and writes only JSON on request or explicitly armed mission-screen capture. No console logging or automatic startup export.

## Validation

Offline checks cover scope guards, record/definition agreement, completed/higher-stage preservation, recipient flags, payout level-up ordering, partial-write rollback, hook lifecycle and F10 read-only behavior. These checks do not prove real game hook behavior. Reuse the existing test saves as described in [Testing](TESTING.md); in-game 1.1.0 validation is pending.

The previous release's tests establish the unchanged scaling baseline. They established mission locking under the old policy and must not be presented as evidence for the new following policy. Synthetic save 12's recipient state was corrected in pack 0.2.2; use that corrected save.

## Prerequisites and presentation

Keep the working patched EXE and genuine UVHM save. Solo BL2, OP0. Ordinary New Game remains Normal mode.

The native turn-in level label is not patched. It should commonly agree now that the mission follows the player; higher mission stages and a turn-in level-up can still produce differences. Raised saved mission stages are not rolled back on disable/removal.
