# Build brief: UVHM from level 1 (we will call it One Playthrough)

## 1. Goal and scope

Build a Borderlands 2 PythonSDK mod for keogh that delivers this experience:

> Imagine Gearbox released vanilla Ultimate Vault Hunter Mode with its minimum scaling level lowered from 50 to 1. Keep the UVHM experience otherwise as native as possible, so one character can play the campaign and DLCs in a single continuous playthrough.

We will name the mod "One Playthrough".

Please refer to `../references/` for some other mods that do similar things, you may be able to get answers to some questions from them. Do not copy them, they is not what they are there for.

The level-50 restriction discussed here is a **minimum/scaling floor**, not the player's maximum level cap. Preserve the maximum character level supported by the installed game and DLCs. Reaching that maximum depends on the content played; do not promise that one campaign alone awards enough XP.

This is an implementation brief, not evidence that every part is already feasible. Investigate the remaining native restrictions before promising success.

### Firm requirements

- Borderlands 2, solo play, using the modern Willow2 PythonSDK/mod manager.
- Start with a genuine UVHM save whose character has been set to level 1.
- Preserve actual UVHM playthrough identity and native behaviour wherever possible.
- Scale UVHM from the character's actual level, including levels 1–49.
- No modification of `Borderlands2.exe`, hex-editing instructions or executable patch prerequisite.
- Deliver an installable `.sdkmod` and its maintainable source.
- Include F10 JSON diagnostics from the first playable prototype.
- No OP difficulty selector, custom Easy/Normal/Hard profiles or weighted enemy-level rolls.

Normal SDK installation and supported SDK hooks are acceptable. Prefer reflected runtime data edits and supported function hooks. Do not silently substitute a custom native byte patch, injected binary patcher or memory-patching workaround and describe the requirement as solved. If something beyond the normal SDK is required, explain the exact blocker and discuss it with the user.

Use the existing repository's naming if one is supplied. Otherwise, use **UVHM from level 1** as the working display name. The old prototype was called **AVHM (Absolute Vault Hunter Mode)**; retaining that name is optional, not a functional requirement.

## 2. Intended player experience

| Area | Required behaviour |
| --- | --- |
| Playthrough | Genuine UVHM, one ongoing campaign and DLC journey; no replaying Normal and TVHM to reach it |
| Player | Level 1 initially; normal XP, skill points, unlock progression and installed maximum character level |
| World and enemies | Native UVHM scaling relative to the player's actual level, without a forced minimum of 50 |
| Encounters | Native UVHM enemy rosters, variants, badass eligibility, spawn rules and boss behaviour |
| Enemy levels | Preserve native level variation and enemy/boss-specific differences; do not force every enemy to the player level |
| Combat | Preserve UVHM health, shields, damage, regeneration, slag rules, resistances and relevant skill interactions |
| Missions | Available offers follow native UVHM scaling from the player's current level; acceptance locks the mission level |
| Mission rewards | Equipment, XP and cash use that accepted mission level; completing the mission later must not upgrade it to the player's new level |
| Loot | Native UVHM generation and level variation around the relevant current game stage; equipment already owned stays unchanged |
| Economy | Native UVHM cash, prices, vendor stock and mission pay, evaluated at the appropriate corrected stages |
| Presentation | Mission offers, journal entries, difficulty descriptions, reward cards and fanfare agree with the actual mission level |

The user's shorthand was “more badass enemies etc.” The requirement is the **actual UVHM encounter rules**, not an invented universal increase in badass spawn chance. Establish what vanilla does and retain it.

The user accepts that true UVHM at level 1 may be punishing before skills and reliable slag are available. Do not quietly disable regeneration, weaken enemies, hand out skills or add an early-game difficulty ramp.

### Preserve native exceptions

“Everything scales” does not mean flatten every value. Keep native boss offsets, item variation, transformations, scripted mechanics and content-specific exceptions unless investigation proves a level-50 floor prevents the intended scaling.

