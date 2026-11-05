# One Playthrough — test saves 0.2.1

**11 new checkpoints · Keep One Playthrough 0.1.7 and your patched EXE.**

**Revision 0.2.1:** boundary saves **05, 06 and 07** now start **5,000 XP below** the next level to allow for arrival/discovery XP. If you installed 0.2.0, replace only those three saves; the others are byte-identical. No earlier tests need repeating.

Original `saves/Save0001.sav` is untouched. These are synthetic test characters with unique names/IDs. The already-passed Plan B save 01 is not repeated.

## Start here

1. **Fully close the game.** Copy only the `.sav` files from [saves](saves/) beside your Windows character saves. Do not overwrite an unrelated character if a filename collides.
2. Select the **OP test character by name**, choosing **UVHM** if prompted.
3. Start with **02 → 03 → 04**. Then try **08 / 09 / 10 / 12**, followed by **05 / 06 / 07 / 11**.

You can report a partial batch; no need to finish all eleven at once.

> **Filename numbering is hexadecimal:** `Save7F0A.sav` = test **10**, `Save7F0B.sav` = **11**, `Save7F0C.sav` = **12**. In-game character names use ordinary test numbers.

## Every test

1. Wait for the HUD after loading; press **F10 before the test**.
2. Follow that character's steps below; press **F10 after the relevant action/reward**.
3. Where requested, **save-quit → reload → F10**.
4. Move the exported JSONs into `logs/`, optionally grouped as `logs/02/`, `logs/03/`, etc. Report the test number, what happened, reward/item/enemy levels and anything odd.

> **Broken checkpoint?** If the spawn, mission, NPC or door is wrong, press **F10 and stop that character's test**. No need to replay missing story or keep attempting it.

## Gear and survival

All supplied gear matches the character's starting level.

| Gear | Location / use |
| --- | --- |
| Double Penetrating Unkempt Harold | Backpack; equip for damage |
| Grog Nozzle | Backpack; equip for slag/healing |
| Shock Norfleet + fire Norfleet | Backpack; optional heavy weapons |
| Infinity | Backpack; spare gun |
| The Sham + Magic Missile ×4 | Initially equipped |
| Grounded The Bee | Backpack; spare shield |

- **Equip Harold and Grog before fighting.** Fire launchers from a safe distance to avoid your own blast damage.
- You have generous ammo, **24 backpack spaces** and **$10,000**.
- Normal level-earned skill points are unspent; allocate them if useful. No extra skill points or OP unlocks.
- Spend some ammo before testing ammo pickups; initially stocked pools may be full.
- Do not sell the kit, count it as a random drop or expect owned gear to level with you.

The kit is stronger than normal progression, but does not grant invincibility. Native enemy scaling and the mod are untouched; this is not a vanilla combat-balance benchmark.

## Mission rewards

**Arm “Capture next mission screen” before opening a turn-in card.** Note the visible mission level and reward item level, collect, then press **F10 promptly**.

Native item variation is allowed: a locked mission stage does not guarantee all equipment matches that stage exactly.

**Redo a test:** fully quit and re-copy only that test's `.sav`. This resets that test character.

## Checkpoint overview

| Test | Character | Player level | Save file |
| --- | --- | --- | --- |
| 02 | OP 02 Shield Lock | 10 | [Save7F02.sav](saves/Save7F02.sav) |
| 03 | OP 03 Fourth Slot | 20 | [Save7F03.sav](saves/Save7F03.sav) |
| 04 | OP 04 World L10 | 10 | [Save7F04.sav](saves/Save7F04.sav) |
| 05 | OP 05 Level 49-50 | 49 | [Save7F05.sav](saves/Save7F05.sav) |
| 06 | OP 06 Level 60-61 | 60 | [Save7F06.sav](saves/Save7F06.sav) |
| 07 | OP 07 Level 72-73 | 72 | [Save7F07.sav](saves/Save7F07.sav) |
| 08 | OP 08 Oasis L10 | 10 | [Save7F08.sav](saves/Save7F08.sav) |
| 09 | OP 09 Tina L10 | 10 | [Save7F09.sav](saves/Save7F09.sav) |
| 10 | OP 10 Snowflake L20 | 20 | [Save7F0A.sav](saves/Save7F0A.sav) |
| 11 | OP 11 Level 80 Cap | 80 | [Save7F0B.sav](saves/Save7F0B.sav) |
| 12 | OP 12 Alt Reward | 25 | [Save7F0C.sav](saves/Save7F0C.sav) |

