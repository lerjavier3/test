---
name: challenge-trader
description: PAPER ONLY one week aggressive challenge (2026-10-06 to 2026-10-13, $100,000 start, $300,000 minimum target). Margin, shorts, crypto and long calls or puts, around the clock, run by the deterministic loop in scripts/challenge_run.py. Never use with live money. Does not use risk-manager, swing-trader or day-trader.
---

# Challenge Trader (PAPER ONLY)

The user asked for an aggressive paper experiment: whole $100,000, leverage, around the clock, 3x as a minimum by 2026-10-13. **3x in a week is extremely unlikely and the most likely result is a large loss.** Never write or imply otherwise.

These rules must **never** be used with live money. `risk-manager`, `swing-trader` and `day-trader` stay the rules for real money.

**All trading logic is in `scripts/challenge_run.py`.** Scheduled check ins only follow `trading/RUNNER.md`: they don't trade by hand, re-derive the strategy or edit the rules. If the script fails, log and stop; don't improvise. The exception is strategy changes, which the user allows at any time, and at least once a day in the **daily review** in `trading/RUNNER.md` after the US close. A change may replace the strategy in the script (never the hard guards), test it with `scripts/challenge_test.sh`, restart the loop and log the change in `trading/journal/reviews.md`. The strategy below is the starting version; the reviews log what changed since.

## Hard guards (in code)

| Guard | Rule |
| --- | --- |
| Paper only | Refuses unless the endpoint is paper, `ALPACA_PAPER` is not `false` and `state.json` mode is `paper_challenge` (exit 2). |
| Equity floor | Below **$25,000** equity: no new trades, exits only. |
| Options | Buy calls or puts only, never sell to open. |
| Stops | Every stock entry has a bracket stop (regular hours) and a mental stop checked every tick; crypto gets a broker stop_limit; options exit at minus 50%. |
| Hygiene | Unique `client_order_id` per order (`ch-<SYMBOL>-<YYYYMMDDHHMM>-<n>`), fill confirmed, unfilled limits canceled. |

## Strategy (what the script does)

* **Signal:** 1 hour bars. Long breakout = close above EMA20 above EMA50 and above the prior 20 bar high; short breakdown is the mirror. Stop 1.5 ATR(14, 1h), take profit 4 ATR.
* **Universe:** QQQ, SPY, IWM, NVDA, TSLA, AAPL, MSFT, AMZN, META, AMD, GOOGL, AVGO; BTC/USD, ETH/USD, SOL/USD.
* **Sizing:** 4% of equity at risk per trade (2% outside regular hours). One stock position at most 1.0x equity (0.6x after 15:40 ET and outside regular hours). Gross exposure at most 3.5x intraday, trimmed to 1.9x from 15:45 ET and outside regular hours (Reg T overnight limit is 2x). At most 6 positions. Crypto is cash only and long only.
* **Sessions:** regular: longs, shorts (before 15:40 only), crypto, options. Pre, post, overnight: stock longs with extended hours limits, crypto. Weekend: crypto.
* **Options:** once a day between 09:35 and 11:00 ET, buy the QQQ call (first 5 minute bar up) or put (down), nearest expiry 1 to 4 days out, strike nearest the money, at most 8% of equity in premium. Exit at minus 50%, plus 100%, or 15:45 ET the day before expiry.
* **Exits:** stop hit, signal flipped against the position, option rules, leverage trim (biggest loser first).
* **Target:** $300,000 is a minimum, not a cap. Risk doesn't change when it is reached.
* **End:** the last stock session is 2026-10-12; at 15:50 ET it closes all stocks and options, then only crypto trades. At 04:30 ET on 2026-10-13 (before the user checks at 18:00 SGT) it cancels all orders, closes everything, writes `trading/journal/challenge-summary.md`, sets `challenge_active` false and exits.

## Files

* `trading/state.json`: equity peak, trough, max drawdown, leverage samples, mental stops, gaps between runs.
* `trading/journal/YYYY-MM-DD.md`: one line per tick that did something, plus an hourly heartbeat.
* `trading/challenge.log`: loop output.
