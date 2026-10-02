# OP inflation buster

**OP firepower. Level 50 cash economy.**

## Experimental build 0.37.0

This build keeps the level-50 equipment pricing, respec, slot cost, cash pickups and mission reward previews verified in earlier OP5 tests. Enemy and container cash pickups, grenade ammo and health purchases matched wallet changes. It also corrects the larger `GD_Currency.A_Item.Currency_Big` pickup variant seen in enemy-drop logs; that variant still needs a live pickup check. The user saw $13,005 on first focus for an undiscovered mission across several restarts. Mission turn-in and slot cash payouts remain untested. Other currencies are untouched. **This remains an experimental build.**

Logging is now capped and focused: a few cash corrections, one summary per mission, unexpected high mission UI values, and positive credit grants or announcements that may reveal untested payout paths. The nearby pickup scans, cash use traces, item card reports and startup function lists are removed. Check the mission reward on first focus after updating; removing those probes may affect UI timing.

**Known scope:** vendor stock, sell-screen and inventory-card prices changed in earlier tests. Item of the Day, ammo, health, respec, cash slot cost, several cash pickups, and one buyback matched wallet changes in OP5 tests. BL2 has no refill-all option in the user's game. Respawn keeps its vanilla percentage of cash on hand. The wallet cap is unchanged.

## Install

Copy `dist/op_inflation_buster.sdkmod` into `<Borderlands 2>/sdk_mods` (beside the `Binaries` folder), restart BL2, then enable **OP inflation buster** in the SDK mod menu. SDK messages are written to `<Borderlands 2>/Binaries/Win32/Plugins/unrealsdk.log` and also appear in the in-game console. Press the console key (usually `~` or `` ` ``) twice to open the full console.

## Package

Run `python3 package.py` from this directory. The archive contains `op_inflation_buster/__init__.py` and `op_inflation_buster/pyproject.toml` at its root. Requires a modern Willow2 Python SDK with `mods_base`.

## Test requests

After updating, check an undiscovered mission reward on first focus and one ordinary cash pickup. Note any visible inflated reward or wallet mismatch. Send only related `OP inflation buster` lines and any `ERR` lines from `unrealsdk.log`.