Keep native item eligibility and rarity rules, including level-dependent loot unlocks. Do not make all endgame equipment available at level 1 or increase legendary rates. If an eligibility restriction must change to make the basic experience functional, document the evidence and discuss that specific exception.

Preserve normal weapon-slot and other character unlock behaviour. Check the supplied save for artificial unlocks rather than assuming an edited save represents a clean starting character.

## 3. Existing work and inputs

The user previously built AVHM around a genuine UVHM save with a level-1 character. They report that the gameplay worked reasonably well but required an executable patch. They remember mission cards showing **level 50 / impossible** at level 1 as a remaining issue. They believe this may have been presentation-only, but that has **not been verified**.

Three old files were supplied in the original conversation:

- `__init__(1).py`: the approximately 843-line AVHM Python implementation. The upload suffix is incidental; the mod's source entry point is `__init__.py`.
- `build.py`: a small `.sdkmod` packaging script.
- `pyproject.toml`: AVHM version 1.0.0 metadata, declaring BL2 and solo-only support and requiring an edited UVHM save.

Ask the user for these files if they have not been included with this brief. Do useful investigation and diagnostics work while other inputs are pending. No `.sav` file or exact executable patch was supplied with those three files. Do not claim to have inspected either.

### Old AVHM behaviour to remove

These are observations from its source, not endorsements of its implementation:

| Old code | Why it does not match the new brief |
| --- | --- |
| `PROFILES`, `scaling_opt`, `_profile()` | Offers NVHM/TVHM/UVHM multiplier profiles and defaults to TVHM tuning |
| `_apply_tuning()` | Replaces tuning values across balance entries with hand-written profile constants |
| `_kill_regen_effect()` and `_kill_regen_formulas()` | Always disable enemy health regeneration |
| `_apply_stages()` and `_scale_region()` | Flatten region bounds and remove boosts above the player; may erase native differences |
| `_scale_pawn_stage()` and `_scale_pawn_exp()` | Attempt to set enemies and vehicles to exactly the player level |
| `_scale_inventory()` | Attempts to force generated equipment to exactly the player level |
| `_reward_level()` | Returns `max(locked_level, player_level)`, upgrading rewards after acceptance |
| `_sync_missions()` | Infers locks using `min(saved_stage, player_level)`; this is not a safe general migration rule |
| `_override_ui_exp_level()` | Attempts to disguise UI difficulty by overriding player-level accessors during fanfare |

The new implementation should keep native balance values instead of copying the old profile table. The old comments labelling those values “vanilla” are not proof that they are correct or sufficient.

The old code reads or writes these candidate objects and paths:

- `GD_Playthrough3Tuning.Balance.BalanceMod_PT3`.
- `BalanceModifiers`, including `MinEffectiveLevel` and health/shield/damage fields.
- Regional `GameBalanceDefinition` objects, including `BalanceByRegion`, region bounds and mission overrides.
- The current player's `MissionPlaythroughs`, mission entries and `MissionDefinition` objects.

Treat these as investigation leads. A minimal change to a lower-level activation threshold may be appropriate, but prove which field controls which behaviour. Preserve higher-level tuning thresholds and formulas instead of overwriting the entire modifier table.

### Useful reference projects

- User's BL1 One Playthrough: <https://github.com/thekeogh/borderlands1e-mods/tree/main/one-playthrough>
- Its diagnostic implementation: <https://github.com/thekeogh/borderlands1e-mods/blob/main/one-playthrough/Source/sdk_mods/OnePlaythrough/diagnostics.py>
- Its mission persistence: <https://github.com/thekeogh/borderlands1e-mods/blob/main/one-playthrough/Source/sdk_mods/OnePlaythrough/storage.py>
- Enemy and Item Scaling: <https://github.com/CalebEaston/bl2-and-tps-enemy-and-item-scaling-sdk>
- Official SDK/mod manager: <https://github.com/bl-sdk/willow2-mod-manager>
- Official SDK installation: <https://bl-sdk.github.io/willow2-mod-db/>
- Older Level 1 UVHM project: <https://www.nexusmods.com/borderlands2/mods/56>

