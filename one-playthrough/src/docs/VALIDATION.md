# Validation — 0.1.7

Offline validation on 2026-11-05: **63 tests passed** using Python 3.9.6. Engine tests use
deliberately limited fakes to test JSON robustness and observer behaviour; they cannot establish real
Unreal layouts, hook firing, UI coverage, vanilla UVHM fidelity, or a floor correction.

Run from the project root:

```sh
python3 -m unittest discover -s src/tests -v
python3 src/build.py
```

The packager compiles source without importing game dependencies; checks required modules,
relative imports, release metadata and documentation; and verifies the exact `.sdkmod`
member layout and archive integrity. It refuses missing files and an existing same-version
release. New releases archive previous version folders into verified `.zip` files, preserving
their contents, and leave the current release folder loose. A `.sdkmod` itself is the SDK's
required ZIP-format installable package; don't wrap the current release in another ZIP.

No executable changes, direct save edits, game-console commands or project `logs/` writes.
No gameplay corrections, mission migrations, custom profiles or OP selector.

User-supplied in-game evidence: 11 completed 0.1.0 JSON reports. Genuine UVHM, OP 0,
F10 disk export, level-50 missions/enemies and a level-1-to-10 change around the first turn-in
are observed. All 0.1.0 event hooks had zero hits because of malformed paths; its armed
screen capture failed. See INVESTIGATION.md for filenames and limits of those conclusions.

Actual 0.1.5 in-game checks: **pending** the short session in TESTING.md. The responsible
floor and SDK gameplay correction remain unresolved. No claim of completed level-1 UVHM.

Passing offline coverage: bounded history and detached snapshots; array/struct distinction;
formula preservation; private-field filtering; missing/non-finite values; atomic replacement
failure and interrupted collection; partial collection; read-only level/mission comparisons;
reflected hook registration/pass-through/removal; armed UI capture; entrypoint metadata/F10;
write-failure notification; package layout, missing-file rejection, same-version protection
and verified previous-release archiving. All files in the SDK archive compile successfully.

New regression coverage: SDK-shaped colon paths, inherited function owners, MStatus argument
identity, live actors versus archetypes, stage priority within field bounds, deeper regen
formulas, lifecycle retention under query churn, and completion-screen capture while ignoring
generic HUD refresh. The path test dispatches to the literal correct engine function key;
the old fake used dotted function names and failed to catch the original bug.

Version 0.1.2 adds offline coverage of bounded economy/combat histories, PRE/POST XP state,
combat damage arguments and actor levels, equipped gear without full inventory traversal,
the explicit QuestAccept reward-card path, and explicit mission arguments taking precedence
over unrelated missions on a UI object. Packaging requires the new activity.py module.
All added native action targets are reflected before registration; actual coverage and field
availability remain unverified until the next game session.

Version 0.1.2 user evidence: 12 JSON exports; hooks fired, armed reward capture worked,
UI payloads show 39,108 XP and 2,601 credits for the stage-50 first mission, and the first
weapon reward is generated with GameStage/ManufacturerGradeIndex 50. The player later
reaches level 10. Exact XP delivery remains distinct from the UI payload observation.
No observer exceptions were reported in the supplied hook status snapshots.

Performance evidence: the last report counts 5,208 observer hits. Targets excluded by the
new exact-name list account for 4,475 of them (85.9%). This is an offline name comparison,
not a measured 85.9% frame-time improvement. Interning duplicate event payloads alone reduces
the largest historical report from 4,705,626 bytes to 2,540,620 bytes with the same event
payloads. New smaller event snapshots and fewer event sources reduce work further, but
actual 0.1.3 frame time and file size are not yet measured in-game.

New tests: startup stage history survives loading-movie closure; scaling history survives
pickup churn; polling/physics functions are absent from the target list; 1,000 throttled
calls perform no extra player reads or reflection; compact report references retain exact
event payloads; ordinary F10 never invokes scaling_probe; and explicit output queries
validate exact parameter flags and tuple shape. A probe with an unexpected signature does
not execute. Interrupted collection retains the initial valid history/implementation
checkpoint rather than rewriting the entire report after every section.

Third user session: five current 0.1.3 reports; one incomplete checkpoint (58 KiB), four
completed reports. The user saw a permission error on the incomplete export, then a later F10
succeeded. This file has no exception details; the precise OS error/path cause is unknown.
Completed gameplay reports are approximately 350–370 KiB; user reports no hitch opening one
ammo chest. Ordinary callback max_sample_ms peaks at 0.765 ms in this capture; this is not a
whole-frame benchmark or proof that every chest/content case is fixed.

Native query evidence at character level 10, UVHM index 2, OP 0: StartOfGame default region
bounds 1–2, native current/default region stage 50, mission stages 50, character cap 80.
GetLevelForMission returns the map name Glacial_P and is no longer listed as a numeric level
query. Native GetExperienceReward/GetCurrencyReward match 39108/2601 for My First Gun.

