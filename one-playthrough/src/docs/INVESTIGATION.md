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


## First synthetic test save — 2026-11-05

User explicitly authorized editing a clean saves/Save0001.sav into one test checkpoint.
Original SHA-256: 56184c07d675707f44f8c75c1e9f309cd97169ab1dfc7b5965e1af8e15034be8.
It is level-1 Axton, XP 0, two weapon slots, three empty mission-playthrough entries.
Raw base LastPlaythroughNumber/PlaythroughsCompleted are 1/1, but Gearbox special packed
inventory expansion record 2 adds 1/1: effective UVHM index 2, completed=2. Record 3 stores
has-played-UVHM=1; record 5 selects OP0. Do not misdiagnose the base fields as TVHM or
increment them: expansion decoding would then select an invalid/different playthrough.
The earlier user-facing TVHM reading was corrected after inspecting Gibbed SaveExpansion.

The pinned loot-midget editor (2f9f17d4a159d64a962c8f998d679c860293da7a) can verify and
roundtrip the raw decoded save. A full human-JSON re-encode changes the special placeholder
item serials, so it was rejected. The new builder patches only selected raw protobuf fields
and preserves all packed inventory/expansion entries byte-for-byte. Source and work data
remain in src; the original input was never written.

Candidate dist/TestSaves-0.1.0/Save7F01.sav: OP Test 01 Plan B, distinct save slot/GUID,
Sanctuary station, first five main story missions completed, Plan B ready to turn in.
Objective counts, dependency chain, completion-set indices and station come from the public
OpenBLCMM BL2 datapack 2023-04-20-01. The four required class dumps are fetched with bounded
ZIP range requests and checked by CRC/length; their SHA-256s are recorded in the manifest.
The cold-cache fetch path reproduces all four dumps. Character level/XP, slots, skills,
cash/ammo, cosmetic data, normal/TVHM records and unrelated fields remain unchanged.
Mission stages are explicitly 1 in this synthetic level-1 test scenario. No SDU is inserted,
no reward pool is changed, and no mod/EXE changes were made. The objective is to test native
Plan B reward selection and third-slot unlock; format checks do not establish game validity.

Disk readback verifies output SHA-1/CRC, exact edited protobuf roundtrip, all mission fields,
opaque inventory preservation and unchanged source hash. Manifest/README document the data
changes and the intended F10-before/card/after/reload test. If world state or HQ access is
wrong, capture F10 and stop rather than playing through the story. Await first game load.


## Test-save 0.1.1 — corrected saved travel identifier

First game load of candidate 0.1.0 produced a missing-DLC message and fallback to Windshear
Waste despite all DLC installed. The candidate incorrectly wrote the definition UObject
path to VisitedTeleporters/LastVisitedTeleporter (protobuf fields 16/17). Gibbed's
FastTravelViewModel writes station.ResourceName instead of ResourcePath. Its pinned
Borderlands2Dumps Travel Stations table confirms ResourceName=Sanctuary, level=Sanctuary_P,
with no DLC expansion for GD_FastTravelStations.Sanctuary.Sanctuary. The intended destination
was always base-game Sanctuary. The warning does not establish any missing installed DLC.

The root cause was the generator's semantic destination format, missed by structural
roundtrip checks. build_plan_b now validates the destination against a pinned Gibbed table
(SHA-256 13597a2e29e6bc4ef34cb70ccb5db2b59ab9872b9c916cbe88c5ff03b02198ab)
and writes the short ResourceName. The repair script creates 0.1.1 from the exact delivered
0.1.0 binary by changing only fields 16/17 to Sanctuary. Raw comparison verifies every
other protobuf field, including GUID, mission state, opaque inventory/UVHM data, remains
identical. Output SHA-1/CRC and manifest SHA-256 validate on disk. Original input remains
unchanged; 0.1.0 is verified archived and only 0.1.1 remains loose. Mod 0.1.7 and EXE untouched.