Read current source before reusing techniques. Follow applicable licences if copying code.

The BL1 project is a reference for the user's single-playthrough goal and diagnostic workflow. Do **not** port its weighted enemy difficulty table or loot-floor policy. Those requirements were explicitly dropped for this BL2 version.

Enemy and Item Scaling provides relevant hook and mission-record examples, but it does not activate the complete UVHM ruleset. Its accepted missions continue levelling, which is specifically unwanted here. The older Level 1 UVHM project uses executable patching and prepared saves; it is research material, not an acceptable installation dependency.

## 4. First milestone: prove the level-50 floor can be removed

Prefer using the game's genuine UVHM execution paths over recreating UVHM in Normal Mode. The edited save already supplies that playthrough identity. Do not change this architecture merely to make a superficial scaling demo easier.

Start with a small instrumented prototype:

1. Verify the current SDK API, supported hook signatures, reflected classes and functions against the target game build.
2. Load an unpatched game with a copied, level-1 UVHM save. Confirm that the current playthrough is genuinely UVHM, without changing the player's real XP level.
3. Capture a baseline F10 report around the first mission offer, acceptance, journal display and reward flow.
4. Trace where the mission/region/game stage first becomes 50: definitions, saved records, level queries, native calculation or UI payload generation.
5. Identify and apply the smallest SDK-level correction that makes the underlying values and presentation agree below level 50.
6. Verify the same path after a level-up, map transition, save-quit and reload.
7. Compare a normal level-50+ UVHM baseline with the mod enabled to establish that existing native behaviour remains intact.

Do not assume the apparent UI problem is cosmetic. A displayed stage of 50 may come from an underlying clamp that also affects XP, money, rewards, enemy levels or loot eligibility.

Conversely, do not rewrite all game stages just because one UI pathway is wrong. Fix the lowest responsible calculation or authoritative record and allow native consumers to use it.

Do not spoof the player's level, substitute 50 into general accessors, or merely remove “impossible” text. If a separate UI fix is still necessary after the authoritative level is correct, keep it narrow, mission-specific and evidenced by diagnostics.

**Feasibility gate:** if the floor is enforced inside a native path that cannot be reached through supported SDK hooks/data, report the exact function or calculation, attempted approaches and observed results. Deliver useful diagnostics and investigation notes; do not claim the requirement is solved or quietly fall back to executable patching.

## 5. Mission state and persistence

Use actual mission status to distinguish offers, accepted missions, ready-to-turn-in missions and completed missions.

- An unaccepted offer uses the corrected native UVHM level calculation.
- On acceptance, record the actual accepted stage in the authoritative per-character mission record.
- Accepted missions retain that stage across level-ups, travel and save/reload.
- The journal, difficulty rating, reward card, equipment reward, XP and cash must all agree with that stage.
- Include automatically assigned story missions, ECHO/cutscene assignments, alternative rewards and native repeatable missions.
- Do not identify a mission through a guessed “active mission” fallback when the event refers to a different mission.
- Do not lower legitimate previously accepted missions solely because the player is below their saved level.
- Handle a prepared save's genuine stale level-50 entries through an explicit, narrow migration decision supported by mission status and diagnostics. Never blindly clamp every saved mission to the current player level.
- Prefer the game's existing mission persistence if it works. If a sidecar is necessary, key it by stable character identity, playthrough and mission path; handle native mission resets so stale locks do not leak into a fresh run.
- Preserve unreadable persistence files and report errors. Write sidecar updates atomically.

Use copies of saves for testing. Do not modify save files directly unless that becomes an explicit, separately agreed part of preparing the starting save.

## 6. F10 diagnostics

This is a core feature, not a final polish task. The user successfully fixed many BL1 issues by pressing F10 at the moment something looked wrong and supplying the resulting JSON to an AI coding agent.

