"""Read existing reflected fields; never guess fields or traverse the UObject graph."""

from __future__ import annotations

import re
from itertools import islice

from unrealsdk.unreal import UObject, WrappedArray, WrappedStruct

from .core import finite_number, safe_text, unavailable

MAX_FIELDS = 32
MAX_ARRAY = 12
MAX_DEPTH = 7
MAX_NODES = 900
PRIVATE = re.compile(r"uniqueid|netid|steam|account|password|token|address|filename|savegameid", re.I)
INTERNAL = re.compile(r"^VfTable_|^Debug|^Bullet(?:Penetrated|Reflected|Ricocheted)", re.I)
PRIORITY = {name.lower(): i for i, name in enumerate((
    "GameStage", "ExpLevel", "GameStageForSpawnedInventory", "bGameStageLocked",
    "MissionDef", "Mission", "Status", "MissionName", "GameStageRegion", "Reward",
    "AlternativeReward", "BalanceDefinition", "PawnBalanceDefinition", "BalanceModifiers",
    "BalanceModifiersForPlayersWithOneLevelCapUpgrade",
    "BalanceModifiersForPlayersWithTwoLevelCapUpgrades",
    "BalanceModifiersForPlayersWithTwoLevelCapUpgradesAndOverpower",
    "Health", "ShieldStrength", "bIsBadass", "RegionGameStages",
))}
RELEVANT = re.compile(
    r"mission|gamestage|explevel|effectivelevel|overpower|region|balance|difficulty|reward|"
    r"health|shield|regen|damage|slag|amplif|status|cash|money|price|cost|grade|manufacturer|"
    r"weapon.*slot|slot.*weapon|playthrough|boost|level|formula|modifier|inventorydefinition|"
    r"itemdefinition|bIsBadass|badass|boss|displayed|current|active|title|name", re.I
)


def identity(obj):
    if obj is None:
        return None
    try:
        return {"path": safe_text(obj._path_name()), "class": safe_text(obj.Class.Name)}
    except Exception as exc:
        return unavailable(f"object identity: {type(exc).__name__}: {exc}")


def property_names(obj, limit=2048):
    struct = obj._type if isinstance(obj, WrappedStruct) else obj.Class
    # The scan itself is bounded, even for a large class.
    return [str(prop.Name) for prop in islice(struct._properties(), limit)]


def read(obj, name):
    if obj is None:
        return unavailable("object not loaded")
    try:
        struct = obj._type if isinstance(obj, WrappedStruct) else obj.Class
        struct._find_prop(name)  # Validate before accessing. No speculative accessor calls.
        return getattr(obj, name)
    except Exception as exc:
        return unavailable(f"{name}: {type(exc).__name__}: {exc}")


class Snapshot:
    def __init__(self, max_nodes=MAX_NODES, max_depth=MAX_DEPTH, max_fields=MAX_FIELDS, max_array=MAX_ARRAY):
        self.nodes = 0
        self.truncations = []
        self.errors = []
        self.max_nodes, self.max_depth = max_nodes, max_depth
        self.max_fields, self.max_array = max_fields, max_array

    def value(self, value, depth=0):
        self.nodes += 1
        if self.nodes > self.max_nodes:
            self._truncate("node budget")
            return unavailable("snapshot node budget exceeded")
        if value is None or isinstance(value, (bool, int)):
            return value
        if isinstance(value, float):
            result = finite_number(value)
            if isinstance(result, dict):
                self.errors.append("non-finite float")
            return result
        if isinstance(value, str):
            result = safe_text(value)
            if len(value) > 384:
                self._truncate("string length")
            return result
        # Arrays MUST be distinguished from structs before reading reflected fields.
        if isinstance(value, (WrappedArray, list, tuple)):
            if depth >= self.max_depth:
                self._truncate("array depth")
                return unavailable("array depth limit")
            count = len(value)
            if count > self.max_array:
                self._truncate("array length")
            return {"items": [self.value(v, depth + 1) for v in islice(value, self.max_array)],
                    "count": count, "truncated": count > self.max_array}
        if isinstance(value, WrappedStruct):
            # Formula/effect structs need BaseValueConstant, AttributeToModify, etc.
            # Their actual reflected fields are safe within our existing bounds.
            return self.fields(value, depth + 1, pattern=None)
        if isinstance(value, UObject):
            return identity(value)  # Never recursively follow object references.
        if isinstance(value, dict):
            return {safe_text(k): self.value(v, depth + 1) for k, v in islice(value.items(), self.max_fields)}
        # Unreal enums may be Python enum/int subclasses; never repr arbitrary objects.
        return unavailable(f"unsupported type {type(value).__name__}")

    def fields(self, obj, depth=0, pattern=RELEVANT):
        if depth >= self.max_depth:
            self._truncate("struct depth")
            return unavailable("struct depth limit")
        if obj is None:
            return unavailable("object not loaded")
        try:
            names = [n for n in property_names(obj) if not PRIVATE.search(n) and not INTERNAL.search(n)
                     and (pattern is None or pattern.search(n))]
            names.sort(key=lambda n: PRIORITY.get(n.lower(), len(PRIORITY)))
            if len(names) > self.max_fields:
                self._truncate("field count")
            result = {}
            for name in names[:self.max_fields]:
                try:
                    result[name] = self.value(getattr(obj, name), depth)
                except Exception as exc:
                    reason = safe_text(f"{name}: {type(exc).__name__}: {exc}")
                    self.errors.append(reason)
                    result[name] = unavailable(reason)
            return result
        except Exception as exc:
            reason = safe_text(f"reflection: {type(exc).__name__}: {exc}")
            self.errors.append(reason)
            return unavailable(reason)

    def _truncate(self, reason):
        if reason not in self.truncations:
            self.truncations.append(reason)

    def object(self, obj, pattern=RELEVANT):
        return {"object": identity(obj), "fields": self.fields(obj, pattern=pattern),
                "errors": list(self.errors), "truncations": list(self.truncations)}
