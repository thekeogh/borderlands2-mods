## Changelog

### Enemy and Item Scaling v0.10
- Enemy vehicles now follow the enemy bounds: bandit technicals, sandskiffs, turrets, fan boats
  and the Pre-Sequel's scav buggies. To the game they are vehicles rather than enemies (buzzards
  are enemies), built by a spawn path of their own that the mod wasn't watching, so they kept
  their vanilla level while their crew scaled (reported on Nexus: level-50 technicals and
  sandskiffs next to a level-24 player with the enemy cap on). Vehicles you take from a Catch-A-Ride are left to the game,
  which levels them to you. A vehicle's drops come at the vehicle's level: the item bounds don't
  reach them.

### Enemy and Item Scaling v0.9
- `On-Level Vendors` now only raises vending machines. A machine below your level still stocks
  at your level; one above your level (a DLC area you are early for, say) keeps its own level,
  the same as without the mod. Pulling a machine far below its area's level could leave it with
  little or nothing to sell, which is what happened in Commander Lilith & the Fight for
  Sanctuary.
- If a mission is turned in again after a turn-in that never completed it (it stays in the list
  and can pay its XP and cash again), the log now says so with a "please report this" line, as
  long as both turn-ins happen on the same map visit (the record starts over at every load).
  This happened with Dr. T and the Vault Hunters, No Vacancy and In Memoriam alongside Reward
  Reroller; the cause is still being tracked down and does not appear to be this mod.
- With `Log Adjustments` on, the log now also shows the mod's settings at each map load, what a
  vending machine has for sale when you open it, each mission turn-in and when it completes,
  and the keys pressed on a mission's reward page. These only report.

### Enemy and Item Scaling v0.8
- `On-Level Mission Rewards` is now `Minimum Mission Level`, a bound like the other four
  (`Vanilla`, `Player Level`, `Within 1` to `Within 10 Levels`): accepted missions below it are
  raised to it. Set it again after updating; the old on/off setting is not carried over.
- The mod now says where it runs: Borderlands 2 and The Pre-Sequel, the latter untested so far.

### Enemy and Item Scaling v0.7
- `On-Level Mission Rewards` now raises the missions themselves instead of patching their
  rewards. An accepted mission is raised to your level (never lowered) when you accept it,
  whenever you level up and whenever a map loads, and that level is written into your
  character's mission record, so the mission log, the XP, the cash and the reward all agree,
  survive a save-quit and stay even if you turn the option off. A mission that levels you up as
  you turn it in can give its reward one level below your new level. The reward item is no
  longer rewritten as you take it; if a reward ever comes out below the level it was rolled
  at, a "please report this" line is logged instead.

### Enemy and Item Scaling v0.6
- Added Borderlands: The Pre-Sequel support. The mod can now be enabled there (earlier versions
  declared themselves Borderlands 2 only, so the mod manager locked them), and the player level
  no longer reads the Overpower field that only Borderlands 2 has. Every hook target was checked
  against The Pre-Sequel's classes; the SHiFT machine in Concordia counts as a vending machine.
  Not yet play-tested there, so reports from The Pre-Sequel are especially welcome.
- Chests in Mercenary Day's map (`Xmas_P`) and The Pre-Sequel's intro (`MoonShotIntro_P`) are no
  longer lowered by `Maximum Item Level`: at least one of them spawns nothing when lowered.

### Enemy and Item Scaling v0.5
- Fixed enemies keeping their old level (nameplate and health) while only their drops were
  scaled. The level is now set where the game builds the enemy, so its displayed level, health
  and drops all move together. An enemy that gets raised or lowered drops loot at its new level;
  the item settings still apply on top of that.
- `On-Level Mission Rewards` now also writes the level into your character's own record of the
  mission right before the reward is rolled, and re-levels a reward item as you take it if the
  roll somehow ignored the level. That last case always prints a "please report this" line in
  the console and log.

### Enemy and Item Scaling v0.4
- `On-Level Mission Rewards` now levels the mission as soon as its reward card is shown, and
  keeps it there until you take the reward. That makes it work with Reward Reroller (its rolls
  and rerolls come out on level); the v0.3 attempt did not reach legacy mods.

### Enemy and Item Scaling v0.3
- Attempted Reward Reroller support (did not work; superseded by v0.4).

### Enemy and Item Scaling v0.2
- Added `On-Level Mission Rewards`: mission reward items, and the XP and cash with them, are
  generated at your level.
- Added `On-Level Vendors`: vending machines stock at your level when they spawn and when they
  restock. Vendors are no longer touched by the item bounds.

### Enemy and Item Scaling v0.1
- Initial skeleton: four level bounds (minimum/maximum enemy level, minimum/maximum item level),
  each either vanilla or within 0-10 levels of the player, plus a console logging toggle.
