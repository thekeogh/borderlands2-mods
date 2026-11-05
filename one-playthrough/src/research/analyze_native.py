#!/usr/bin/env python3
"""Read-only analysis of the supplied BL2 executable. No runtime mod dependency.

Reads a PE file, verifies this exact sample, and writes analysis artifacts under
src/. It never opens the input executable for writing, launches it, or emits a patch.
Recovered addresses below apply only to the pinned sample and are not used by the mod.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

import capstone
import pefile

EXPECTED_SHA256 = "1231b384aea791bc51286664627d03e27d6a77ffd4ec3bb5001186c136504c17"
BASE = 0x400000
VTABLE = 0x17DE350
SRC = Path(__file__).resolve().parents[1]
ROOT = SRC.parent

# Boundaries verified by native registration, constructor and direct-call tracing.
RANGES = {
    "region_exec": (0xD524D0, 0xD525C2),
    "region_getter": (0xF53730, 0xF53749),
    "region_test_getter": (0xF53750, 0xF53769),
    "region_implementation": (0xF53610, 0xF53728),
    "uvhm_stage_helper": (0xF4CCF0, 0xF4CD68),
    "player_stage_input": (0xF4CBE0, 0xF4CCEC),
    "upper_limit_helper": (0xF4CB20, 0xF4CBD3),
    "override_exec": (0x1271060, 0x12710AC),
    "override_setter": (0xF3E200, 0xF3E20F),
    "region_constructor": (0xF46AB0, 0xF46ACB),
    "replication_info_playthrough_exec": (0x12579A0, 0x12579D3),
}


def analyze(executable, output):
    executable, output = Path(executable).resolve(), Path(output).resolve()
    if SRC not in output.parents and output != SRC:
        raise ValueError("Analysis artifacts must be under src/")
    data = executable.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError("Different executable hash; refusing to apply this sample's recovered addresses")
    pe = pefile.PE(data=data, fast_load=True)
    if pe.FILE_HEADER.Machine != 0x14C or pe.OPTIONAL_HEADER.ImageBase != BASE:
        raise ValueError("Unexpected PE architecture/image base")
    decoder = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

    def offset(va):
        return pe.get_offset_from_rva(va - BASE)

    def u32(va):
        return struct.unpack_from("<I", data, offset(va))[0]

    def pointer_references(va):
        needle = struct.pack("<I", va)
        positions, start = [], 0
        while True:
            at = data.find(needle, start)
            if at < 0:
                break
            positions.append(BASE + pe.get_rva_from_offset(at))
            start = at + 1
        return positions

    def registration(name):
        encoded = name.encode("ascii") + b"\0"
        at = data.find(encoded)
        if at < 0 or data.find(encoded, at + 1) >= 0:
            raise ValueError("Native registration name missing or ambiguous: " + name)
        name_va = BASE + pe.get_rva_from_offset(at)
        refs = pointer_references(name_va)
        if len(refs) != 1:
            raise ValueError("Registration reference ambiguous: " + name)
        return {"name": name, "name_va": hex(name_va), "record_va": hex(refs[0]),
                "exec_va": hex(u32(refs[0] + 4))}

    instructions = {}
    for name, (start, end) in RANGES.items():
        instructions[name] = [{"va": hex(i.address), "mnemonic": i.mnemonic, "operands": i.op_str}
                              for i in decoder.disasm(data[offset(start):offset(start) + end - start], start)]
    regs = [registration(name) for name in (
        "UWillowRegionDefinitionexecGetRegionGameStage",
        "URegionDefinitionexecGetRegionGameStage",
        "UWillowRegionDefinitionexecSetGameStageOverride",
        "AWillowGameReplicationInfoexecGetCurrPlaythrough",
    )]

    def instruction(va, mnemonic, operands):
        found = next((i for seq in instructions.values() for i in seq if i["va"] == hex(va)), None)
        if found != {"va": hex(va), "mnemonic": mnemonic, "operands": operands}:
            raise ValueError(f"Disassembly verification failed at {hex(va)}: {found}")

    # These are analysis assertions, not native execution tests.
    checks = {
        "derived_and_base_reflected_getters_share_exec": regs[0]["exec_va"] == regs[1]["exec_va"] == "0xd524d0",
        "setter_exec_matches_registration": regs[2]["exec_va"] == "0x1271060",
        "region_vtable_getter": u32(VTABLE + 0x144) == 0xF53730,
        "region_vtable_test_getter": u32(VTABLE + 0x148) == 0xF53750,
        "playthrough_exec_matches_registration": regs[3]["exec_va"] == "0x12579a0",
    }
    if not all(checks.values()):
        raise ValueError("Native registration/vtable cross-check failed")
    instruction(0xD525A6, "mov", "edx, dword ptr [edx + 0x144]")
    instruction(0xD525B2, "call", "edx")
    instruction(0xF53741, "call", "0xf53610")
    instruction(0xF53663, "mov", "eax, dword ptr [edx + 0x448]")
    instruction(0xF5366B, "lea", "esi, [eax + 1]")
    instruction(0xF5366E, "cmp", "esi, 3")
    instruction(0xF53671, "jne", "0xf5368e")
    instruction(0xF53673, "call", "0xf4ccf0")
    instruction(0xF5367B, "mov", "dword ptr [ecx], eax")
    instruction(0xF4CD54, "cmp", "esi, 0x32")
    instruction(0xF4CD57, "jge", "0xf4cd60")
    instruction(0xF4CD59, "mov", "eax, 0x32")
    instruction(0xF4CD5F, "ret", "")
    instruction(0xF3E206, "mov", "dword ptr [0x19c8524], eax")
    instruction(0x12579C1, "mov", "eax, dword ptr [edx + 0x448]")
    checks["instruction_assertions"] = True

    text = next(s for s in pe.sections if s.Name.rstrip(b"\0") == b".text")
    lo, hi = text.PointerToRawData, text.PointerToRawData + text.SizeOfRawData
    direct_calls = []
    pos = lo
    while True:
        pos = data.find(b"\xe8", pos, hi - 4)
        if pos < 0:
            break
        va = BASE + pe.get_rva_from_offset(pos)
        if va + 5 + struct.unpack_from("<i", data, pos + 1)[0] == 0xF4CCF0:
            direct_calls.append(hex(va))
        pos += 1
    report = {
        "analysis_kind": "read-only PE/disassembly; no game execution or binary edits",
        "input": {"filename": executable.name, "sha256": digest, "bytes": len(data), "image_base": hex(BASE), "architecture": "PE32 x86"},
        "registrations": regs, "checks": checks,
        "native_floor": {"entry": "WillowGame.WillowRegionDefinition:GetRegionGameStage",
                         "unnamed_helper_va": "0xf4ccf0", "rule": "if candidate stage < 50, return literal 50",
                         "floor_is_instruction_constant": True, "direct_call_candidates": direct_calls,
                         "helper_pointer_references": [hex(v) for v in pointer_references(0xF4CCF0)]},
        "override_setter": {"writes_native_global": "0x19c8524",
                            "literal_address_references": [hex(v) for v in pointer_references(0x19C8524)],
                            "limit": "No literal read references found; does not exclude arbitrary indirect aliasing elsewhere"},
        "instructions": instructions,
        "limitations": ["This report is specific to the SHA-256 above.",
                        "Native helper names are analyst labels, not recovered public symbols.",
                        "Direct call candidates are byte-pattern hits; region call site is independently disassembled and verified.",
                        "No SDK runtime interception, executable patch or substitute gameplay implementation is included."]}
    if hashlib.sha256(executable.read_bytes()).hexdigest() != digest:
        raise RuntimeError("Input hash changed during analysis")
    report["input_bytes_unchanged"] = True
    output.mkdir(parents=True, exist_ok=True)
    (output / "native-analysis.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = ["Read-only disassembly; addresses apply only to the pinned input SHA-256.", digest, ""]
    for name, seq in instructions.items():
        lines.append(name + ":")
        lines.extend(f"  {i['va']:<12} {i['mnemonic']:<8} {i['operands']}" for i in seq)
        lines.append("")
    (output / "native-disassembly.txt").write_text("\n".join(lines), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path, default=ROOT / "references" / "Borderlands2.exe")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    result = analyze(args.executable, args.output_dir)
    print("Read-only analysis verified; input SHA-256 unchanged:", result["input"]["sha256"])
    print("Native floor: candidate < 50 returns literal 50. Analysis artifacts:", args.output_dir)
