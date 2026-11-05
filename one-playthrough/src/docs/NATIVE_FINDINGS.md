# Native scaling feasibility gate — 2026-11-05

**The executable contains a literal level-50 minimum in the native UVHM stage calculation.**
No compliant way to replace that calculation through the normal SDK has been established.
The mod is still a diagnostic prototype; it is not ready for a real level-1 UVHM campaign.

The executable was read only. SHA-256 before/after analysis:
`1231b384aea791bc51286664627d03e27d6a77ffd4ec3bb5001186c136504c17`.
It is a PE32 x86 image with preferred base `0x400000`. Addresses below identify this sample
only. No patch, runtime address write, injected interceptor or executable edit was produced.

## Verified native path

1. Native registration records for both `UWillowRegionDefinitionexecGetRegionGameStage`
   and `URegionDefinitionexecGetRegionGameStage` point to the same execution wrapper.
2. That wrapper dispatches through the object's native vtable slot `0x144`. The derived
   region constructor supplies the Willow vtable whose slot targets the region getter.
   An explicitly bound superclass UFunction would use this same execution wrapper and
   still dispatch through the derived object's native vtable; it is not a bypass.
3. The getter enters a common region routine. It calls the replication-info native
   playthrough getter, adds one, and compares with 3. The corresponding reflected
   `GetCurrPlaythrough` execution wrapper uses the same playthrough vtable slot.
4. For UVHM (index 2), the routine calls an unnamed native helper, writes its result
   to the stage output, and returns success. This happens before the ordinary regional
   balance-list path. The default-region bounds are not the controlling minimum here.
5. The helper contains this decisive branch:

   ```text
   compare candidate stage with 50
   if candidate >= 50: continue to native upper-bound handling
   otherwise: return literal 50
   ```

The floor is an immediate machine-instruction constant. It is not read from a reflected
region bound or the tuning table's `MinEffectiveLevel`. The helper has other direct native
callers too; changing individual mission UI or enemy setters would not repair this shared
calculation or establish preservation of all native consumers.

For technical reproduction, preferred virtual addresses in this sample are: region
execution wrapper `0x00D524D0`, derived getter `0x00F53730`, common region routine
`0x00F53610`, unnamed UVHM helper `0x00F4CCF0`. The analyzer verifies the registrations,
vtable and decisive instructions, rather than treating a generic occurrence of 50 as proof.
The labels for private helpers are analytical descriptions, not recovered source symbols.

## Why the experiments behaved as they did

| SDK route | Observed result | What it establishes |
| --- | --- | --- |
| Native default region-bound queries | 1–2 for StartOfGame, while effective stage is 50 | Default bounds do not remove the UVHM floor |
| First tuning threshold 50 → 1 | XP evaluation changed; region stages stayed 50 | Tuning activates independently of the native floor |
| Native SetGameStageOverride(10) | Returned normally; all three sampled regions stayed 50 | This tested override did not bypass the floor |

The override setter body stores its argument in a native global. The identified UVHM
branch/helper does not consult that override. Only a write is found among literal absolute
references to that global in this executable; this is not a universal proof against all
possible indirect aliasing, but it matches the observed lack of effect. It also confirms
that assuming a private per-region property would have been incorrect.

## SDK boundary

The standard hook on `GetRegionGameStage` exposes a **bool** return. Stage and awesome level
are separate output parameters. The documented hook arguments are copies; changing them
does not replace the original values. Post-hook return changes do not alter completed
execution. More importantly, the UVHM helper is reached by a direct native call, not by a
reflected UFunction dispatch that normal Python hooks intercept.

The contract is documented in the official
[hook manager](https://github.com/bl-sdk/unrealsdk/blob/master/src/unrealsdk/hook_manager.h)
and [Python hook implementation](https://github.com/bl-sdk/pyunrealsdk/blob/master/src/pyunrealsdk/hook.cpp).
The helper reads native player/playthrough state and applies the literal minimum. Spoofing
player level or changing UVHM identity would violate the brief, rather than remove it.

Directly removing/replacing this exact minimum requires native-code intervention or an SDK
capability beyond the tested normal runtime hooks/data. A larger reimplementation that
corrects individual actors, items, missions and rewards is another architecture; it would
require separate proof of native UVHM semantics and is not silently substituted here.
This finding does not prove that no conceivable external SDK development could ever expose
an adequate override. It does establish the concrete native blocker for this implementation.

**No further gameplay captures are needed for these same hypotheses.** Changing the
implementation constraints or pursuing new native SDK capabilities requires discussion
with keogh. No such work or executable patching is authorized by this analysis.

## Reproduction and artifacts

From the project root, with the research requirements installed:

```sh
python3 src/research/analyze_native.py
```

The script opens the input for reading only, refuses a different executable hash, validates
the recovered instruction/registration chain, verifies the hash again, and writes analysis
only under `src/`. Outputs:

- `src/research/native-analysis.json`: verified metadata, checks, call/reference candidates.
- `src/research/native-disassembly.txt`: bounded disassembly for the relevant routines.
- `src/research/analyze_native.py`: maintainable read-only analysis source.

These are offline static-analysis results, reconciled with the supplied in-game reports.
They do not establish an implemented or tested gameplay fix. The executable itself is not
included in the mod package or release artifacts.


## Subsequent decision and game evidence

The user subsequently authorized an external executable patch and installed their verified
Borderlands2_Patched.exe (hash and exact differences in INVESTIGATION.md). The 12:47–12:52
UTC logs confirm UVHM index 2 and level-1 enemies/starter weapon. The original brief's
no-EXE condition is superseded by this explicit decision. The SDK package does not apply or
verify that external patch. A separate 0.1.6 correction lowers only the native first tuning
activation threshold; regen and full UVHM fidelity still need in-game validation. Earlier
sections describe the unpatched investigation and its historical constraints.
