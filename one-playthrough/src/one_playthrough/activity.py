"""Small read-only snapshots for rewards, resources, visible gear and combat."""

from __future__ import annotations

import re

from unrealsdk.unreal import UObject

from .core import unavailable
from .reflection import Snapshot, identity, property_names, read

RESOURCES = re.compile(r"^(?:ExpLevel|ExpPoints|Currency|AmmoResourceUpgrades|LastKnownAmmoCount_.*|ResourcePoolManager|ActiveWeaponSlot|OffHandWeaponSlot|CurrentNumOfHolsteredWeaponSlots)$", re.I)
GEAR = re.compile(r"stage|level|grade|definitiondata|weapon.*definition|item.*definition|balance|inventoryslot", re.I)
COMBAT = re.compile(r"^(?:ExpLevel|GameStage|Health.*|Shield.*|bIsDead|bInjured|.*BalanceDefinition|.*ResourcePool.*)$", re.I)


def player_resources(pc):
    """Only reflected fields, never currency/ammo/XP evaluator or getter calls."""
    if pc is None:
        return unavailable("local controller not loaded")
    pri = read(pc, "PlayerReplicationInfo")
    pawn = read(pc, "Pawn")
    result = {"controller": Snapshot().object(pc, RESOURCES),
              "replication_info": Snapshot().object(pri, RESOURCES) if isinstance(pri, UObject) else pri,
              "pawn": Snapshot().object(pawn, RESOURCES) if isinstance(pawn, UObject) else pawn}
    # One explicit manager hop. Pool data may still be opaque; do not invent counts.
    manager = read(pc, "ResourcePoolManager")  # Actual owner confirmed by 0.1.2 reports.
    result["resource_pools"] = (Snapshot(max_nodes=160, max_depth=4, max_array=6).object(
        manager, re.compile(r"pool|resource|value|current", re.I)) if isinstance(manager, UObject) else manager)
    return result


def equipped_gear(pc):
    if pc is None:
        return unavailable("local controller not loaded")
    pawn = read(pc, "Pawn")
    if not isinstance(pawn, UObject):
        return unavailable("player pawn not loaded")
    result = {}
    for name in ("Weapon", "OffHandWeapon"):
        item = read(pawn, name)
        result[name] = Snapshot().object(item, GEAR) if isinstance(item, UObject) else Snapshot().value(item)
    return {"equipped": result, "coverage": "equipped weapons only; no full inventory traversal"}


def event_object(obj, combat=False):
    return Snapshot().object(obj, COMBAT if combat else GEAR)


def selected_ui_items(obj):
    """At most four directly referenced selected/displayed item objects; no item graph."""
    results = []
    for name in property_names(obj):
        if re.search(r"selected|displayed|focused|reward", name, re.I):
            value = read(obj, name)
            if isinstance(value, UObject):
                results.append({"field": name, "item": Snapshot().object(value, GEAR)})
            if len(results) == 4:
                break
    return {"screen": identity(obj), "items": results, "sample_limit": 4}


def transaction_resources(pc):
    """Hot-path evidence: two scalar XP fields and at most three currency balances."""
    if pc is None:
        return unavailable("local controller not loaded")
    pri = read(pc, "PlayerReplicationInfo")
    if not isinstance(pri, UObject):
        return unavailable("player replication info not loaded")
    fields = {name: Snapshot(max_nodes=8).value(read(pri, name)) for name in ("ExpLevel", "ExpPoints")}
    currency = read(pri, "Currency")
    if isinstance(currency, dict):
        fields["Currency"] = currency
    else:
        from itertools import islice
        fields["Currency"] = [{name: Snapshot(max_nodes=8).value(read(entry, name))
                               for name in ("FormOfCurrency", "CurrentAmount")}
                              for entry in islice(currency, 3)]
    return {"replication_info": {"fields": fields}, "currency_sample_limit": 3}