User should close game and replace only the previous test Save7F01.sav, then retry the
Sanctuary/Plan B test. The corrected destination and HQ/world setup still need game validation.


## Plan B candidate validated in game — 2026-11-05 16:37–16:39 UTC

Reviewed all five root 0.1.7 logs: 163707 before turn-in; 163830 armed card; 163847
reward; 163909; 163926 after reload. All exports complete, no top-level collector/export
errors, no observer callback errors. All five confirm level 1, actual UVHM index 2, OP0,
tuning threshold active=1 with no tuning errors. Loaded/pending map-name lists include
Sanctuary_P and its associated levels, confirming the corrected short travel identifier
reaches base-game Sanctuary. The ready stage-1 Plan B record becomes completed stage 1,
and Hunting the Firehawk is automatically accepted at 1. The final capture has a newly
created controller _5 and restored mission state: the completed/accepted records persist.

ReceiveItemReward and SetPendingMissionRewardData explicitly contain
GD_StorageDeckUpgrade.A_Item.INV_SDU_WeaponEquipSlot, with balance
GD_ItemGrades.StorageDeckUpgrades.ItemGrade_SDU_WeaponEquipSlot, stage 1. The user reports
an SDU slot was obtained and the scenario looked correct. This is a native low-level UVHM
SDU award without any SDK reward override or pre-inserted SDU. Plan B therefore does not
require the proposed fallback for this tested state; do not assume SDUs are strictly
NVHM-only. Selection at other stages, and the fourth-slot mission, remain unverified.

Reward query/card payload is 35 XP / 10 credits; ServerGrantMissionRewards and currency
PRE/POST confirm cash 0->10. Actual XP-total delta is unavailable. CurrentNumOfHolsteredWeaponSlots
remains 1 in every capture; this cannot be used as a count of unlocked weapon slots.
The visual unlock is user evidence, and the JSON proves the SDU item was awarded; direct
slot-capacity and slot-persistence reads are not established. No new mod/save edits needed.
Machine-readable validation is in src/test_saves/results/plan_b_0.1.1.json. Release manifest
records build-time game_verified=false; it is kept immutable, with this later result separate.


## Extended test-save pack 0.2.0 — 2026-11-05

User authorised additional focused checkpoints and powerful combat gear. Delivered
11 unique characters (02–12): accepted-stage shield reward, fourth weapon-slot reward,
level-10 world/pickups/vendors, 49→50 / 60→61 / 72→73, Scarlett and Tina arrivals,
Mercenary Day boss checkpoint, level-80 OP0 baseline, and alternative Rakkaholics reward.
Every character has five on-level backpack guns, Sham/Magic Missile equipped, spare Bee,
ammo and normal unspent skill points. Source input's opaque expansion records preserved;
all travel destinations use verified short ResourceNames. Mission dependencies, objective
counts/sets and DLC package IDs come from game-data dumps. Level-boundary XP is one
point below the next level and checked against Gibbed's independent float-constant formula.

Build/verification tools: src/test_saves/build_pack.py and verify_pack.py. Sources, hashes,
per-character setup and item-code attribution are in the release manifest/license. Previous
0.1.1 pack verified archived; 0.2.0 is loose. SDK 0.1.7, EXE and original Save0001 untouched.
All new scripted world/mission states and supplied gear still require in-game validation.
README tells the user to F10 and stop any checkpoint with missing NPC/door/objective,
without replaying earlier story. Suggested first batch: 02,03,04.


## Test 02 in-game result — 2026-11-05 17:39–17:41 UTC

All four logs/02 exports complete without top-level or observer event errors. Player10,
UVHM2/OP0, active tuning threshold1. Cleaning up the Berg remains stored/locked stage5
while ready, completed and after controller recreation/reload. ReceiveItemReward explicitly
contains a standard Tediore shield with GameStage5 and ManufacturerGradeIndex5. Queries
and reward-card payloads show477XP/15cash; actual cash10000→10015 persists after reload.
Actual XP-total delta unavailable. Best Minion Ever is newly accepted at stage10.

