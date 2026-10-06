# Cash coverage research

Reviewed 6 October 2026; current beta 0.41.0 uses a level 1 cash ceiling.

## Sources and scope

Inspected 14 BL2 object dump classes from [ft-explorer's game data](https://github.com/apocalyptech/ft-explorer/tree/master/resources/BL2/dumps), including 81 usable item definitions, 271 mission item definitions, 288 mission definitions, 602 item spawning behaviors and 1,901 item pools. These are exported game objects, not a complete account of native game code or every runtime grant. The large BehaviorProviderDefinition dump could not be retrieved; individual behavior dumps supplied the relevant spawn and cost data.

## Cash pickups

| Definition | Handling |
| --- | --- |
| `GD_Currency.A_Item.Currency` | Small cash pickups, capped |
| `GD_Currency.A_Item.Currency_Big` | Large cash pickups and slot cash prizes, capped |
| `GD_Currency.A_Item.Currency_Crystal` | Crystalisk gems, capped |
| `GD_Skeleton_Crystal.A_Item.Currency_CrystalBones` | Tiny Tina DLC crystal bones, newly capped |
| Other usable item definitions with the same external credits effect and cash initialization formula | Automatically recognized, capped |
| `GD_RatShared.Pools.Item_RatShared_StolenMoney` | Returned stolen money, unchanged |
| `GD_Allium_GrandmaData.A_Item.CurrencyOneDollar` | Granny Torgue's fixed dollar, unchanged |
| `GD_Z3_ChosenOneData.ItemDefs.ID_MO_ChosenOne_Cash` | Marcus' quest cash item, unchanged |

The four regular cash definitions use an external `D_Attributes.Currency.CreditsOnHand` attribute slot initialized by `GD_Economy.CashPickups.Init_CashPickupCalc`. The new fallback requires this specific combination and credits currency; a cash-looking name or cash sale value alone is insufficient. Classification is cached per definition. [Usable item data](https://github.com/apocalyptech/ft-explorer/blob/master/resources/BL2/dumps/UsableItemDefinition.dump.xz)

The cash formula's `CurrencyItemLevel` attribute resolves the inventory's `ExpLevel`. Pickup correction uses that level, with `DefinitionData.GameStage` as a fallback if the property is absent. It scales the actual positive wallet gain by `1.12 ** (1 - level)`, rounding with a minimum of $1. This remains an approximate level 1 economy; part and grade multipliers are retained. [Cash formulas](https://github.com/apocalyptech/ft-explorer/blob/master/resources/BL2/dumps/AttributeInitializationDefinition.dump.xz), [level resolver](https://github.com/apocalyptech/ft-explorer/blob/master/resources/BL2/dumps/ObjectPropertyAttributeValueResolver.dump.xz)

Rat theft takes a percentage of the player's wallet and uses a separate stolen-money pool. Scaling the returned amount again would destroy part of the refund. That definition is also excluded from inventory price overrides. [Rat theft behaviors](https://github.com/apocalyptech/ft-explorer/blob/master/resources/BL2/dumps/Behavior_AITakeMoney.dump.xz)

## Sources sharing existing cash pickups

Spawn data confirms the following use cash pools already covered by the pickup hooks:

- Captain Scarlett's aqua Crystalisks, including their foot crystals, use `GD_Itempools.AmmoAndResourcePools.Pool_Crystal`.
- Tiny Tina's `GD_Skeleton_Crystal.AmmoAndResourcePools.Pool_CrystalBones` references the dedicated crystal bones inventory balance, now covered.
- Pot O' Gold shield projectiles use `Pool_Money_1`.
- The Wisp projectile uses `Pool_Money_1or2`.
- Standard slot cash prizes use the large-money pool.
- Enemy, boss and container sources that spawn the standard money pools use the same existing pickup correction.

These sources need no separate enemy hooks or changes to loot tables. Aqua Crystalisk coverage is confirmed in the exported data, not yet through gameplay in this mod. [Spawn behaviors](https://github.com/apocalyptech/ft-explorer/blob/master/resources/BL2/dumps/Behavior_SpawnItems.dump.xz), [item pools](https://github.com/apocalyptech/ft-explorer/blob/master/resources/BL2/dumps/ItemPoolDefinition.dump.xz)

## Mission cash and other currencies

`MissionDefinition:GetCurrencyReward` remains restricted to credits. Added `GetOptionalCreditReward` for extra cash when the main reward is another currency. It uses the existing temporary mission preview and restores mission level, player level and mission lock state even on errors. Existing SDK reward code confirms that this function grants credits separately from the main reward. [RewardReroller implementation](https://github.com/ZetaDaemon/bl-sdk-mods/blob/8308420d1ab90394b284ecc46a0d59e34429ac13/RewardReroller/__init__.py)

Inventory price overrides now explicitly skip items valued in other currencies. Eridium, Seraph crystals and Torgue tokens are not cash. Cash pickup detection and slot cost adjustments also require credits. The game data lists Tiny Tina's slot costs as Eridium; those costs are left alone. Fixed tolls, telescope charges and Moxxi tips are outside the slot cost hook. [Usability costs](https://github.com/apocalyptech/ft-explorer/blob/master/resources/BL2/dumps/Behavior_SetUsabilityCost.dump.xz)

## Runtime limits

- No blanket scaling of `AddCurrencyOnHand`: sales, buybacks, refunds and already capped rewards could otherwise be scaled twice.
- Successful pickups, price previews, mission previews and enable/disable events are silent. Removed the direct credit grant, HUD announcement and mission UI logging hooks.
- Diagnostics report unrecognized cash-paying usable pickups, unadjusted mission cash and failures. Each problem is logged once, with at most eight messages total per enabled session. Fixed cash rewards and other currencies are excluded. Unknown direct native grants outside the pickup hooks are not monitored; research cannot establish the source of every native credit addition.
- No continuous world scanning was added.
- Automated tests use a mocked SDK. Native execution, HUD timing, co-op and every DLC encounter still require gameplay observation. The release remains beta; crash-free operation cannot be established from static data alone.
