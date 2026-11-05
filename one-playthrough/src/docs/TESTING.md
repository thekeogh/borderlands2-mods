# 0.1.7 — ongoing playthrough

This is a smaller diagnostic build with the same gameplay module as 0.1.6. Install with
the game fully closed, keep the patched EXE, and enable before loading your existing tested
UVHM/OP0 character. No save reset is needed. Check the version in Mods.

First load after updating: press F10 once. The report should show threshold current=1,
original=50, state=active and no tuning errors. Automatic startup exports are removed.
This confirms the cleanup's package/input wiring in the actual game.

Then play normally. The following remain useful checks rather than reasons to farm:

- Cleaning up the Berg is accepted at stage 2 and has a configured shield reward. Arm
  Capture next mission screen before turn-in; note the displayed mission and shield levels.
  Collect the shield and press F10 promptly. If already past it, use a later item reward.
- Save-quit/reload, then F10 to check accepted/completed stages persist. Capture newly
  spawned enemies after entering a new area; native exceptions/offsets remain allowed.
- At Plan B and Bright Lights, Flying City, check whether the still-locked weapon slot
  receives its normal SDU. Current code does not add or replace these rewards.
- Later DLC, level-50+ tuning, alternate/repeatable rewards and full UI agreement remain
  unverified. Report concrete mismatches as they occur.

If something seems wrong: F10 at the moment, then again after the relevant action if useful.
If a mission card consumes F10, use Capture next mission screen beforehand. Provide the
mission/map name, actual player level, expected behaviour and what you saw. Copy the new
JSONs to logs after archiving the preceding batch. No console or constant captures needed.

Use periodic save copies while testing a proper playthrough. Existing evidence confirms
initial low-level scaling, visible regeneration, Blindsided's accepted stage remaining 1
through a player 1->2 level-up/completion, and subsequent mission acceptance at stage 2.
It does not establish full-game correctness or a numeric per-pawn regen rate.

The stale completed My First Gun record remains stage 50 and is not migrated. Avoid
resetting the prepared save as part of ordinary testing. Disable followed by a full game
restart is required to clear existing native actor effects. Ordinary New Game stays Normal.