Implement a modern SDK keybind, default **F10**, that writes a new timestamped JSON report under the mod's SDK settings directory, for example `sdk_mods/settings/<mod-id>/diagnostics/`. Resolve the actual location through the supported SDK facilities; do not assume the current working directory.

Provide a short success notification and the output path in the log. Report export failures clearly. Capture useful partial output when optional reads fail. If a UI screen consumes F10 before the keybind receives it, diagnose that input path and provide a supported way to capture the same screen without closing it.

### Required report contents

| Section | Evidence to capture |
| --- | --- |
| Report identity | Schema version, UTC timestamp, mod version, known game/SDK versions, completion/partial flags and errors |
| Player and session | Actual player XP level, playthrough identifier, OP-related state if present, loaded map and relevant character identifier |
| Implementation state | Enabled state, registered hook status/hit counts, active corrections, original/current values and pending loads |
| Mission comparison | Mission path/name/status, definition stage, stored per-player stage, acceptance lock, region reference and relevant native query results |
| Mission UI | Current mission offer/journal/reward/fanfare context, displayed mission identity, level and difficulty payloads when accessible |
| Rewards | Relevant mission reward configuration, generated equipment levels and observable XP/cash reward data |
| Regional scaling | Relevant region bounds, formulas/attributes, mission overrides, native player-relative boosts and effective tuning thresholds |
| UVHM tuning | Relevant native balance entries, health/shield/damage values and regeneration configuration, with original/current differences |
| Nearby enemies | Bounded samples of actual enemy/vehicle levels, game stages, balance definitions, boss/badass identifiers and observable health/shields/regeneration |
| Equipment and economy | Bounded samples of visible/recent drops and vendor stock, equipment levels/stages, and observable cash/pricing inputs |
| Recent events | Bounded history of relevant level queries, mission accept/reward/UI events, spawns, map loads and corrections |

For the level-50 investigation, show the **same mission's values side by side**, rather than a large dump that obscures the discrepancy. Label raw/native values, corrected values and displayed values distinctly. Never label a value “native” if it was already read through an overriding hook without a verified bypass.

Only read verified, safe APIs. Some values may be inaccessible. Record that fact and the reason instead of inventing fields, guessing a value or representing missing evidence as zero.

### Export robustness

- Diagnostics must be observational: pressing F10 must not rescale actors, apply tuning, grant rewards, change mission state or force a save.
- Hook observers must preserve arguments, return values and event execution. Keep gameplay corrections separate from diagnostic collection.
- Use bounded collection sizes, recursion depth, string lengths and a fixed-size event ring buffer. Avoid unbounded per-frame logging or recursively walking the entire UObject graph.
- Store paths/class names and serialisable snapshots, not live Unreal objects in JSON or long-lived references to actors that can be destroyed during travel.
- Distinguish wrapped arrays from wrapped structs when reflecting fields; the BL1 diagnostic source contains an example of this pitfall.
- Handle unavailable objects, menu/loading states, stale references, property-read errors and non-finite floats safely.
- Write a small initial valid report before optional expensive reads; complete it through an atomic temporary-file replacement. Interrupted optional collection should leave useful evidence.
- Keep explicit `export_complete`, `partial`, truncation and error information. Missing data must not silently disappear.
- Avoid secrets, account identifiers and unnecessary personal filesystem paths. Do not dump the entire save or player inventory by default.

Supply a short testing guide explaining when to press F10 and which reports to return. Capture recent UI events so transient fanfare can be investigated even after the popup closes.

## 7. Implementation discipline

