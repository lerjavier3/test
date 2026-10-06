---
name: day-trader
description: Intraday Opening Range Breakout routine on QQQ and SPY for the Alpaca account. Entry run at 09:36 ET, exit run at 15:50 ET. Always load risk-manager first. Flat every night.
---

# Day Trader (5 minute Opening Range Breakout)

**Status: experimental.** Research (`research/RESEARCH.md` section 3) shows this rule is roughly break even after realistic costs in independent tests. It trades only while it's in paper mode, or with real money only after the minute data backtest in section 7 of the research shows a positive edge **and** the user approves.

## Capital

20% of equity, times `day_sleeve_size_multiplier` from `trading/state.json`.

## Run 1: entry at 09:36 ET

1. Load `risk-manager` and run the checks. If the day sleeve is blocked, stop here.
2. Skip the day if it's a half day, an FOMC announcement day, or a CPI release day (log the reason).
3. For each of **QQQ** and **SPY**, get the first 5 minute bar (09:30 to 09:35 ET): `O`, `H`, `L`, `C`.
4. Direction:
   * `C > O` by more than 0.05%: **long** setup
   * `C < O` by more than 0.05%: **short** setup (only if the account allows shorting; otherwise skip)
   * otherwise: no trade for that ticker
5. Entry: a marketable limit order right away (at most 0.05% through the quote).
6. Stop: for longs, `L` (the opening range low); for shorts, `H`.
7. Size: `R = |entry - stop|`. Shares = (0.5% of equity x multiplier / number of tickers traded today) / R. Cap position value at 50% of day sleeve capital per ticker. If `R` is under 0.05% of price, skip (too tight to survive the spread).
8. Send entry with an attached stop loss (bracket order). Take profit: entry + 10R for longs, entry minus 10R for shorts (rarely reached; mostly the trade ends at the close).

## Run 2: exit at 15:50 ET

1. Cancel any open day sleeve orders.
2. Close every position tagged to the day sleeve with marketable limit orders. Nothing from this sleeve is held overnight.
3. Record each trade's result in R multiples and dollars. Update `consecutive_day_losses` in `trading/state.json`.

## Plan B: intraday momentum "noise area" rule (inactive)

Switch to this rule **only** if the minute data backtest (`research/RESEARCH.md` section 7, step 1) shows ORB doesn't beat zero after costs, the noise area rule does, and the user approves the switch. Until then, don't trade it.

Based on Zarattini, Barbon and Aziz (2024) on SPY:

1. For each minute of the day `t`, compute `sigma_t` = the average over the last 14 days of `|close at t / open of that day - 1|`.
2. Noise band for today: upper = `max(open, prior close) x (1 + sigma_t)`, lower = `min(open, prior close) x (1 - sigma_t)`.
3. Check only at :00 and :30 of each hour from 10:00 to 15:30 ET. Price above the upper band: be long. Below the lower band: be short (if shorting is allowed). Inside the band: be flat.
4. Trailing stop: for longs, the higher of the upper band and VWAP; for shorts, the lower of the lower band and VWAP. Exit when it's crossed.
5. Same sizing, loss limits and 15:50 ET flat rule as ORB. No leverage.

## Rules that never change

* At most one entry per ticker per day. No re-entries after a stop.
* No averaging down, no moving the stop farther away, no holding overnight.
* If the 09:36 run starts after 09:45 ET (for example a scheduling delay), skip the day. The setup is no longer valid.
