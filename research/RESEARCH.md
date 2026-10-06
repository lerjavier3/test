# Trading Research: Day Trading and Swing Trading

Prepared 2026-10-06, before any paper trading. Raw numbers are in `research/results/`. The code is in `research/backtests/` and can be rerun with `scripts/get_data.sh`.

## 1. Summary

* **Day trading is the hard part.** Studies of real retail day traders find that almost all of them lose money. None of the simple day rules I tested on QQQ and VTI showed a reliable edge after costs. The one published intraday strategy with good results (the 5 minute Opening Range Breakout) falls to roughly zero once realistic spreads and slippage are included. Day trading gets a **small** share of the capital and has to prove itself on paper first.
* **Swing trading has the stronger evidence.** Two ideas held up across decades and in both halves of the data:
  1. **A trend filter** (only be long while the market is above its 200 day average). It cut the S&P 500's worst loss from 57% to 29% and QQQ's from 36% to 22%.
  2. **Momentum rotation** (hold the 5 strongest liquid large caps, monthly, only when the market is in an uptrend). On 20 large caps from 1991 to 2022 it returned 14.3% a year with a 25% worst drawdown, versus 66% with no filter.
* **Short pullback trades (RSI 2)** still work on index ETFs and mega caps, but the edge is small and has faded since 2010. On the broad Nasdaq stock list it loses money after costs. It's kept only as a filler for idle cash, and only on index ETFs.
* **Universe matters more than cleverness.** Every strategy lost money on the full list of about 1,450 Nasdaq stocks, small caps included. All playbooks are restricted to very liquid large caps and ETFs.
* **Realistic expectation:** in a normal year the combined plan's backtests point to about 10% to 15% a year, with drawdowns of 15% to 25% possible along the way. Anything much higher than that needs leverage or concentration that also raises the risk of a wipeout.

## 2. Data used

Yahoo Finance, Alpaca, Stooq and similar sites are blocked by this cloud environment's network policy, so these free public datasets were used instead:

| Dataset | Content | Period |
| --- | --- | --- |
| skfolio `sp500_index` | S&P 500 index daily closes | 1990 to 2022 |
| skfolio `sp500_dataset` | 20 large caps (AAPL, MSFT, JPM, XOM...) daily closes | 1990 to 2022 |
| skfolio `nasdaq_dataset` | About 1,450 Nasdaq stocks, daily closes | 2018 to 2023 |
| yennanliu `finance_data` | QQQ and VTI daily OHLCV | 2016 to 2026 |

**Known weaknesses**

* **Survivorship bias.** The large cap and Nasdaq lists contain companies that still existed when the data was saved. This flatters buy and hold and momentum. Comparisons against the equal weight benchmark of the same list are fairer than the raw numbers.
* **No minute data.** Intraday rules like Opening Range Breakout could only be judged from published studies. They'll be tested on Alpaca minute bars once the account is connected.
* **Fills at the close.** Swing signals assume the bot trades about 15 minutes before the close using live prices. A "filled one day late" version is included as a stress test.

Costs charged per side: 2 bps on ETFs, 5 bps on mega caps, 10 bps on other stocks.

## 3. What published research says

### Day trading

* **Most retail day traders lose.** In Taiwan, fewer than 1% of day traders earned predictable profits after fees (Barber, Lee, Liu and Odean, 2014 and 2019). In Brazil, 97% of people who day traded futures for more than 300 days lost money, and only 1.1% earned more than the minimum wage (Chague, De Losso and Giovannetti, 2019).
* **Opening Range Breakout (ORB).** Zarattini and Aziz (2023) traded QQQ in the direction of the first 5 minute candle, with a stop at the other side of that candle. They reported positive results using 4x leverage, but charged no spread or slippage and had no out of sample test. Independent replications with realistic costs find results close to zero, and negative in 4 of 5 markets.
* **Intraday momentum.** The return of the first half hour of the session tends to predict the last half hour on SPY (Gao, Han, Li and Zhou, 2018). Zarattini, Barbon and Aziz (2024) built a "noise area" breakout on SPY from this idea. It's the most credible intraday candidate, and it needs minute data to verify.
* **Overnight vs intraday.** Most of the US stock market's long run gain has come overnight (close to next open), not during the trading day (Lou, Polk and Skouras, 2019). My data confirms it (section 4.1). That works directly against long only day trading.

### Swing and position trading

* **Short term reversal.** Stocks that fell sharply over a few days tend to bounce (Jegadeesh 1990; Lehmann 1990). Connors' RSI(2) rule ("buy above the 200 day average when 2 day RSI is very low, sell when price closes above the 5 day average") is the popular version.
* **Momentum.** Winners of the past 3 to 12 months keep outperforming for a while (Jegadeesh and Titman 1993), in stocks, sectors and asset classes. The main risk is sudden "momentum crashes" after bear markets (Daniel and Moskowitz 2016), which a market trend filter reduces.
* **Trend following / time series momentum.** Assets above their long term average tend to keep going up (Moskowitz, Ooi and Pedersen 2012; Faber 2007, 10 month average). The main benefit is avoiding the deepest crashes, not raising returns.
* **Volatility scaling.** Taking smaller positions when volatility is high improves risk adjusted returns (Moreira and Muir 2017). This is built into position sizing.

### Regulation

* The SEC approved removing the **Pattern Day Trader rule** and its $25,000 minimum on 2026-04-14. FINRA set the effective date to 2026-06-04, but brokers get up to 18 months to switch over. During setup I'll check how the Alpaca account reports day trading limits. Under the new rules, intraday margin needs a margin account above $2,000.

## 4. My backtest results (key rows)

### 4.1 Where the money comes from (2017 to 2026)