User reports journal level5 but turn-in card level10. Same screen's captured
GetExpectedGameStage return is10 despite locked definition5; this is consistent with a
presentation-path discrepancy, not evidence that rewards or authoritative stage upgraded.
Rendered Flash text is not captured; UI level10 is user evidence. Keep cosmetic issue open
and investigate a narrow UI consumer before considering changes to general stage queries.
Existing third EXE byte at CAF942 is a HUD branch change already present; its involvement
in this turn-in screen is not established. No new mod/EXE/save edits for this result.
ResourcePoolMap still reports unsupported MapProperty reflection; no gameplay failure.
Machine-readable evidence: src/test_saves/results/test_02_0.2.0.json. Proceed to test03.


## Test 03 in-game result — 2026-11-05 17:47–17:48 UTC

Four logs/03 exports complete without top-level or observer event errors. Player20,
UVHM2/OP0, threshold1. Bright Lights Flying City remains stored/locked stage16 while
ready, completed and after controller recreation/reload. ReceiveItemReward PRE/POST
contains the native INV_SDU_WeaponEquipSlot, SDU balance, stage/grade16. No class-mod
replacement observed in that reward event. Cash10000→10055 persists; query/card XP2585
and cash55. Actual XP-total delta unavailable. Wildlife Preservation accepted at20.
User reports03 seemed good; direct unlocked slot capacity/persistence is not exposed by
these diagnostics, so native SDU award is established separately from that measurement.
GetExpectedGameStage returns20 with locked16, consistent with the known presentation
query discrepancy; rendered card level for03 is not separately confirmed. Only nested
unsupported ResourcePoolMap read errors remain. No runtime/save/EXE changes needed.
Evidence: src/test_saves/results/test_03_0.2.0.json. Proceed to04.


## Test 04 in-game result — 2026-11-05 17:51–17:55 UTC

Seven logs/04 exports complete; player10, UVHM2/OP0, active threshold1, no top-level,
tuning or event callback errors. Only nested unsupported ResourcePoolMap reads persist.
Ice_P stage10 AI samples have ExpLevel9/10/11, with fresh stage10 AI at12 after reload.
This establishes unflattened level variation including above-player samples, not a forced
player-level minimum. Stage0/level0 dynamic pawn excluded; not every AI is identified hostile.
Three vendor types use stage10; bounded stock samples are8/9/10 with matching GameStage,
ExpLevel and DefinitionData stage. New vendor actors/stock appear after controller reload.

Hunting the Firehawk stays active/locked10 throughout. Cash10000→10020 and equipped
sample stage10 persist after controller14→17 reload. AddInventory usable-item/class-mod/
grenade events and player TakeDamage events observed; user reports all looked good.
Ground pickup snapshots do not expose item levels; direct pickup/currency/ammo events
are absent. Resource sample stays full, so individual pickup amounts, natural-drop levels
and evaluated vendor prices are not independently established. No repeat test requested
without a concrete failure. Next suggested batch08/09/10/12 per README. No runtime changes.
Evidence: src/test_saves/results/test_04_0.2.0.json.


Test04 user follow-up: several picked-up items visually on or around player level;
no pickup issue reported. This adds user observation to the limited JSON ground-item
coverage; exact item levels/individual pickup amounts remain unmeasured.


## Boundary save XP correction 0.2.1 — 2026-11-05

User reports test05 earned arrival/discovery XP and reached50 before the baseline F10.
This is a test-fixture defect: original boundary margin was one XP point. No test05 JSON
supplied at this point; no gameplay/scaling failure inferred. Revised05/06/07 to start
5,000XP below50/61/73 respectively. Raw old/new comparison proves ONLY protobuf field3
(XP) changed in those three saves. All other eight binaries are byte-identical; names,
GUIDs, missions, gear, spawn and UVHM/OP records preserved. Pack0.2.0 verified archived;
current loose pack0.2.1 includes updated steps and source/verifier support for XP margins.
All11 staged save/gear/mission checks pass; delivered hashes and archived comparisons pass.
User should close game, replace only Save7F05/06/07.sav, F10 after arrival, kill nearby
XP enemies until target level, F10, then reload/F10. Exact kill count/discovery buffer
sufficiency still needs in-game testing. Existing02–04 results remain valid; no mod/EXE edits.
Repair tool: src/test_saves/repair_boundary_xp.py.