## Test 02: OP 02 Shield Lock

**Locked equipment reward: mission accepted at 5, player now 10**

**Player:** 10 · **Mission stage:** 5 · **Weapon slots:** 2

**Save:** `Save7F02.sav` · **Destination ID:** `SouthernShelfTown`

1. **F10** after loading; mission should be ready to turn in at level 5, player 10.
2. Arm **Capture next mission screen**; turn in Cleaning up the Berg to Hammerlock. Note mission level, shield level, XP and cash.
3. Collect the shield, **F10** immediately; save-quit/reload, **F10**. The accepted stage should remain 5; native item variation is allowed.

## Test 03: OP 03 Fourth Slot

**Fourth weapon-slot reward in low-level UVHM**

**Player:** 20 · **Mission stage:** 16 · **Weapon slots:** 3

**Save:** `Save7F03.sav` · **Destination ID:** `Sanctuary`

1. **F10** after loading; player 20, Bright Lights Flying City ready at 16, three weapon slots.
2. Arm mission capture; follow the turn-in marker to Roland. Record SDU versus class mod/other reward.
3. Collect reward, **F10**; check slot four, then save-quit/reload and **F10**. A different native reward is a finding; do not insert an SDU manually.

## Test 04: OP 04 World L10

**Native enemy variation, dropped gear, vendors, ammo and money**

**Player:** 10 · **Mission stage:** 10 · **Weapon slots:** 3

**Save:** `Save7F04.sav` · **Destination ID:** `IceEast`

1. Equip the provided gear, then **F10** before fighting near Three Horns Divide fast travel. Note enemy names/levels.
2. Kill a few nearby enemies; collect money/ammo and one dropped item, open a nearby chest if convenient; **F10**.
3. Check nearby weapon/ammo/medical vendors and their item levels/prices. **F10** while the menu is open if possible; otherwise just after closing.
4. Save-quit/reload, **F10**. No need to travel far or finish Hunting the Firehawk.

## Test 05: OP 05 Level 49-50

**Cross the former level-50 floor**

**Player:** 49 · **Mission stage:** 49 · **Weapon slots:** 3

**Save:** `Save7F05.sav` · **Destination ID:** `IceEast`

1. **F10** at level 49 after arrival/discovery XP finishes. The save starts 5,000 XP below level 50; report if arrival alone still levels you up.
2. Kill nearby XP-awarding bullymongs/enemies until you reach 50; several kills may be needed. **F10** immediately after the level-up.
3. Owned test gear should stay level 49. Capture a fresh drop or vendor item, then save-quit/reload and **F10** with newly spawned enemies.
4. Hunting the Firehawk was accepted at 49; its saved stage should stay 49 after levelling/reload. No need to complete it.

## Test 06: OP 06 Level 60-61

**Native tuning boundary at level 61**

**Player:** 60 · **Mission stage:** 60 · **Weapon slots:** 3

**Save:** `Save7F06.sav` · **Destination ID:** `IceEast`

1. **F10** at level 60 after arrival/discovery XP finishes. The save starts 5,000 XP below level 61; report if arrival alone still levels you up.
2. Kill nearby XP-awarding bullymongs/enemies until you reach 61; several kills may be needed. **F10** immediately after the level-up.
3. Save-quit/reload, **F10** near fresh enemies; accepted mission and owned kit should remain level 60. No mission turn-in needed.

## Test 07: OP 07 Level 72-73

**Native tuning boundary at level 73, OP selection remains zero**

**Player:** 72 · **Mission stage:** 72 · **Weapon slots:** 3

**Save:** `Save7F07.sav` · **Destination ID:** `IceEast`

