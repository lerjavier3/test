---
name: challenge-trader
description: PAPER ONLY one week aggressive challenge (2026-10-06 to 2026-10-13, $100,000 to a $300,000 target). Margin, shorts, crypto and long calls or puts, 24/7. Run by the scheduled challenge Routines. Never use with live money. Does not use risk-manager, swing-trader or day-trader.
---

# Challenge Trader (PAPER ONLY)

This mode exists because the user asked for an aggressive paper experiment: use the whole $100,000, use leverage, trade around the clock, try for 3x in one week. **3x in a week is extremely unlikely. The most likely result is a large loss.** Never write or imply otherwise in a journal, summary or message.

These rules must **never** be used with live money. The conservative `risk-manager`, `swing-trader` and `day-trader` skills stay the rules for any real money use.

## Hard guards (enforced in code, never work around them)

`scripts/challenge.py` refuses to run unless the endpoint is `paper-api.alpaca.markets`, `ALPACA_PAPER` is not `false` and `trading/state.json` has `"mode": "paper_challenge"`. Never pass `--live`, never edit those checks.

| Guard | Rule |
| --- | --- |
| Equity floor | Equity below **$25,000**: no new trades. Closing and stop management only. |
| Window | After 2026-10-13 16:00 ET: no new trades, the challenge is over. |
| Options | **Buy** calls or puts only. Never sell to open. |
| Crypto | Long only (Alpaca crypto can't be shorted or margined). |
| Stops | Every new position has a stop: broker stop if possible, else a mental stop that every run checks. |
| Hygiene | Every order has a unique `client_order_id`; the script refuses duplicates and confirms the fill. |

## Each run: lean, about 6 tool calls

1. `python3 scripts/challenge.py preflight` (JSON: session, equity, leverage, positions, open orders, `can_open_new`, `is_final_run`).
2. If preflight says the challenge is over, go to **End of challenge**.
3. **Manage** every open position (rules below).
4. If `can_open_new` is true: `python3 scripts/challenge.py signals` and **enter** per the rules below.
5. `python3 scripts/challenge.py journal --run <hourly|open|close> --note "..."` one note per order or decision (symbol, side, qty, price, stop, reason), plus any blocked trade or error.
6. `bash scripts/challenge_push.sh` and exit. No long analysis, no web searches.

If any API call fails, do nothing new, journal it and push. If preflight's `rate_limit_failures` grew, mention the gap in the journal note.

## Sizing

* **Risk per trade:** 4% of equity, `qty = 0.04 * equity / abs(entry - stop)`, rounded down (whole shares for shorts).
* **Max gross exposure** (long plus short value / equity): 3.5x during the regular session; **1.9x** for anything held through 16:00 ET and in pre, post and overnight sessions (Reg T allows 2x overnight; going over invites a margin call).
* At most 6 open positions. No adding to a position already held.
* Extended and overnight session stock entries use half risk (2%).

## Entries (`signals` output, 1 hour bars, ATR = `atr14_1h`)

| Session | Allowed |
| --- | --- |
| regular | stocks long or short, crypto, options (open run only) |
| pre, post, overnight | stock **longs** with `--extended` limit orders, crypto |
| closed (weekend) | crypto only |

* **Stocks:** enter only on `long_breakout` (buy) or `short_breakdown` (sell short). Stop = `long_stop` / `short_stop` (1.5 ATR). Take profit 4 ATR. Regular session:
  `python3 scripts/challenge.py order NVDA buy 120 --limit <ask*1.001> --stop <long_stop> --tp <last+4*ATR> --id ch-NVDA-<YYYYMMDDHHMM>-1`
  Extended or overnight (no brackets there):
  `python3 scripts/challenge.py order NVDA buy 60 --limit <ask*1.002> --extended --mental-stop <long_stop> --id ...`
* **Crypto** (BTC/USD, ETH/USD, SOL/USD): buy on `long_breakout` only, with cash (`non_marginable_buying_power`). After the fill, place a broker side stop as a closing order:
  `python3 scripts/challenge.py order BTC/USD sell <filled_qty> --stop-limit <long_stop> --limit <long_stop*0.99> --tif gtc --id ch-BTCUSD-<stamp>-s`
* **Options** (09:36 ET open run only, QQQ or SPY): if the first 5 minute bar of QQQ closed up, buy a call; down, buy a put. Nearest expiry 1 to 3 days out, strike nearest the money, find it with `python3 scripts/alpaca.py option-chain QQQ --type call --exp-gte <tomorrow> --exp-lte <+3d>`. Spend at most 8% of equity on premium, limit at the ask, `--mental-stop <premium*0.5>`. Exit at minus 50% or plus 100% of premium, or at the 15:50 run if it expires the next day.
* Never enter a symbol with an open order already working on it.

## Managing open positions (every run)

* **Mental stops** (`state.json` → `mental_stops`): if the latest price is past the stop, close (cancel any open order on the symbol first, then a marketable limit 0.3% through the quote, `--extended` outside regular hours) and run `challenge.py clear-stop <SYMBOL>`.
* **Signal flip:** a long whose signal is now `short` or `short_breakdown`, or a short whose signal is `long` or `long_breakout`: close it.
* **Leverage check:** at the 15:50 run, and in any non regular session, if gross leverage is above 1.9x, close the weakest positions (largest loss first) until it is below 1.9x.
* **Options:** apply the minus 50%, plus 100% and next day expiry exits. Never let an option expire in the money unattended.
* Closing a position with a working stop or bracket: `alpaca.py cancel <order_id>` for those child orders first, then close.

## Scheduled runs

| Routine | Time | Extra work |
| --- | --- | --- |
| Hourly | every hour, 24/7 | the run above |
| Open | 09:36 ET weekdays | options entry (ORB direction), stock entries |
| Close | 15:50 ET weekdays | close options expiring next day, cut leverage to 1.9x |

Routine ids are kept in `trading/state.json` → `routines`.

## End of challenge

On the **15:50 ET run on 2026-10-13** (preflight `is_final_run` true), or any run after the window:

1. Cancel all open orders (`alpaca.py cancel-all`) and close every position (stocks, options, crypto) so end equity is final.
2. `python3 scripts/challenge.py summary` for the numbers, then write `trading/journal/challenge-summary.md` with: start and end equity, return, best and worst 3 trades, max drawdown, how leverage affected the result (gross leverage levels used, what the same trades would have returned at 1x), missed runs from `rate_limit_failures`, and what a sane real money plan looks like instead (the conservative plan in `trading/PAPER_PLAN.md` and `research/RESEARCH.md`: roughly 10% to 15% a year expected, 15% drawdown halt, no leverage).
3. Set `"challenge_active": false` in `trading/state.json`.
4. Disable every Routine in `state.json` → `routines` with the `update_trigger` tool (`enabled: false`). If that tool is not available, journal it so the user can disable them by hand.
5. Push with `scripts/challenge_push.sh`.