## Test05 corrected checkpoint result — 2026-11-05 18:07–18:14 UTC

Five logs/05 exports complete, no top-level/tuning/event errors; only known nested
ResourcePoolMap reflection errors. Actual level49 first, then50 in four subsequent
captures, UVHM2/OP0, threshold1 throughout. Corrected discovery-XP margin allowed
pre-level baseline. Hunting the Firehawk stays active/locked49 throughout. Captured
equipped weapon stays49 after level-up; user reports other gear unchanged. Stage49
AI start with levels48–51; subsequent stage50 AI show49–52, preserving offsets.
Existing vendor stock remains47–49, predating level-up; no fresh restock claim.

User reports new level50 SMG from bullymong pile. AddInventory WillowWeapon_16 at
18:13:57 records weapon acquisition but not its level/type/source; visual evidence
provides those details. All five use controller2 and no later load sequence is captured,
so post-level save/reload remains outstanding. Request one save-quit/reload/F10 before
moving on to06; no repeat combat/loot needed. No mod/EXE/save edits.
Evidence: src/test_saves/results/test_05_0.2.1.json.


Test05 follow-up: user confirms save-quit/reload/F10 performed, enemies50, vendor
level50 gear and all owned inventory unchanged. No additional logs/05 JSON present
at review. Reload behaviour supported by user observation; JSON corroboration pending.
No repeat capture requested; upload existing export when convenient, continue06.


Test05 reload JSON received:181628, controller2→5, level50 UVHM2/OP0 threshold1;
mission still active/locked49, equipped weapon49, stage50 AI with levels49–51, fresh
vendor stage50 and sampled stock48/49/50. Export complete with only known nested
ResourcePoolMap reflection error. User full-inventory observation supplements equipped
sample. Reload requirement now evidenced; test05 captured checks pass. Continue06.


## Test06 in-game result — 2026-11-05 18:17–18:22 UTC

Three logs/06 captures confirm player60→61→61, UVHM2/OP0 threshold1 throughout.
Mission remains active/locked60; equipped weapon60 survives level-up and controller8→11
reload. Existing stage60 actors persist immediately after levelling; after reload stage61
AI show60/61/62. Vendor stage60/stock58–60 becomes fresh stage61/stock59–61 after reload.
All exports complete; no top-level/tuning/event errors, only known nested ResourcePoolMap
reflection error. Reported gameplay looked good. Captured transition/reload checks pass.
Active native cap/OP balance table selection and exact combat multiplier transition are
unavailable; no claim all level61 tuning mechanics independently proven. No runtime changes.
Evidence: src/test_saves/results/test_06_0.2.1.json. Continue07.


## Test07 in-game result — 2026-11-05 18:23–18:26 UTC

Three logs/07 exports complete:72→73→73, UVHM2/OP0 threshold1. Mission remains
active/locked72 and equipped weapon72 through levelling and controller14→17 reload.
Existing stage72 actors/stock70–72 persist immediately after levelling; fresh stage73
AI after reload show72–75 and vendor stock71–73 at vendor stage73. OP remains0.
No top-level/tuning/event errors; only known nested ResourcePoolMap reflection error.
User reports looked good. Captured transition/reload checks pass; exact combat tuning
multiplier/table selection remains unmeasured. No runtime changes. Continue08.
Evidence: src/test_saves/results/test_07_0.2.1.json.


## Test08 in-game result — 2026-11-06 09:36–09:43 UTC

