"""UVHM No Health Regen Please - disable UVHM enemy health regeneration only."""

from __future__ import annotations

from typing import Any

from mods_base import CoopSupport, Game, RestartToDisable, build_mod, hook
from unrealsdk import find_all, find_object, load_package, logging
from unrealsdk.hooks import Type

PT3_TUNING_PATH = "GD_Playthrough3Tuning.Balance.BalanceMod_PT3"
REGEN_ATTRIBUTE_NAME = "HealthPassiveRegenerationRate"
REGEN_FORMULA_NAME = "Init_EnemyHealthRegenFormula"

_regen_effect_snapshots: dict[str, dict[str, Any]] = {}
_regen_formula_snapshots: dict[str, dict[str, Any]] = {}
_regen_disabled = False


def _obj_path(obj: Any) -> str:
    try:
        return str(obj._path_name())
    except Exception:
        return str(obj)


def _get_pt3_tuning() -> Any | None:
    try:
        load_package("GD_Playthrough3Tuning")
    except Exception:
        pass

    for cls in ("BalanceModifierDefinition", "Object"):
        try:
            obj = find_object(cls, PT3_TUNING_PATH)
            if obj is not None:
                return obj
        except Exception:
            continue
    return None


def _snap_value(value: Any) -> dict[str, Any]:
    return {
        "BaseValueConstant": value.BaseValueConstant,
        "BaseValueAttribute": value.BaseValueAttribute,
        "InitializationDefinition": value.InitializationDefinition,
        "BaseValueScaleConstant": value.BaseValueScaleConstant,
    }


def _restore_value(value: Any, snapshot: dict[str, Any]) -> None:
    value.BaseValueConstant = snapshot["BaseValueConstant"]
    value.BaseValueAttribute = snapshot["BaseValueAttribute"]
    value.InitializationDefinition = snapshot["InitializationDefinition"]
    value.BaseValueScaleConstant = snapshot["BaseValueScaleConstant"]


def _zero_value(value: Any) -> None:
    value.BaseValueConstant = 0.0
    value.BaseValueAttribute = None
    value.InitializationDefinition = None
    value.BaseValueScaleConstant = 0.0


def _disable_regen_effects() -> int:
    tuning = _get_pt3_tuning()
    if tuning is None:
        logging.error("[UVHM No Health Regen Please] PT3 tuning object not found")
        return 0

    count = 0
    for modifier_index, modifier in enumerate(getattr(tuning, "BalanceModifiers", ())):
        effects = getattr(modifier, "AttributeEffectsForSpawnedEnemies", ())
        for effect_index, effect in enumerate(effects):
            attr = getattr(effect, "AttributeToModify", None)
            if attr is None or REGEN_ATTRIBUTE_NAME not in str(attr):
                continue

            value = getattr(effect, "BaseModifierValue", None)
            if value is None:
                continue

            key = f"{modifier_index}:{effect_index}"
            if key not in _regen_effect_snapshots:
                _regen_effect_snapshots[key] = _snap_value(value)
            _zero_value(value)
            count += 1
    return count


def _disable_regen_formulas() -> int:
    try:
        load_package("GD_Playthrough3Tuning")
    except Exception:
        pass

    count = 0
    for obj in find_all("AttributeInitializationDefinition"):
        path = _obj_path(obj)
        if REGEN_FORMULA_NAME not in path:
            continue

        formula = getattr(obj, "ValueFormula", None)
        if formula is None:
            continue

        if path not in _regen_formula_snapshots:
            parts: dict[str, dict[str, Any]] = {}
            for part in ("Multiplier", "Level", "Power", "Offset"):
                value = getattr(formula, part, None)
                if value is not None and hasattr(value, "BaseValueConstant"):
                    parts[part] = _snap_value(value)
            _regen_formula_snapshots[path] = {
                "has_bEnabled": hasattr(formula, "bEnabled"),
                "bEnabled": getattr(formula, "bEnabled", None),
                "parts": parts,
            }

        if hasattr(formula, "bEnabled"):
            formula.bEnabled = False
        for part in ("Multiplier", "Level", "Power", "Offset"):
            value = getattr(formula, part, None)
            if value is not None and hasattr(value, "BaseValueConstant"):
                _zero_value(value)
        count += 1
    return count


def _disable_regen() -> None:
    global _regen_disabled
    effect_count = _disable_regen_effects()
    formula_count = _disable_regen_formulas()
    _regen_disabled = True
    logging.info(
        "[UVHM No Health Regen Please] Disabled UVHM enemy health regen "
        f"({effect_count} effects, {formula_count} formulas)"
    )


def _restore_regen_effects() -> None:
    tuning = _get_pt3_tuning()
    if tuning is None:
        return

    for modifier_index, modifier in enumerate(getattr(tuning, "BalanceModifiers", ())):
        effects = getattr(modifier, "AttributeEffectsForSpawnedEnemies", ())
        for effect_index, effect in enumerate(effects):
            snapshot = _regen_effect_snapshots.get(f"{modifier_index}:{effect_index}")
            if snapshot is None:
                continue
            value = getattr(effect, "BaseModifierValue", None)
            if value is not None:
                _restore_value(value, snapshot)


def _restore_regen_formulas() -> None:
    if not _regen_formula_snapshots:
        return

    try:
        load_package("GD_Playthrough3Tuning")
    except Exception:
        pass

    for obj in find_all("AttributeInitializationDefinition"):
        snapshot = _regen_formula_snapshots.get(_obj_path(obj))
        if snapshot is None:
            continue

        formula = getattr(obj, "ValueFormula", None)
        if formula is None:
            continue

        if snapshot["has_bEnabled"] and hasattr(formula, "bEnabled"):
            formula.bEnabled = snapshot["bEnabled"]
        for part, value_snapshot in snapshot["parts"].items():
            value = getattr(formula, part, None)
            if value is not None and hasattr(value, "BaseValueConstant"):
                _restore_value(value, value_snapshot)


def _restore_regen() -> None:
    global _regen_disabled
    if not _regen_disabled:
        return
    _restore_regen_effects()
    _restore_regen_formulas()
    _regen_disabled = False
    logging.info("[UVHM No Health Regen Please] Restored UVHM enemy health regen")


@hook("WillowGame.WillowPlayerController:SpawningProcessComplete", Type.POST)
def _on_spawn(*_: Any) -> None:
    _disable_regen()


@hook("WillowGame.WillowPlayerController:WillowClientDisableLoadingMovie", Type.POST)
def _on_map_load(*_: Any) -> None:
    _disable_regen()


@hook("WillowGame.FrontendGFxMovie:NotifyAtMainMenu", Type.POST)
def _on_main_menu(*_: Any) -> None:
    _disable_regen()


def _on_enable() -> None:
    _disable_regen()


def _on_disable() -> None:
    _restore_regen()


mod = build_mod(
    cls=RestartToDisable,
    supported_games=Game.BL2,
    coop_support=CoopSupport.Incompatible,
    on_enable=_on_enable,
    on_disable=_on_disable,
)