New offline tests cover transient/permanent atomic-replace PermissionError, bounded retries,
full report recovery with errno/phase, first-threshold restoration on success and query error,
failed restoration requiring restart, preservation of later thresholds/combat values, and
ordinary F10 never invoking the data experiment. The recovered-file restart notification also
retains priority over ordinary export warnings. Actual 0.1.4 retry and experiment behaviour
remain untested in-game.

0.1.4 in-game evidence now received: both explicit threshold experiments completed without
errors. Both restored the first threshold to 50, matched the captured tuning snapshot after
restoration, and left later thresholds unchanged. Region and mission stages remained 50.
XP evaluation changed 39108→25811 and 29331→19358 during the temporary edit, then returned
to baseline. This establishes a live tuning effect but no observed floor removal in the
loaded session. Missing HUD feedback did not prevent either JSON export. No scaling success
or universal native blocker is established; see INVESTIGATION.md for the precise limits.

0.1.5 offline validation adds a native-override fake that can behave globally or locally:
the report distinguishes those outputs without assuming scope. Tests verify one setter call
with actual level, restart required after any setter attempt or post-write exception, no
call for changed signatures/flags, rejection of OP selection and level 50+, and blocking
another data experiment until process restart. Ordinary F10 also verifies that the new
region experiment is never invoked. The test harness cannot prove the actual setter's
scope, cache behaviour, native level offsets or persistence. No 0.1.5 game results yet.

0.1.5 in-game result received: native override setter was attempted once with actual level
10 and returned normally. StartOfGame, Waterfront_A and Waterfront_A2 all remained stage 50
for both current/default region queries; their default bounds remained unchanged. No export
errors were reported. This native setter use did not remove the measured floor. No gameplay
correction has passed the feasibility gate. The internal clamp and remaining SDK access
possibilities require native implementation analysis; no full opening replay is requested.

Executable static validation completed using the supplied PE32 file, SHA-256
1231b384aea791bc51286664627d03e27d6a77ffd4ec3bb5001186c136504c17. The read-only analyzer
verified native registration records, region constructor/vtable targets, direct UVHM helper
call, playthrough-dispatch relationship and literal-50 branch. All explicit assertions passed;
the input file's SHA-256 remained unchanged. See NATIVE_FINDINGS.md and src/research/ artifacts.
This is evidence of the implementation blocker, not an in-game gameplay fix. Mod code and
distribution were not changed for the static-analysis hand-off.


0.1.6 offline tests verify the one-field tuning edit preserves other row fields and later
thresholds, restores an owned edit, does not restore an external preexisting=1 edit, refuses
an unexpected later-threshold layout, applies a pending asset in PRE before a spawn without
changing arguments/returns, preserves/report conflicting changes on disable, and keeps F10
read-only even when a tuning manager is attached. All 64 tests pass. The verified patched
EXE gameplay captures establish low enemy/item stages with 0.1.5; actual 0.1.6 UVHM tuning,
regen, early application timing and rollback of native actor effects are not validated by
these fake-engine tests. Use TESTING.md for the next game session.


0.1.6 first in-game validation received (13:06–13:08 UTC): all four JSON exports completed
without collector/export errors. Three gameplay reports have threshold 1, original 50,
state active, no tuning errors and unchanged later thresholds 61/73. Genuine UVHM/OP0 and
level-1 AI/pistol remain confirmed. User reports visible enemy regen is back. Expanded
snapshots show the native initializer uses an enabled ConditionalInitialization path even
though ValueFormula is disabled. This validates the initial encounter gate, not all native
combat modifiers or actual numeric regen rates. No cross-level mission or fresh reload
test is established. Continue with the same 0.1.6 release; no code changes made this turn.


0.1.6 cross-level mission evidence received (13:26–13:46 UTC): all eight exports complete
without top-level/observer errors. Blindsided stored and locked definition stage stays 1
from accepted at player 1 through player 2, ready-to-turn-in and completion. Subsequent
Cleaning up the Berg acceptance is stage 2. Blindsided reward getters/UI payloads show
35 XP and 10 credits; actual currency changes 1756->1766. Actual XP delta and a generated
equipment reward across the level-up are not measured. GetExpectedGameStage=2 is distinct
from locked stage=1; rendered mission level/difficulty text remains unverified. Completed
record reload after the final turn-in and fresh-area enemy scaling remain outstanding.
No new runtime code, executable edits, release, or repeated offline tests were required.


0.1.7 cleanup validation: 63 offline tests pass. Three export tests for removed experiment
controls were retired; historical pure probe/restore tests remain as development-only
research checks. New checks verify general scaling/pickup tracers are absent while core
mission/reward hooks remain, retired experimental export keywords are rejected before any
file write, the discovery catalogue is absent, and the package excludes experiment modules.
The entrypoint test verifies enabling produces no automatic JSON, the first F10 still
exports, author/version/options are correct and disable runs. The first-F10 debounce now
starts at negative infinity so a capture is never suppressed merely because the process
clock is below 0.5 seconds. This clock condition was detected by the fake-engine test.

Compared the gameplay tuning module with the tested 0.1.6 SDK mod: identical bytes. No enemy,
reward, mission-record or native tuning value changes beyond the existing threshold edit.
Diagnostic target count 59->36 was derived from the old/new ASTs. No live performance or
0.1.7 game validation is claimed by these checks. Build integrity, import coverage and
previous-release archival are checked before hand-off.