Seven logs/08 captures complete. Player10, UVHM2/OP0 threshold1 throughout; only known
nested ResourcePoolMap errors. Prepared save initially loads Glacial_P/Windshear, not
Oasis: direct DLC destination fixture failed, cause unproven. User manually fast travelled;
subsequent map lists confirm Orchid_OasisTown_P. A Warm Welcome is initially absent,
then natively assigned active/locked10 via UpdateMissionStatus; remains10 through
controller2→5 reload in Oasis. Stage10 AI samples show10/11; vendor stage10 stock8–10.
User reports on-level enemies and fresh level11 drop. Drop level is visual evidence;
JSON does not directly expose contained ground-item levels. Reload captures only dynamic
stage0 pawn, so post-reload hostile levels unmeasured. Gameplay/DLC intro checks pass
after travel; starting checkpoint destination remains separate unresolved fixture issue.
No runtime/save/EXE changes. Evidence: src/test_saves/results/test_08_0.2.1.json. Continue09.


## Test09 in-game result — 2026-11-06 09:48–10:00 UTC

Seven logs/09 exports complete; player10, UVHM2/OP0 threshold1, only known nested
ResourcePoolMap reflection errors. First snapshot Glacial_P with no Aster intro mission;
subsequent Docks_P records A Role-Playing Game active/locked10. Stage10 AI levels9/10/11
preserve variation; after controller8→11 reload, Docks_P, mission10 and stage10/level9
AI persist. Equipped weapon10 throughout. User reports mission/enemies on level and
fresh10 shotgun drop, latter visual evidence rather than directly logged ground level.
No vendor stock sampled. Initial destination issue recurs in synthetic DLC checkpoint,
separate from successful travel/intro/scaling/reload observations; cause unresolved.
No runtime/EXE/save changes. Evidence: src/test_saves/results/test_09_0.2.1.json. Continue10.


## Test11 in-game result — 2026-11-06 10:04–10:07 UTC

Six logs/11 exports complete: player80 UVHM2/OP0 threshold1, mission active/locked80
and equipped weapon80 throughout controller14→17 reload. Stage80 AI retain levels79–82,
vendor stage80 sampled stock78–80 both before/after reload. User reports several drops
looked good; exact ground-item levels not directly logged. No top-level/tuning/event
errors, only known ResourcePoolMap reflection issue. Captured baseline/reload checks
pass; no controlled mod-off comparison or exact combat/cap-enforcement claim.
User explicitly skips test10 to avoid spoilers for unseen DLC. Leave unverified and do
not request it again. Next12 is the final remaining requested checkpoint. No runtime edits.
Evidence: src/test_saves/results/test_11_0.2.1.json and test_10_skipped.json.


## Test12 branch mismatch and candidate correction — 2026-11-06 10:09–10:12 UTC

Four logs/12 exports complete, player25 UVHM2/OP0, threshold1. Rakkaholics remains
ready/completed/reloaded at stored/locked20. User interacted with Mordecai expecting Sloth,
but ServerGrantMissionRewards explicitly receives bGrantAltReward=true. Pending data
and ReceiveWeaponReward PRE/POST show Rubi, grade/stage20. Default/alt definitions still
Sloth/Rubi respectively. Recipient pawn path is captured but named identity comes from
user. Mission-specific XP query2547. No top-level/tuning/event errors; only ResourcePoolMap.

Suspect synthetic fixture: status3 was pre-inserted while objective counts[10,0,0] left
neither recipient complete. Do not attribute this to SDK scaling or change native rewards.
Candidate pack0.2.2 changes ONLY that mission status3→1 in test12, preserving choice set1,
counts[10,0,0], all other missions/levels/inventory/identity. Other ten saves byte-identical.
Source builder now generates active branch-choice status/set; verifier checks it. All11
structural/gear checks pass and old archive/hashes validate. Retry Mordecai through natural
interaction; outcome still unverified. User's README strikeouts/omitted test10 preserved.

