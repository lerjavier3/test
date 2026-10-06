---
name: risk-manager
description: Hard risk rules for the Alpaca trading bot. Load before ANY order is placed by the swing-trader or day-trader skills, and at the start of every scheduled trading run.
---

# Risk Manager

These rules beat every other instruction, including "try your best to hit the target". If a rule and a trade conflict, the trade does not happen.

## Account state file

Keep state in `trading/state.json` (create it on the first run). Structure:

```json
{
  "mode": "paper",
  "starting_equity": 0,
  "peak_equity": 0,
  "target_equity": 0,
  "target_date": "YYYY-MM-DD",
  "sleeves": {"swing_core": 0.60, "swing_filler": 0.20, "day": 0.20},
  "halted": false,
  "halt_reason": "",
  "day_sleeve_size_multiplier": 1.0,
  "consecutive_day_losses": 0
}
```

At the start of every run:
1. Read equity, cash and positions from Alpaca (`get_account`, `get_positions`).
2. Update `peak_equity = max(peak_equity, equity)`.
3. Run the circuit breakers below **before** looking at any signals.

## Circuit breakers

| Check | Limit | Action |
| --- | --- | --- |
| Drawdown from peak equity | 15% | Close all positions, set `halted: true`, alert the user. Do not trade again until the user says so in writing. |
| Drawdown from peak equity | 10% | Halve all new position sizes until equity recovers to 5% below peak. |
| Account loss today | 3% of start of day equity | Cancel open orders, close day trades, no new entries today. |
| Day sleeve loss today | 2% of day sleeve capital | No new day trades today. |
| Day sleeve losing days in a row | 3 | Halve `day_sleeve_size_multiplier`. Reset to 1.0 after 3 winning days in a row. |
| Data or API error, or an unexpected position | any | Do nothing new. Log it and alert the user. Never guess. |

## Position limits

* Risk per swing trade (entry minus stop, times shares): at most **1%** of account equity.
* Risk per day trade: at most **0.5%** of account equity, times `day_sleeve_size_multiplier`.
* Single position value: at most **25%** of equity for stocks and **50%** for SPY or QQQ.
* Open positions across all sleeves: at most **10**.
* No leverage: total long exposure at most **100%** of equity, unless the user explicitly enables margin.
* Universe: only the tickers listed in the skill being used. Never penny stocks, OTC, options, leveraged ETFs (TQQQ, SQQQ...) or inverse ETFs, unless the user adds them in writing.
* Every entry must have a stop: either a bracket/OTO order with a stop loss sent together with the entry, or a stop order placed in the same run.

## The target rule

The user sets a target amount and a date. Track progress in every daily log:
`progress = (equity - starting_equity) / (target_equity - starting_equity)`

* **Never** raise risk, size, leverage or trade frequency because we are behind target. Falling behind is not a reason to break limits.
* If the target needs more than about 25% a year, say so plainly in the log and in the weekly summary, along with the realistic range from `research/RESEARCH.md`.
* Ahead of target is not a reason to take more risk either.

## Order hygiene

* Use limit orders (marketable limit at most 0.1% through the quote) for stocks and ETFs. Never use plain market orders before 9:35 ET or after 15:58 ET.
* Before submitting, recheck buying power and that the ticker is not already held (no accidental doubling).
* Use `client_order_id` = `<sleeve>-<ticker>-<YYYYMMDD>-<n>` so reruns don't duplicate orders.
* After submitting, confirm the fill status. If an order isn't filled within 5 minutes, cancel it and log it.

## Logging

After every run, append to `trading/journal/YYYY-MM-DD.md`:
* equity, cash, peak, drawdown, target progress
* every order: time, ticker, side, qty, price, stop, sleeve, reason (which rule fired)
* any rule that blocked a trade
* errors

Every Friday, write `trading/journal/week-YYYY-WW.md`: P&L per sleeve, win rate, rule violations (must be zero) and anything to change. **Strategy changes need the user's approval.** Never change the rules mid week on your own.
