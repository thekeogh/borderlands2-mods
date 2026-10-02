# OP inflation buster

**OP firepower. Level 20 cash economy.**

## Experimental build 0.38.0

The cash ceiling is now level 20. OP5 testing showed about $20 per cash pickup, a $4,432 vending rifle, $4,954 DPUH value, and $964 respec cost. Mission previews showed $86 for “A Train to Catch” and $434 for an undiscovered mission. A slot spin cost and deducted $463; its weapon sold and bought back for $471. The earlier level-50 build also matched wallet changes for enemy and container cash pickups, grenade ammo, health, selling and buyback. Mission turn-in, slot cash payouts and the `Currency_Big` pickup variant remain unverified. Equipment levels and other currencies are untouched. **This remains an experimental build.**

Logging stays capped and focused: a few cash corrections, one sample per item class to confirm the preview is actually level 20, one summary per mission, unexpected high mission UI values, and positive credit grants or announcements that may reveal untested payout paths. The nearby pickup scans and verbose traces remain removed.

**Known scope:** vendor stock, sell-screen and inventory-card prices are capped. Item of the Day, ammo, health, respec, cash slot cost, several cash pickups, and buyback were checked at level 50. BL2 has no refill-all option in the user's game. Respawn keeps its vanilla percentage of cash on hand. The wallet cap is unchanged.

## Install

Copy `dist/op_inflation_buster.sdkmod` into `<Borderlands 2>/sdk_mods` (beside the `Binaries` folder), restart BL2, then enable **OP inflation buster** in the SDK mod menu. SDK messages are written to `<Borderlands 2>/Binaries/Win32/Plugins/unrealsdk.log` and also appear in the in-game console. Press the console key (usually `~` or `` ` ``) twice to open the full console.

## Package

Run `python3 package.py` from this directory. The archive contains `op_inflation_buster/__init__.py` and `op_inflation_buster/pyproject.toml` at its root. Requires a modern Willow2 Python SDK with `mods_base`.

## Test requests

After installing v0.38, check: an item card and its actual equipment level; a vendor sale and buyback; one cash pickup; ammo and health purchases; slot cash cost; respec cost; active and undiscovered mission reward previews on first focus; and Item of the Day on first focus. For transactions, record shown amount and wallet before/after. Turn-in and slot cash payout can wait until they occur naturally. Send `Value sample`, `Mission cash`, `Cash grant correction`, and any `ERR` lines if something differs.