Editor source .git was removed/vendored under parent repository. Old git-HEAD guard
correctly failed before release mutation; compared all25 upstream Python source files
byte-for-byte with pinned2f9f17d4a159d64a962c8f998d679c860293da7a via primary codeload
archive. Added offline file-list/SHA256 verification so parent HEAD is not mistaken for
dependency revision. No upstream source, user save, runtime mod or EXE changed.
Evidence: src/test_saves/results/test_12_0.2.1.json; repair_recipient_choice.py.


## Corrected test12 validated — 2026-11-06 10:20–10:22 UTC

Four additional logs/12 exports complete, player25 UVHM2/OP0 threshold1. Rakkaholics
progresses active1→ready3→completed4→completed4, stored/locked20 throughout. User
observed proper recipient-choice objectives before handover. ServerGrantMissionRewards
now bGrantAltReward=false; ReceiveWeaponReward PRE/POST explicitly Sloth, grade/stage20.
Controller2→5 reload preserves completed20. Only known nested ResourcePoolMap error.

Only test12's mission status changed between candidates, with identical runtime mod,
mission/reward definitions, inventory and stage. This controlled correction establishes
the earlier wrong Rubi arose from the synthetic ready-without-recipient fixture in this
test. No runtime reward override or EXE change needed. User reports worked perfectly.
Chosen test batch is complete;10 remains deliberately skipped for spoilers. Corrected
Moxxi route is optional/unverified. Turn-in level presentation mismatch remains open;
synthetic DLC starting destination issue remains in fixture tooling. Whole campaign/DLC,
full balance/cap equivalence and other native exceptions are not comprehensively proven.
Evidence: src/test_saves/results/test_12_0.2.2.json.


## Stable release1.0.0 — 2026-11-06

User accepts tested gameplay, deliberately defers cosmetic turn-in label issue and requests
release cleanup while retaining F10. Version/author1.0.0/keogh, early-access descriptions
removed. Gameplay tuning, observers, recorder and reflection remain byte-identical to
0.1.7. Only F10 collection change excludes ResourcePoolMap, a repeatedly unsupported
MapProperty; supported pool/value snapshots preserved. No console or automatic startup
logging; bounded recent history, F10/manual/armed mission-screen export retained.
Release packaging now ships INSTALL, TROUBLESHOOTING and RELEASE_NOTES instead of
historical investigation/test records. Source research and user logs preserved. Existing
63 offline tests pass, including registration/version/F10, no startup export, read-only
exports, tuning restoration and package/archive protections. Ad hoc guarded-map snapshot
check confirms unsupported property never read and valid resource values survive.
No executable/save/gameplay or UI correction introduced. Actual1.0.0 game load remains
unobserved; gameplay evidence comes from unchanged0.1.7 tuning/observers and test reports.


## Always-on mission following1.1.0 — 2026-11-06

User explicitly changes the vanilla mission-lock requirement: bake in mission following
without an option. Raises only accepted statuses1/2/3 in actual local UVHM2/OP0; never
lowers a higher saved/definition stage or touches completed/unaccepted records. Independent
implementation in missions.py, informed by existing reflected hooks and reference behavior,
without copying reference code. Updates native mission definition/stored record together;
partial writes read back and attempt owned-value rollback. No direct saves, sidecars or
reward rewrites. Persistence is intentional and not reversed on disable.

Reconciles at enable/load/accept/status/level-up boundaries and before reward completion.
Explicit event mission paths only; no tracked-mission guessing. Temporary per-mission
payout-depth guard prevents turn-in XP level-up from changing that payment's stage while
allowing other unfinished missions to rise. Hook callbacks preserve args/return/flow.
F10 snapshots only, with bounded change history, scope/hook/error/payout state; no console
or automatic startup export. Tuning, recorder, reflection and activity byte-identical to1.0.0.