1. **F10** at level 72 after arrival/discovery XP finishes. The save starts 5,000 XP below level 73; report if arrival alone still levels you up.
2. Kill nearby XP-awarding bullymongs/enemies until you reach 73; several kills may be needed. **F10** immediately after the level-up.
3. Save-quit/reload, **F10** near fresh enemies; accepted mission and owned kit should remain level 72. Do not select OP difficulty.

## Test 08: OP 08 Oasis L10

**Scarlett DLC arrival, automatic mission acceptance and enemy/loot scaling below 50**

**Player:** 10 · **Mission stage:** 10 · **Weapon slots:** 3

**Save:** `Save7F08.sav` · **Destination ID:** `OasisTown`

1. Let the arrival scene finish, then **F10** in Oasis. Record which local mission appeared and its displayed level.
2. Equip the kit; fight only the nearby opening enemies, record their levels and collect a drop; **F10**.
3. Save-quit/reload, **F10**. No need to play through the DLC or finish its first mission.

## Test 09: OP 09 Tina L10

**Tina DLC arrival and scaling below its normal starting range**

**Player:** 10 · **Mission stage:** 10 · **Weapon slots:** 3

**Save:** `Save7F09.sav` · **Destination ID:** `Docks`

1. Let the arrival story/cutscene finish, then **F10** in Unassuming Docks. Record the local mission and its displayed level.
2. Equip the kit; sample the first nearby enemies and a drop/chest, **F10**.
3. Save-quit/reload, **F10**. Stop if a scripted gate blocks the route; no need to complete the DLC introduction.

## Test 10: OP 10 Snowflake L20

**Short DLC boss encounter and native boss offsets**

**Player:** 20 · **Mission stage:** 20 · **Weapon slots:** 3

**Save:** `Save7F0A.sav` · **Destination ID:** `Xmas`

1. Equip the kit; **F10** after loading Marcus Mercenary Shop. The local mission is prepared at Summon Snowman.
2. Follow its marker to the bell/arena and summon Tinder Snowflake; **F10** with the living boss visible, before firing the strongest guns.
3. Use slag/healing and the provided heavy weapons to kill him; take a loot sample, **F10**. Fire launcher is provided as an option.
4. Do not slog through earlier objectives if the checkpoint fails to restore them: **F10** and report the displayed objective instead.

## Test 11: OP 11 Level 80 Cap

**Installed maximum-level baseline with OP zero**

**Player:** 80 · **Mission stage:** 80 · **Weapon slots:** 3

**Save:** `Save7F0B.sav` · **Destination ID:** `IceEast`

1. **F10** at 80; keep OP selection zero.
2. Equip the kit; kill a few nearby enemies, collect a drop and inspect vendor levels. **F10**.
3. Save-quit/reload, **F10**. No promise that every native enemy/item equals 80; preserve native exceptions.

## Test 12: OP 12 Alt Reward

**Alternative weapon reward and accepted stage lower than the player**

**Player:** 25 · **Mission stage:** 20 · **Weapon slots:** 4

**Save:** `Save7F0C.sav` · **Destination ID:** `Sanctuary`

1. **F10** in Sanctuary. Rakkaholics Anonymous is prepared for turn-in at 20; player is 25.
2. Pick Moxxi (Rubi) OR Mordecai (Sloth). Arm mission capture before opening the reward card. Tell us which recipient you chose and the displayed weapon level.
3. Collect reward and **F10**; save-quit/reload, **F10**. Accepted stage should remain 20; native item variation is allowed.
4. Optional: fully close game and re-copy this test file to try the other recipient. If neither offers a turn-in, **F10** and report; do not replay the prerequisite story.

## Validation and references

Each binary passes SHA-1/CRC, raw-protobuf and rescaled-gear serial roundtrips. UVHM expansion records and the original save are preserved. Travel IDs use Gibbed's verified ResourceName strings; mission objectives and package IDs use game-data dumps.

**These new checkpoints and gift gear still need your first in-game test.** The earlier Plan B checkpoint validates the approach, not every NPC, door, DLC or scripted state here.

No EXE, mod, enemy definitions, loot pools or native reward definitions were edited.

[Full setup and sources](manifest.json) · [Validation details](VALIDATION.txt) · [Optional checklist](CHECKLIST.csv) · [Item-code attribution](ITEM-CODES-LICENSE.txt)