| | Overnight only | Intraday only (no costs) | Buy and hold |
| --- | --- | --- | --- |
| QQQ, yearly | 12.9% | 6.0% | 19.7% |
| VTI, yearly | 13.2% | **minus 0.6%** | 12.6% |

Being long during market hours captured little or none of the market's gain. After a 2 bps cost each way, going long QQQ every day from open to close **lost 4.2% a year**, and VTI lost 10.1% a year.

### 4.2 Simple day rules on QQQ (open to close, 2017 to 2026, after costs)

| Rule | Yearly | Worst drawdown | 2017 to 2020 | 2021 to 2026 |
| --- | --- | --- | --- | --- |
| Gap down over 0.5% in uptrend, buy open | 1.5% | 9.9% | 3.4% | 0.4% |
| Prior day fell over 1%, buy open | 3.1% | 27.9% | 8.0% | 0.3% |
| Gap up over 0.5%, short (fade) | minus 5.6% | 48.1% | minus 11.3% | minus 1.9% |
| Gap up over 0.5%, buy (go) | 0.0% | 36.2% | 6.0% | minus 3.5% |

**Verdict:** every rule that worked in 2017 to 2020 faded to roughly zero in 2021 to 2026. None of them is good enough to trade.

### 4.3 Swing rules on the S&P 500 index (1990 to 2022)

| Strategy | Yearly | Worst drawdown | Sharpe | Time in market |
| --- | --- | --- | --- | --- |
| Buy and hold | 8.2% | 56.8% | 0.52 | 100% |
| 200 day trend filter | 6.1% | 28.8% | 0.57 | 74% |
| RSI(2) pullback | 3.9% | 15.0% | 0.66 | **11%** |

RSI(2) won 74% of its trades and was only in the market 11% of the time. That makes it a good use of idle cash, but its yearly return dropped from 5.5% (1990 to 2009) to 1.6% (2010 to 2022).

### 4.4 Portfolios of 20 large caps (1991 to 2022, 5 positions)

| Strategy | Yearly | Worst drawdown | Sharpe | 1991 to 2009 | 2010 to 2022 |
| --- | --- | --- | --- | --- | --- |
| Equal weight of all 20 (benchmark) | 18.4% | 48.4% | 0.99 | 20.2% | 15.9% |
| **Momentum top 5, monthly, with market filter** | **14.3%** | **25.3%** | 0.84 | 14.6% | 13.8% |
| Momentum top 5, no filter | 13.5% | 65.8% | 0.67 | 9.9% | 18.8% |
| 55 day breakout, with filter | 8.5% | 32.8% | 0.64 | 7.0% | 10.8% |
| RSI(2) pullback, with filter | 5.7% | 10.1% | 0.85 | 6.9% | 3.8% |

The momentum rotation with a filter was the most stable result in the whole study: almost the same return in both halves, and about half the drawdown of the benchmark.

### 4.5 Broad Nasdaq list (2018 to 2023)

Every strategy lost money here, with drawdowns of 40% to 80%, even after filtering for price above $20 and volatility under 40%. I checked this independently of the portfolio engine: across 6,900 RSI(2) signals the average trade made only +0.09% before costs, so the costs ate the edge. **Conclusion: stick to the most liquid large caps and ETFs.**

### 4.6 Recent check on ETFs (2017 to 2026)

| | Buy and hold | 200 day filter | RSI(2) pullback |
| --- | --- | --- | --- |
| QQQ yearly / worst drawdown | 19.7% / 35.6% | 17.1% / 21.9% | 5.4% / 8.8% (12% invested) |
| VTI yearly / worst drawdown | 12.6% / 35.0% | 8.2% / 19.4% | 3.7% / 13.6% (11% invested) |

The filter on QQQ kept most of the return and **had a better Sharpe ratio than buy and hold** (1.01 vs 0.89).

## 5. Plan that follows from the evidence

| Sleeve | Share of capital | Strategy | Why |
| --- | --- | --- | --- |
| Swing core | 60% | Momentum rotation, top 5 liquid large caps and sector ETFs, with market filter | Best long run evidence |
| Swing filler | 20% | RSI(2) pullbacks on SPY, QQQ, IWM with a trend filter | Uses idle cash, high win rate, low time in market |
| Day trading | 20% | 5 minute Opening Range Breakout on QQQ and SPY, strict stop, flat by the close | Most testable intraday idea, but unproven after costs, so kept small |

Crypto (BTC, ETH through Alpaca) is not in the starting plan. Alpaca charges roughly 0.15% to 0.25% per crypto trade, and I haven't been able to test crypto data yet. It can be added later as a trend filter sleeve (hold BTC only while it's above its 200 day average).

The playbooks are in `.claude/skills/swing-trader/SKILL.md`, `.claude/skills/day-trader/SKILL.md` and `.claude/skills/risk-manager/SKILL.md`.

## 6. About the one week paper test

One week is about 5 trading days. It's enough to prove the **plumbing** works: orders go through, stops get placed, logs get written and the schedule fires on time. It's **not** enough to prove an edge. The momentum sleeve only rebalances monthly, and the day sleeve will make at most 5 trades. A good or bad first week says almost nothing about the strategy. The real test is that every rule gets followed exactly, every day.

## 7. Still to do once Alpaca is connected

1. Download Alpaca minute bars for QQQ and SPY (2016 to now) and backtest the ORB rule with realistic spread and slippage. If it doesn't beat zero after costs, the day sleeve switches to the intraday momentum ("noise area") rule, or its capital moves to swing.
2. Rerun momentum on the exact live universe with Alpaca daily bars through 2026.
3. Test BTC and ETH trend rules with Alpaca crypto bars and fees.
