---
name: challenge-trader
description: PAPER ONLY aggressive challenge (2026-10-06 to 2026-10-20, $100,000 start, $500,000 minimum target, no cap). Margin, shorts, crypto and long calls or puts, around the clock, run by the deterministic loop in scripts/challenge_run.py. Never use with live money. Does not use risk-manager, swing-trader or day-trader.
---

# Challenge Trader (PAPER ONLY)

The user asked for an aggressive paper experiment: whole $100,000, leverage, around the clock, 5x as a minimum by 2026-10-20 (changed on 2026-10-06 from 3x by 2026-10-13). **5x in two weeks is extremely unlikely and the most likely result is a large loss.** Never write or imply otherwise.

These rules must **never** be used with live money. `risk-manager`, `swing-trader` and `day-trader` stay the rules for real money.

**All trading logic is in `scripts/challenge_run.py`.** Scheduled check ins only follow `trading/RUNNER.md`: they don't trade by hand, re-derive the strategy or edit the rules. If the script fails, log and stop; don't improvise. The exception is strategy changes, which the user allows at any time, and at least once a day in the **daily review** in `trading/RUNNER.md` after the US close. A change may replace the strategy in the script (never the hard guards), test it with `scripts/challenge_test.sh`, restart the loop and log the change in `trading/journal/reviews.md`. The strategy below is the starting version; the reviews log what changed since.

## Hard guards (in code)

| Guard | Rule |
| --- | --- |
| Paper only | Refuses unless the endpoint is paper, `ALPACA_PAPER` is not `false` and `state.json` mode is `paper_challenge` (exit 2). |
| Equity floor | Removed by the user on 2026-10-06 (`equity_floor` 0). Alpaca itself may restrict a low account. |
| Options | Buy calls or puts only, never sell to open. |
| Stops | Every stock position has a real GTC stop order at the broker (bracket, OTO or a backup stop the bot places) plus the bot's own stop check every tick; crypto gets a broker stop_limit; options exit at minus 50%. |
| Earnings | No stock is held overnight into its earnings report (`trading/earnings.json`). |
| Hygiene | Unique `client_order_id` per order (`ch-<SYMBOL>-<YYYYMMDDHHMM>-<n>`), fill confirmed, unfilled limits canceled. |

## Strategy (what the script does)

* **Strategies:** several run side by side, defined in `scripts/strategies.py` (shared with the backtester), each with a capital weight in `trading/state.json` → `weights`. Order ids carry the strategy name (`ch-<strategy>-<SYMBOL>-<stamp>-<n>`); `owners` maps each open position to its strategy, which manages its exits. `trading/journal/strategy-scoreboard.md` has backtest (in and out of sample) and live results plus the exact rules.
* **Sizing:** 2.5% of equity at risk per trade at equal weights, scaled by the strategy's weight (half outside regular hours). Each strategy may use its weight's share of the gross cap: 3.5x intraday, 1.9x from 15:40 ET and outside regular hours, all strategies combined. At most 3 positions per strategy, 8 in total, one per symbol. One hour re-entry cooldown after any close. Crypto is cash only and long only.
* **Target:** $500,000 is a minimum, not a cap; keep pushing as high as possible. Risk doesn't change when it is reached.
* **End:** the last stock session is 2026-10-19; at 15:50 ET it closes all stocks and options, then only crypto trades. At 04:30 ET on 2026-10-20 (before the user checks at 18:00 SGT) it cancels all orders, closes everything, writes `trading/journal/challenge-summary.md`, sets `challenge_active` false and exits.

## Files

* `trading/state.json`: equity peak, trough, max drawdown, leverage samples, mental stops, gaps between runs.
* `trading/journal/YYYY-MM-DD.md`: one line per tick that did something, plus an hourly heartbeat.
* `trading/challenge.log`: loop output.