- Use modern `mods_base`/`unrealsdk` APIs supported by the installed SDK. Verify hook names and argument/return signatures against current documentation or reflection.
- The old AVHM contains many speculative property names and broad exception handlers. Do not carry them over blindly. Check registration success and whether each important hook actually fires.
- Investigate existing native calculations before introducing a replacement. Prefer the smallest change that removes the artificial lower bound while preserving native offsets and formulas.
- Preserve native behaviour at levels 50+ and across DLC-specific tuning thresholds.
- Keep the supported scope to UVHM. Normal and TVHM must not be altered accidentally. Treat a non-zero native OP selection as outside the first version's scope and report it clearly; do not silently reset saved OP progression.
- Guard against hook recursion, unloaded controllers, repeated application, stale references and map transitions.
- Snapshot values before mutating shared objects. Restore supported changes on disable, or explicitly require a game restart where safe reversal cannot be guaranteed.
- Keep gameplay, persistence and diagnostics in focused modules if useful. Avoid another monolithic collection of UI workarounds.
- Normal logging should be concise; detailed evidence belongs in diagnostics.
- Mark the first version solo-only. Do not claim multiplayer or TPS compatibility without implementing and testing it.
- Do not change executable files or add unrelated gameplay/QoL features.

## 8. Validation and acceptance

Offline tests can verify pure calculations, mission-lock state, serialisation and packaging. They cannot establish that a native hook fires or that gameplay matches UVHM. State clearly which checks were run in the actual game and which still require the user's testing.

| Scenario | Required result |
| --- | --- |
| Unpatched executable, level-1 UVHM save | Mod loads and genuine UVHM identity is verified |
| Available mission below level 50 | Correct player-relative offer level and difficulty presentation |
| Accept at level 3, level to 6 | Mission and its ordinary rewards remain based on the accepted level 3 |
| Automatically assigned story mission | Correct assignment level and persistence |
| Save/reload and travel | Mission locks remain consistent; no reappearance of the level-50 floor |
| Journal, offer, reward card and fanfare | Displayed level/difficulty agree with authoritative mission data |
| Ordinary enemies, badasses and bosses | Native UVHM rules and level offsets remain; enemies are not all flattened |
| Combat | Native UVHM tuning and regeneration are active below 50 |
| Drops, chests and vendors | Appropriate native stage/level variation; owned equipment is not re-levelled |
| Mission XP/cash and world economy | Appropriate stage is used; no accidental reward inflation or duplicated turn-ins |
| Different DLC areas | Relevant scaling rules work without blanket rewrites of all special cases |
| Levels around 49/50/51 and later tuning thresholds | No discontinuity caused by the mod; native later changes remain intact |
| Installed maximum level | Normal cap is honoured; no OP progression added |
| Level-50+ native UVHM comparison | Same rules, eligible content and tuning as an unmodified baseline |
| F10 during gameplay, mission UI and loading/menu states | Valid bounded report or a clear supported limitation, with no gameplay changes |
| Disable/restart or remove mod | No executable changes; documented handling of runtime and persisted state |

For random loot or encounters, compare rules, eligibility, stages and representative distributions. Do not require identical random outcomes from separate sessions.

If access to the game is unavailable, implement testable components and the diagnostic build, then give the user precise in-game steps. Do not claim a compile check or mocked test proves the level-50 issue fixed.

## 9. Deliverables and hand-off

When asked to implement this brief, produce:

1. Maintainable mod source and metadata.
2. An installable `.sdkmod`, with a verified archive layout and all required modules included. Packaging must fail clearly if required files are missing; the old builder only warns and skips them.
3. F10 diagnostics and a short capture/test guide.
4. Concise installation and starting-save instructions explaining which actual UVHM state is required. A supplied edited save is acceptable; automatic save generation and a normal New Game-to-UVHM workflow are not first-version requirements.
5. Investigation notes naming the responsible level-50 floor, chosen SDK correction and supporting evidence, or the unresolved blocker.
6. A validation report separating offline checks, observed in-game results and remaining user verification.

The public `README.md` should initially contain **only a title and a short description**. Put implementation details, diagnostic instructions and investigation notes in separate developer/test documents. Do not expand the public README unless the user asks.

Keep the work focused: preserve genuine vanilla UVHM, lower only the restrictions that prevent scaling from level 1, and use diagnostics to justify every additional change.