79 offline tests pass, including new policy scope/status/identity, persistence, higher-stage
preservation, native recipient flag preservation, nested reward payment ordering, invalid
stage rejection, partial rollback, hook lifecycle and F10 read-only checks. These establish
contracts, not in-game hook behavior. Prior acceptance-lock tests are not evidence for the
new following behavior. Reuse unchanged0.2.2 saves02(5→10),12(20→25),03(16→20 +native
SDU safeguard),05(49→50 +owned gear49). Test10 remains skipped. Game validation pending.
No additional EXE changes or enemy-scaling edits. 1.0.0 to be archived as rollback artifact;
raised mission stages already saved will not downgrade automatically with the old mod.


##1.1.0 test02 in game — 2026-11-06 13:10–13:11 UTC

Four root logs confirm player10 UVHM2/OP0. Captured mission-scaling change explicitly
raises Cleaning up the Berg saved/definition5→10 at ApplyMissionSaveGameData POST.
Ready/completed/reloaded mission stays10; shield grade/stage10. Getter/card XP1528 and
actual cash10000→10027; cash persists through controller2→5 reload. Older completed
My First Gun/Blindsided remain5. All14 mission hook phases register; no mission-scaling,
payout guard, export or nested collector errors (unsupported map noise now absent).
User reports all looked good. On-load mission following/reward/reload checks pass.
This does not yet establish live level-up following, alternative rewards or SDU conditions
under new policy;12/03/05 pending. Source evidence:test_saves/results/test_02_1.1.0.json.
User reorganised logs: current exports in root logs/, not old numbered folders. No writes
to user logs. No new runtime changes or release needed. Continue12 as planned.


##1.1.0 test12 received — 2026-11-06 13:14–13:15 UTC

Four captures confirm native status1→3→4→4, player25 UVHM2/OP0, stored/locked20→25
explicitly raised on ApplyMissionSaveGameData POST; completed25 persists controller8→11
reload. No mission/export/nested errors,14 hook phases registered, payout guards empty.
XP getter/card3772, cash0/unchanged. Native grant bGrantAltReward=true, ReceiveWeaponReward
Rubi stage/grade25. This is not Sloth; user reports passed but recipient not named.
Asked Moxxi vs Mordecai to distinguish intended alternate route from prior wrong-branch
fixture failure. Level-following/reward-stage/reload checks pass; recipient-route judgment
pending reply. Do not misreport Sloth. No runtime changes.
Evidence: src/test_saves/results/test_12_1.1.0.json.


1.1.0 test12 clarification: user intentionally chose Moxxi. Captured alternative=true
and Rubi25 are therefore correct; mission following/reward branch/reload test passes.
Default Sloth route not separately retested on1.1.0; no regression indicated. Continue03.


##1.1.0 test03 validated — 2026-11-06 13:19–13:20 UTC

Four captures confirm Bright Lights saved/locked16→20 on load at player20 UVHM2/OP0.
Native ReceiveItemReward contains weapon-slot SDU, grade/stage20; no reward override.
XP query/card3820, cash10000→10086. Completed20 and cash persist controller14→17
reload. All14 mission hook phases registered; no exporter/scaler/nested errors, payout
guards empty. User says in-game passed. Native SDU eligibility survived this stage raise;
direct unlock-capacity count remains unexposed. Only requested live level-up05 remains.
No runtime changes. Evidence: src/test_saves/results/test_03_1.1.0.json.


##1.1.0 final focused validation — 2026-11-06 13:22–13:28 UTC

Four test05 captures49/49/50/50 explicitly record mission49→50 in saved record and
definition at OnExpLevelChange POST. Equipped weapon remains49. Ice_P→Sanctuary_P
travel preserves active50; fresh vendor stage50/stock48–50. All14 hooks registered,
no scaler/export/nested errors. Same controller throughout, so do not call final capture
a save-quit reload; raised-stage completion/reward reloads already evidenced02/03/12.
User reports all good. Requested focused1.1.0 tests02/12/03/05 complete; no runtime
changes after test. Payout-induced level-up guard remains offline-tested, not deliberately
triggered in game. Test10 skipped by user. Broader campaign/edge cases remain ongoing
playthrough evidence. F10 retained. Sources:test_05_1.1.0.json and mission_follow_1.1.0_summary.json.
