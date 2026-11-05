# Feasibility investigation — 0.1.5

## Established from source, not in-game observation

- The older supplied `Level 1 UVHM/ReadMe.txt` requires an executable edit and prepared saves.
  Its listed byte sequence changes an immediate comparison constant from hexadecimal `32`
  (decimal 50) to `01`. This supports a native comparison hypothesis; **it does not identify
  the owning function, authoritative stage calculation, or prove all affected paths**.
  No executable was supplied, opened, patched or searched. No prepared save was parsed.
- The supplied AVHM source replaces balance multipliers, disables regeneration, flattens
  stages and raises rewards after acceptance. None of that implementation was carried over.
- The modern Enemy and Item Scaling reference identifies useful factory and mission record
  paths, and explicitly levels accepted missions. Its policy is unsuitable here. References
  were read for investigation; no reference mod code was copied.
- A first `MinEffectiveLevel` tuning threshold is a separate investigation lead. Changing it
  alone is not evidence that mission, region or native world-stage floors are removed.

## Verified SDK surface

Inspected official source and stubs on 2026-11-04:

- [mods_base](https://github.com/bl-sdk/mods_base): `SETTINGS_DIR`, `build_mod`, `ButtonOption`,
  modern `keybind`, BL2 game mask, solo incompatibility metadata and enable/disable callbacks.
- [Willow2 manager stubs](https://github.com/bl-sdk/willow2-mod-manager/tree/master/stubs):
  `find_class`, `find_object`, iterator `find_all(exact=False)`, `_properties`, `_find`,
  `_find_prop`, `WrappedStruct._type`, distinct `WrappedArray`, SDK hook registration/status/removal.
- [Willow keybinds](https://github.com/bl-sdk/willow_keybinds/blob/master/__init__.py): keybinds
  dispatch from a PRE observer on `WillowGame.WillowUIInteraction:InputKey`.
- [UI utilities](https://github.com/bl-sdk/willow2-mod-manager/blob/master/src/ui_utils/hud_message.py):
  supported HUD notifications. In-game notification delivery remains untested.

Specific game functions from old mods are **candidates**, not verified game-build facts.
At runtime the prototype reflects each target's existence and parameters before adding an
observer; it records registration status and hit counts. A registered hook with zero hits
does not establish coverage. Unavailable classes/functions are reported and retried on
known reflected spawn/loading-complete lifecycle events. Collection itself does not retry
registration, load packages or execute candidate stage queries.

## Implemented evidence

Bounded PRE/POST observations around accept/complete/status events; POST observations of
reflected stage queries/setters, spawning, UI and rewards. No hook changes arguments,
return values or execution. Queries are labelled **observed SDK pipeline returns**, because
other mods can override them. No value is labelled an unmodified native return.

Mission comparisons join events and saved records by the exact mission object path. They
show definition stage, saved stage/status and existing lock flag together. No guessed
active-mission fallback, migration, acceptance correction or sidecar persistence is present.
Current screens and recent UI payloads are captured where accessible. Displayed Flash text,
effective resource pool regeneration and final XP/cash payment may remain inaccessible.

Bounded loaded-object samples cover regions, UVHM balance entries, nearby enemies/vehicles,
equipment generation and vendor stock. Bounds and truncation are explicit. Runtime UObject
references are not retained in history. Reports are checkpointed and atomically replaced;
failure in optional reads leaves partial evidence. Account IDs and full inventory/save dumps
are excluded; a controller-local save ID is hashed if that reflected field is available.

## Evidence received 2026-11-05

All 11 supplied 0.1.0 JSON files were read without modification. All exports completed.
Runtime versions: Python 3.14.6; mods_base 1.12; unrealsdk v3.2.0 (`b1852aa4`).

- Every report confirms playthrough index 2 and selected OP 0.
- `103412` reports **My First Gun** active, stored/definition stage 50, character level 1.
- `103534` reports the same mission ready to turn in (status 3), still level 50/character 1.
- `103635` reports that mission complete (status 4), **Blindsided** active at stage 50,
  and character level 10. No exact XP payout was captured. The timing supports a level-50
  reward inflation hypothesis; it does not prove the precise XP formula or exclude other XP.
- `103907` and `103915` capture actual spawned pawns at ExpLevel 50.
- The saved StartOfGame region entry remains stage 1 **for playthrough 0**. It cannot be
  treated as evidence that the UVHM regional stage was 1.
- Base UVHM modifier thresholds are 50, 61, 73. Other level-cap/OP-specific modifier arrays
  also exist, so the active native table cannot be inferred from the base array alone.

## Corrected diagnostic defects

All 50 reflected hooks had zero hits. They were registered as, for example,
`WillowGame:WillowPlayerController:AcceptMission` instead of
`WillowGame.WillowPlayerController:AcceptMission`. The SDK reported those string
registrations as present even though no matching function executed. The code had split an
already-colon-qualified UFunction `_path_name()` on its final dot.

Version 0.1.1 constructs each hook name from **the reflected function's actual Outer path
and Name**, preserving inherited owners such as `Engine.WillowInventory`. Regression tests
use the colon-shaped names evidenced by the logs and dispatch to the literal correct path.
Registration is now explicitly distinguished from observed hits in the report.
This bug also prevented the armed capture from firing. A completion screen was a valid
thing to try; its being a completion screen does not explain away the registration failure.

Additional evidence fixes: discover real mission movie/provider classes; read MStatus-named
struct arguments and returned mission data; preserve mission states at PRE/POST calls;
retain lifecycle events against query churn; prioritize stage/balance fields over the first
32 reflected properties; omit internal VfTable pointer noise; exclude non-world templates
from live actor samples; and separately capture deeper tuning tables and relevant region rows.
All changes remain observational; none edits a save, executable, stage or gameplay tuning.

## Gate and next action

**Responsible floor: unresolved. SDK correction: none chosen. Gameplay success: unproven.**
No game runtime is available in this workspace. User-supplied captures establish the
0.1.0 observations above, but malformed hooks leave the native stage-query sequence unknown.
No gameplay correction has been tried in-game; a hard native blocker cannot yet be claimed.

Collect the corrected observer's gameplay/journal reports on the existing test character
(or an untouched level-1 copy if already available). No further turn-ins or combat required.
Identify the first observed transition to 50 for the same mission. Determine whether a
supported authoritative query, reflected bound or saved record explains it. Only then add
the smallest correction and test low-level UVHM, acceptance locks, and 50+ behaviour.
If the responsible native calculation is unhookable, document its exact evidence and discuss
that blocker with keogh. No executable or memory patch fallback is authorized or included.

## Reset-save activity capture — 0.1.5

Keogh has reset the test save and will repeat the opening through the first bullymongs.
The supplied Enemy and Item Scaling reference also identifies QuestAcceptGFxMovie.SetRewardCard,
QuestAcceptGFxMovie.extCompleteConfirmed and WillowPlayerController.ServerGrantMissionRewards.
These are now explicit reflected observation candidates. No reference implementation was copied.
The earlier class-discovery filter looked only for mission/reward in class names, which could
miss QuestAcceptGFxMovie. Discovery now also includes quest, inventory and status-menu names.

PRE/POST resource snapshots accompany reflected XP/currency/ammo, pickup/inventory, reward,
damage and death functions. They contain declared argument values and existing reflected
player fields, without invoking evaluators/setters or calculating an assumed payout.
Dedicated histories retain the last 32 economy/pickup and 24 combat events against query churn.
F10 includes current player resource fields, equipped weapons only, UI-selected object samples,
and combat history. Every capture remains bounded, JSON-only and read-only.

Explicit mission arguments/return data take precedence over UI object fields. UI MissionList
is not used as a guessed selected mission. Health/ammo pools may still expose handles instead
of useful numeric values; missing counters remain unavailable. No scaling correction yet.

## Second captured session and next probe — 0.1.5

Read all 12 supplied 0.1.2 JSONs, without modification. These replace the older batch in
logs/; earlier findings above describe the prior session, not files currently present.
Relevant evidence:

- `105823`: level 1, My First Gun already locked at stored/definition stage 50.
- `110157` (`armed_mission_screen`): actual QuestAcceptGFxMovie.SetRewardCard event,
  mission ready to turn in; GetExpectedGameStage returns 50. Armed capture is verified.
- QuestAccept/StatusMenu reward setters receive `XPText="39108 XP"` and `Credits=2601`.
- `110234`: ReceiveWeaponReward PRE/POST shows the starter Dahl pistol's GameStage and
  ManufacturerGradeIndex both 50. The later player snapshot is level 10.
- GetRegionGameStage fired, but retained history lost those initial events. Loading movie
  notifications with bShowMovie=False cleared context at the end of startup. This is fixed:
  context clears on an actual show/start or main-menu event, not on movie closure.
- Separate cap/OP-named balance arrays are map-specific enemy modifier lists (MapName and
  AIPawnBalanceModifiers), not extra MinEffectiveLevel threshold tables. Earlier caution
  about additional threshold-table selection should not be read as a confirmed game fact.

Heavy capture was self-inflicted: the broad pickup-name pattern hooked polling, mesh,
physics, visibility and pickupability queries, then took repeated player/resource snapshots.
The new allowlist retains specific transactions and mission/stage events. Callbacks use
cached parameter names and at most 80 serialized value nodes; throttling happens before
reflection or player reads. No per-frame timers or global call logging are used. Full
resources, actor samples and class metadata remain on explicit export only. Each retained
event is stored once in the JSON event_table, referenced elsewhere by sequence. A small
initial checkpoint and one final atomic replacement avoid repeated full-file rewrites.

The responsible floor remains unresolved. The native controller's region/mission accessors
had zero observed hits while lower region query and mission definition paths did fire.
Zero hits do not prove an unhookable native path. The new separate scaling probe evaluates
only getter signatures already captured from this exact game build. It compares:

- Stored mission stage, definition GetGameStage/GetExpectedGameStage, and PC GetLevelForMission.
- PC GetGameStageFromRegion versus region GetDefaultRegionGameStage and GetRegionGameStage
  with both values of bDefaultGameStage. Out values are named explicitly and valid only if
  the function's return value reports success.
- Read-only mission XP/currency evaluation and installed player-level cap.

Parameter flags and output ordering are checked before each call. The SDK's BoundFunction
contract returns `(return_value, out1, out2, ...)` for out-parameter functions; the hook's
return argument alone contains the actual return, not all output values. Official sources:
https://github.com/bl-sdk/willow2-mod-manager/blob/master/stubs/unrealsdk/unreal/_bound_function.pyi
and https://github.com/bl-sdk/pyunrealsdk/blob/master/src/pyunrealsdk/hook.cpp .
Direct SDK hooks are bypassed for the probe calls, while nested native calls may still
invoke other mods. Results are not claimed to be unmodified native values. No setters,
stage overrides, reward grants, generated loot, save calls or binary workarounds are used.
Ordinary F10 remains observational and never invokes the explicit probe.

## Focused query results — 0.1.3 session

Read the five JSONs at logs/ root as the current session. logs/archive/ is previous-session
material; it is not mixed into current-session conclusions. No input files were moved or edited.

The 111908 report is the initial valid checkpoint (`export_complete=false`, sections empty),
consistent with the user's reported failure before final commit. It contains no PermissionError
or Windows code, so antivirus, indexing, an open reader and ACL problems are hypotheses only.
Later F10 and the 112016 scaling probe completed. Recovery in 0.1.4 records exception type,
errno, winerror and phase, retries a locked replacement within 350 ms, and tries a fresh
recovery filename if necessary. It preserves the existing checkpoint.

At player level 10 / UVHM 2 / OP 0, the 112016 probe returns:

| Query | Result |
| --- | --- |
| Installed character maximum | 80 |
| Default StartOfGame bounds | min 1, max 2, boost 0 |
| GetRegionGameStage current/default | success, stage 50, awesome 1 |
| Controller GetGameStageFromRegion | -1 (no corresponding stored UVHM stage; not level -1) |
| Mission GetGameStage / GetExpectedGameStage | 50 / 50 |
| Controller GetLevelForMission | Glacial_P (map name, despite the misleading name) |
| My First Gun XP/cash evaluation | 39108 / 2601 |
| Blindsided XP/cash evaluation | 29331 / 2601 |

This places the discrepancy between default region bounds and the native computed region
stage, rather than a cosmetic mission label. It does not expose the exact internal clamp
instruction or prove it is unhookable. The normal Python hook return is the function's bool;
GameStage/AwesomeLevel are separate out parameters. Documented hook args are copies and
post-hooks cannot replace the executed return. Returning a tuple of stage/awesome as the bool
return would be an invalid workaround. No raw-memory access or custom binary interception
is introduced. Official SDK hook contract:
https://github.com/bl-sdk/unrealsdk/blob/master/src/unrealsdk/hook_manager.h .

The brief identifies the first tuning MinEffectiveLevel as a possible lower activation gate.
An explicit, temporary experiment in 0.1.4 tests that narrow lead. It requires the exact
observed [50,61,73] threshold layout and a genuine loaded UVHM/OP0 mission region; snapshots
the first modifier; temporarily sets only its MinEffectiveLevel to 1; runs identical queries;
and restores 50 in finally before another query. It checks later thresholds and the captured
modifier snapshot after restoration. No rewards, actor rescaling, saves or permanent changes
are applied. Ordinary F10 and ordinary scaling probe never run the experiment.

Restart after this explicit test because hidden native caches are not established. A failed
field restoration is reported immediately as requiring restart. If the region result stays
50 while the first threshold is 1, that field alone is insufficient to remove this native
floor. Do not respond by changing all balance tables or forcing every enemy to player level.
A remaining native/data route or precise SDK limitation must then be investigated/reported.

## Temporary-threshold results — 0.1.5 session

Current-session files reviewed: startup `113533`, experiment `113702`, experiment `113733`.
Both experiment JSONs completed without export/collector errors. They agree:

| Measurement | Baseline | Threshold temporarily 1 | After restoration |
| --- | --- | --- | --- |
| First tuning MinEffectiveLevel | 50 | 1 | 50 |
| StartOfGame current/default region stage | 50 / 50 | 50 / 50 | 50 / 50 |
| My First Gun / Blindsided definition stages | 50 / 50 | 50 / 50 | 50 / 50 |
| My First Gun evaluated XP | 39108 | 25811 | 39108 |
| Blindsided evaluated XP | 29331 | 19358 | 29331 |
| Evaluated ordinary cash reward, each mission | 2601 | 2601 | 2601 |

Both report restored=true, tuning_snapshot_matches_after_restore=true and
later_thresholds_unchanged=true. The player is level 10. XP evaluation during the test is
consistent with the captured native XPGainedFromQuestsMultiplier of approximately 0.66
becoming eligible below level 50. These getter evaluations do not grant XP or money.

Conclusion: changing the first tuning activation threshold alone did not remove the
observed region floor in this already-loaded session. It demonstrably affected native
reward evaluation, so it is not simply an ineffective/unexecuted data write. This does not
prove that every possible native cache or initialization-time dependency is excluded, or
that the native floor is unhookable. The next investigation must concern the computed
region stage and its supported override/data paths; repeating this identical threshold
test adds no evidence. Do not claim a gameplay fix or replace the floor with independent
pawn/item/reward clamps.

The user did not see a HUD save notification while activating the options, but the two
complete, error-free files establish successful export. The HUD helper can be unavailable
or obscured during menus; do not interpret absent HUD feedback as a failed export. The
mod-menu export status remains the alternative confirmation. No new build was needed to
interpret this session, and the input JSONs were not modified.

## Supported override investigation — 0.1.5

Independent source research found no published implementation body for BL2's native clamp.
The older generated bindings at
https://github.com/RobChiocchio/BL2-SDK/blob/master/bl2-sdk/WillowGame_classes.h
and its GearboxFramework_classes.h confirm the hierarchy WillowRegionDefinition →
RegionDefinition. They expose generated dispatch wrappers, not native algorithm bodies.
They add no proof about a current game's internal clamp, or whether an explicitly bound
superclass wrapper would bypass internal C++ virtual dispatch. No wrapper code, offsets,
address tables, flag modifications or injection techniques were copied into this mod.

The current game's own JSON already reflects SetGameStageOverride(NewGameStageOverride:int),
flags 140288 (0x22400), and no reflected region-stage override getter/backing property.
Flags suggest a possible static scope, but flags/old headers alone are insufficient to
claim a per-region or global effect. In particular, later-engine flag documentation is
not proof of every UE3/Gearbox flag meaning. The experiment measures scope instead.

The standard PythonSDK hook contract allows replacing a function's bool return but does
not expose output-parameter replacement through its copied args. That does not itself
prove all SDK data routes impossible. The supported native setter is the remaining concrete
lead identified in reflection; it has not yet been tested in-game.

The separate region_override experiment:

1. Requires a current UVHM character, OP0, actual level 1–49 and a verified mission region.
2. Verifies the setter's owning class, exact IntProperty/flags signature and function flags
   against the runtime values supplied in keogh's reports; refuses unexpected metadata.
3. Snapshots current/default query outputs and reflected fields for the mission region and
   up to two other already-loaded opening-area regions. A first region not currently at
   the measured floor of 50 prevents the setter call.
4. Calls SetGameStageOverride once with actual XP level, using the ordinary SDK bound call.
5. Records the same outputs afterward, including which sampled regions changed. No assumed
   scope, guessed native reset (-1/0/etc), restoration of an unknown value, actor/mission/item
   re-leveling, rewards, save call, native bytecode changes or binary patches are used.
6. Requires immediate process quit/restart, even if the setter raises after changing state.
   The mod blocks further data experiments in this process and reports the pending override
   state. Only process restart is claimed as cleanup; disabling is insufficient evidence.

A below-50 query result would establish a supported native override route for that query,
not a complete vanilla-UVHM scaling solution. Scope, native offsets/boosts, enemy factories,
mission locking, UI and all loot/economy consumers still require evidence. A setter that
leaves the query at 50 would rule out this tested use of the override in the loaded session;
it would strengthen, but not universally prove, a native SDK feasibility blocker.

## Native override result and investigation boundary — 0.1.5 session

Current-session reports: startup 115259 and region_override_experiment 115336. Both exports
completed without errors. The experiment's native SetGameStageOverride(10) call returned
normally. The current/default query outputs remained stage 50, awesome 1 for all three
sampled regions: StartOfGame, Waterfront_A, Waterfront_A2. Default bounds remained respectively
1–2, 3–5, 4–5. No sampled current output changed; target_returned_requested_stage=false.

This rules out the tested use of the native override as a sufficient floor correction in
this session. It does not establish its scope, prove it was a no-op internally, identify
where an override might be ignored/reclamped, or prove every SDK route impossible. The
original private override remains unreadable and no guessed restoration was attempted;
the prescribed full process quit/restart remains required.

Evidence boundary now reached:

- The first tuning activation threshold can affect XP evaluation but does not change the
  measured region floor during the tested loaded session.
- The public native region-stage override setter returns normally but does not change the
  measured floor in any sampled region.
- The native WillowGame.WillowRegionDefinition:GetRegionGameStage entry point produces the
  stage-50 discrepancy after ordinary default-bound queries return low-level bounds.
- Its primary return is bool. Actual stage/awesome values are out parameters. The documented
  Python hook contract permits return overrides but its args are copies; it provides no
  documented direct replacement of these output parameters. A bool-return override would
  not supply a corrected stage.
- No native implementation body has been inspected. Generated C++ bindings only dispatch
  functions; they do not locate the responsible clamp instruction or additional native
  caches/data inputs. Hooking independent pawn/item/mission consumers would not establish
  preserved vanilla UVHM semantics.

Next useful input is a read-only copy of the exact tested game's
Binaries/Win32/Borderlands2.exe, placed under references/. Native implementation analysis
may locate the clamp and any reflected data/function inputs upstream of it. This is an
analysis input, not a proposed executable patch, executable edit, custom native interceptor,
memory-writing workaround or installation prerequisite. Do not infer a binary patch is
necessary merely because the tested data routes failed. A supported SDK route may still
exist, but none is currently demonstrated. No additional gameplay replay is requested.

The last export also showed native UObject housekeeping fields in the broad region-field
snapshot (hash/linker/object identifiers). They supplied no usable override getter or stage
control. They are not permission to use raw addresses or write hidden fields. Future capture
should omit this housekeeping noise rather than treat it as a gameplay API.

## Executable analysis completed — 2026-11-05

The exact supplied Borderlands2.exe was analyzed read-only. Native registration strings,
class construction, vtable dispatch and instruction checks establish the native UVHM region
path and an unnamed helper that directly returns literal 50 for a calculated stage below 50.
The override setter writes a native global; the identified UVHM path does not consult it.
An explicit superclass getter binding would reuse the same native wrapper/vtable dispatch.
The input SHA-256 was checked unchanged after analysis.

Full current result and feasibility boundary: NATIVE_FINDINGS.md. Reproducible analyzer and
bounded JSON/disassembly: src/research/. No gameplay fix, native interception, binary edit,
patch recipe or additional experiment build was produced. Original normal-SDK-only gameplay
design is blocked on this native calculation; broader intervention requires discussion.
No more repetitions of the existing in-game experiments are requested.


## Patched EXE session — 2026-11-05 12:47–12:52 UTC

Reviewed all eight new root logs (0.1.5), including startup and armed mission capture.
All export_complete=true with no top-level collector/export errors. Partial flags reflect
explicit unavailable optional data; they do not indicate failed JSON writes.

The user explicitly approved external EXE patching after the native analysis. Their
Borderlands2_Patched.exe is byte-identical to the previously supplied Borderlands2 2.exe:
SHA-256 8bbe6e31f3bf5c9f83f9943c7c643ad4a950388ee03e4f4d705f4f10e9c3f1eb.
Relative to the root original, only three bytes differ: B4C156 32->01, B4C15A 32->01,
CAF942 7E->EB. The first two match the proposed floor correction. The third changes a HUD
level display branch. No local binary was modified or executed during verification.

All seven gameplay captures confirm actual player level 1, playthrough 2, OP 0.
The last two sample three Glacial_P AI pawns with GameStage=1 and ExpLevel=1. A separate
Glacial_Dynamic pawn is level/stage 0; it must not be treated as a failed hostile clamp.
The starter pistol is observed equipped at stage/level 1; reward payloads also carry stage 1.
Native mission definitions for My First Gun and Blindsided are both 1. My First Gun's stored
record is already 50 at the first gameplay capture and stays 50 through completion.
Blindsided's newly accepted record is 1. No cross-level mission-lock test is present.
UI reward events show 71 XP/10 credits for My First Gun and 53 XP/10 credits for Blindsided;
these are displayed payloads, not proof of actual paid deltas. No probe was run this batch.

BalanceModifiers still has thresholds [50,61,73]. Its original regen effect references the
native initializer with constant/scale 1; the formula snapshot includes only ValueFormula
(bEnabled=false). Earlier unpatched batches have the same ValueFormula fields. This is
insufficient to establish whether another mod disabled the actual regen calculation.
The observer does not evaluate the effective enemy regen attribute. The user reports no
visible regen and has a disabled regen-suppression mod; its identity and disable timing
are not yet known. Do not blame that mod or assert regen is fixed.

Prior controlled threshold experiments prove that lowering only the first threshold
activates the native 0.66 quest XP multiplier below 50. Combined with the external native
floor patch, this is the next narrow correction: 0.1.6 activates that original entry from
1 while preserving every other field and later entries. This is not a replacement balance
profile. Independent PRE/POST load/spawn hooks retry after assets load. F10 never applies
this correction. Runtime ownership, boundary, errors and original/current threshold are
included in reports. Disable restores only an owned current=1 threshold and requires a full
restart to clear actor effects. All three initializers now capture all reflected fields.
Mission records remain untouched pending evidence; no blanket stale-50 migration is applied.


## 0.1.6 regen test — 2026-11-05 13:06–13:08 UTC

Reviewed all four root reports: startup 130627 and F10 130654, 130823, 130832.
All exports completed without top-level collector/export errors. No observer callback errors
are recorded. Startup correctly leaves the absent tuning asset pending; every gameplay
capture has state=active, original=50, current=1, owns_edit=true and no tuning errors.
All 16 tuning PRE/POST hook registrations are confirmed. Later thresholds remain 61 and 73.
Gameplay reports confirm actual player level 1, playthrough 2, OP 0. The last two show three
Glacial_P AI pawns at level/stage 1 and the equipped starter pistol remains level/stage 1.
The user reports visible enemy health regeneration has returned. Together with the runtime
threshold evidence this passes the initial low-level tuning/regen gate for this encounter;
it does not establish full UVHM fidelity for every actor/content or native effect.

The expanded initializer snapshot confirms ConditionalInitialization.bEnabled=true; its
default uses Init_EnemyHealth scaled by approximately 0.015, with a separate maximum
restriction. ValueFormula.bEnabled=false is therefore not proof of disabled regen. The
mod has not changed either calculation path. Effective per-pawn regen rate remains
unmeasured; no numeric rate is inferred from the visible recovery report.

Blindsided remains accepted with record/definition stage 1. My First Gun remains completed
with record/definition stage 50 (its definition was 1 during the preceding gameplay session,
consistent with native restoration of the stored record on load). This completed stale
record is left unchanged. No level-up, cross-level reward, map transition, or fresh reload
is established by this batch. No new source gameplay change or release is justified yet.
Next test: mission acceptance lock versus world scaling across a level-up and save/reload,
using 0.1.6 and the same patched EXE. Do not artificially flatten or migrate mission stages.


## 0.1.6 mission-lock session — 2026-11-05 13:26–13:46 UTC

Reviewed all eight root JSONs: 132617 startup; 132651; 132837 armed My First Gun card;
132848 reward; 134152; 134349 after level-up; 134635 armed Blindsided card; 134652 reward.
Every export completed with no top-level errors or recorded observer callback errors.
Startup pending asset is expected. Every gameplay snapshot remains genuine UVHM/OP0,
threshold active=1, original=50, with no tuning errors.

My First Gun again has a prepared-save record at stage 50 while its first-session locked
definition is 1. It completes at player level 1 with reward query/UI payload 47 XP and
10 credits; the currency transaction changes 1826 to 1836. Starter reward payload stage=1.
Its record remains completed=50, and its definition becomes 50 in later captures after
controller recreation. No stale-record migration is justified or performed.

Blindsided (GD_Episode02.M_Ep2_Henchman) is observed accepted with stored and locked
definition stage 1 at player level 1 in 132848 and 134152. At 134349 the actual player is
2, while both mission stages remain 1. At 134635 it is ready to turn in (status 3) and
still 1. At 134652 it is completed (status 4) and still 1. The newly accepted Cleaning up
the Berg (GD_Episode02.M_Ep2a_MoreGuns) has stored/locked definition stage 2 at player 2.
This passes the observed native acceptance-lock gate across the player's 1-to-2 level-up;
no SDK mission-level rewrite or sidecar is needed for this case.

Blindsided native GetExperienceReward returns 35; SetRewardsXP receives '35 XP'. Its
GetCurrencyReward returns 10; SetRewardsTotalCredits receives 10. ServerGrantMissionRewards
PRE/POST and AddCurrencyOnHand show cash 1756 to 1766. Actual XP points remain unavailable
(the previously sampled PRI ExpPoints property does not exist), so 35 is an evaluated and
UI-payload amount, not a verified XP-total delta. Empty/default reward structs have null
balance definitions and are not physical stage-0 items. As user reports, this mission has
no equipment reward, so this batch cannot validate equipment scaling across the level-up.

GetExpectedGameStage returns 2 for Blindsided at player 2 despite actual locked stage 1.
Treat this separately as an expected/offered-stage query. Rendered mission level/difficulty
text is not captured, so neither claim the mission was upgraded nor claim all UI agrees.
Reward XP/cash payloads retain the observed locked-stage values. My First Gun's completed
record remains 50. A controller change from _2 to _5 supports intervening reloads before
Blindsided completion; no post-completion reload report exists after 134652.

The one sampled Glacial_P pawn in later captures remains stage/level 1 after the player
reaches 2. This alone does not establish failed world scaling: spawn timing and native
mission/encounter exceptions are not resolved. Do not rescale it to 2 to flatten exceptions.

Next targeted validation, with unchanged 0.1.6: Cleaning up the Berg is accepted at 2 and
has a configured standard common shield reward pool. Capture its turn-in/reward payload,
ask the user to read the actual shield level, then save-quit/reload and capture accepted
and completed mission records. Capture newly spawned enemies in the next area. Continue
normal play rather than requiring another forced level-up or repeated boss farming.


## 0.1.7 — cleanup for an ongoing playthrough

User reaffirmed vanilla UVHM across the board, without enemy scaling edits, and asked
whether the current state was suitable for a proper playthrough and unnecessary debugging
could be removed. Recommendation: reasonable solo early-access play on the tested character
with periodic save copies. No claim of complete campaign/DLC validation. Native equipment
rewards across a level-up, weapon-slot SDUs, later content/thresholds and rendered UI still
need evidence. The prepared first mission's stale record is not silently repaired.

The gameplay tuning module remains byte-identical to 0.1.6. Diagnostic targets fall from
59 to 36, removing 23 general scaling/stage, spawn/population, pickup and inventory-init
tracers. Existing bounded mission/reward/currency/inventory/combat/UI history is retained.
Automatic startup exports and the broad runtime class catalogue are removed. Initializer
captures now include verified calculation fields without reflected UObject internals.
F10/Export JSON now and one-shot mission-card capture remain. Export serialization,
checkpoint/recovery and bounded event history remain unchanged. No gameplay function is
called by the export routine beyond the verified observational playthrough getter.

All completed probe controls, including the read-only query button and hidden data/native
experiments, are removed from the entrypoint. The live export API no longer accepts probe
arguments. probes.py and region_probe.py remain in development source for historical research
but are excluded from the .sdkmod. Packaging now checks relative imports against the actual
release manifest, so an omitted development module cannot be an accidental dependency.
The EXE and saves are not modified by this cleanup.
