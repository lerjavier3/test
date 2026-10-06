---
name: swing-trader
description: Daily swing trading routine for the Alpaca account (momentum rotation core plus RSI(2) pullback filler). Run once per trading day at about 15:45 ET. Always load risk-manager first.
---

# Swing Trader

Evidence for these rules is in `research/RESEARCH.md` sections 4.3, 4.4 and 4.6. Follow them exactly. Don't improvise extra trades.

## Schedule

Run on US market days at **15:45 ET** (enough time to fill before the 16:00 close). If the market is closed (holiday) or closes early, log it and exit.

## Step 0: risk check

Load and run the `risk-manager` skill. If `halted` is true or a breaker has tripped, stop here.

## Step 1: data

For every ticker in the universes below, get at least 260 daily bars from Alpaca market data (adjusted for splits and dividends). Use today's latest trade price as today's close. Compute:
* `SMA200`, `SMA5` of the close
* `RSI2`: Wilder RSI with period 2
* `MOM126`: close / close 126 trading days ago minus 1
* `ATR20`: 20 day average true range

**Market regime:** `RISK_ON` = SPY close above SPY SMA200.

## Sleeve A: Momentum rotation (60% of equity)

**Universe (liquid large caps and sector ETFs):**
AAPL MSFT NVDA AMZN GOOGL META AVGO TSLA BRK.B JPM LLY V UNH XOM MA COST HD PG JNJ WMT NFLX ABBV BAC CRM ORCL AMD KO PEP MRK CVX ADBE TMO CSCO MCD ACN LIN ABT WFC DIS INTU IBM QCOM TXN CAT GE AMGN ISRG NOW SPGI GS UBER AMAT MU BKNG LOW HON PLTR
XLK XLF XLV XLE XLY XLP XLI XLU XLB XLRE XLC GLD

**Rebalance:** only on the **last trading day of each month**. On other days, only check stops.

**First run exception:** if Sleeve A holds nothing and `trading/state.json` has no `last_rebalance` date, do one rebalance on the first run instead of waiting for month end, then set `last_rebalance` to today. This gets the core sleeve invested and the plumbing tested during the first paper week. After that, month end only.

On rebalance day:
1. If not `RISK_ON`: sell everything in Sleeve A and stay in cash until the next month end.
2. Otherwise, rank the tickers that are above their own SMA200 by `MOM126`, highest first. Skip any ticker with earnings in the next 2 trading days if that data is available.
3. Target the **top 5**, each at 1/5 of the sleeve (12% of equity each).
4. Sell holdings that are no longer in the top 5. Buy the new ones. Resize existing holdings only if they're more than 25% off target.
5. **Protective stop** for each holding: 3 x ATR20 below the entry price. Raise it monthly to 3 x ATR20 below the current price (never lower it). If a stop is hit mid month, leave that slot in cash until the next rebalance.

## Sleeve B: RSI(2) pullback (20% of equity)

**Universe:** SPY QQQ IWM DIA

Every day:
1. **Exit:** sell any Sleeve B holding whose close is above its SMA5, or that has been held 10 trading days.
2. **Entry:** if `RISK_ON` and there's a free slot (at most 2 positions, each 10% of equity), buy tickers where close is above SMA200 **and** RSI2 is below 10. If there are more candidates than slots, pick the lowest RSI2 first.
3. **Disaster stop:** 2.5 x ATR20 below entry, placed as a GTC stop order.

## Cash

Uninvested cash stays in cash. Sleeve capital is a guideline: if Sleeve A is in cash because of the regime, Sleeve B does **not** borrow its money.

## Output

Append to today's journal: regime, each sleeve's holdings, trades with the rule that fired, stops placed, and target progress.