0.1.7 / test-save 0.1.1 in-game validation (16:37–16:39 UTC): five complete, error-free
captures confirm Sanctuary map loading, UVHM2/OP0 at player 1, active threshold 1, native
stage-1 Plan B SDU item reward, cash 0->10, completion at stage 1 and next mission accepted
at 1. Final controller recreation/restored records establish a post-completion reload.
User reports the slot unlock looked correct. JSON does not directly count unlocked slots;
holstered weapon count is not an unlock count. No SDU workaround or runtime change was made.


Test-save pack 0.2.0 offline validation: all 11 written binaries pass outer SHA-1/CRC,
raw-protobuf roundtrip, manifest hashes, unique names/IDs/GUIDs, mission state/count/set
checks against game dumps, travel ResourceName checks, valid level/XP and normal skill
points. Boundary XP independently matches Gibbed at all selected levels. Every supplied
weapon/item has valid serial roundtrip, on-level grade/stage and unchanged seed parts.
Original opaque UVHM inventory prefix and normal/TVHM records are byte-identical; raw
changes restricted to documented allowed fields. Old pack archives pass integrity checks.
SDK 0.1.7 archive members match source; original save and patched EXE hashes unchanged.
No runtime code changes or additional mod tests needed. These checks do not validate
new NPC/world scripts, actual gear effects, DLC arrival, or rewards in game. User testing
pending; full steps and VALIDATION.txt accompany dist/TestSaves-0.2.0.


Test02 / pack0.2.0: four in-game0.1.7 captures establish ready/completed/reloaded mission
stage5 at player10, native shield stage/grade5, cash10000→10015, query/UI477XP and15cash,
and next story mission accepted10. Actual XP-total delta unavailable. All exports complete;
only nested unsupported ResourcePoolMap reflection reported. User-observed turn-in label10
conflicts with journal5; captured GetExpectedGameStage10 is consistent with UI using an
expected-stage query. Presentation acceptance remains open; rewards and mission persistence
pass this test. Existing third EXE patch causality is unproven. No runtime changes.


Test03 / pack0.2.0: four0.1.7 game captures establish native fourth-slot mission SDU
award at16, mission16 completion/reload at player20, next mission accepted20, cash+55
persisted and query/UI2585XP. Direct unlocked-slot count and actual XP-total delta remain
unavailable. User says test seemed good. Expected-stage query20 versus locked16 remains
a presentation investigation; no new rendered-text claim. No runtime changes.


Test04 / pack0.2.0: seven game0.1.7 captures pass sampled level10 world/vendor and
reload checks: stage10 AI ExpLevel9–12, three vendor types at10, bounded stock8–10
with stage/level agreement, accepted mission10 and cash net+20 persisted after reload.
Equipped samples remain10. User reports gameplay good. Natural ground-item levels,
individual pickup/ammo amounts and actual vendor prices remain unmeasured; no full
combat/regen validation claimed. Only known ResourcePoolMap reflection errors. No changes.


Test04 user follow-up: several picked-up items visually on or around player level;
no pickup issue reported. This adds user observation to the limited JSON ground-item
coverage; exact item levels/individual pickup amounts remain unmeasured.


Pack0.2.1 boundary repair: test05 one-point XP setup failed on discovery XP (user report).
05/06/07 now5,000XP below target. All11 structural checks pass; raw XP-only diffs for
three saves, other eight byte-identical, all delivered hashes/old archive integrity checked.
Updated README and generator/verifier. In-game discovery headroom still pending.


Corrected05 / pack0.2.1: five game captures confirm49→50, locked mission49 and
equipped weapon49 after levelling; user reports unchanged gear and new level50 pile SMG.
Fresh stage50 AI retain49–52 variation. No new errors beyond ResourcePoolMap reflection.
All captures share controller2; post-level reload validation still outstanding.


Test05 follow-up: user confirms save-quit/reload/F10 performed, enemies50, vendor
level50 gear and all owned inventory unchanged. No additional logs/05 JSON present
at review. Reload behaviour supported by user observation; JSON corroboration pending.
No repeat capture requested; upload existing export when convenient, continue06.


Test05 reload JSON received:181628, controller2→5, level50 UVHM2/OP0 threshold1;
mission still active/locked49, equipped weapon49, stage50 AI with levels49–51, fresh
vendor stage50 and sampled stock48/49/50. Export complete with only known nested
ResourcePoolMap reflection error. User full-inventory observation supplements equipped
sample. Reload requirement now evidenced; test05 captured checks pass. Continue06.


Test06 / pack0.2.1: three game captures verify60→61 and reload; locked mission and
equipped weapon60, fresh AI stage61/levels60–62, vendor stage61/stock59–61. No new
errors. User reports looked good. Exact combat tuning/table selection remains unmeasured.


Test07 / pack0.2.1: three game captures verify72→73 and reload at OP0; mission
and equipped weapon72, fresh AI stage73/levels72–75, vendors73/stock71–73.
No new errors. User reports looked good. Exact combat tuning transition unmeasured.
