# Strategy scoreboard (PAPER challenge)

Updated 2026-10-09 16:30 ET. Backtest: 400 days of Alpaca bars (1100 for daily strategies), in sample before 2026-06-11, out of sample after (never tuned on). Per trade returns, unlevered, after costs. Live: Alpaca fills since the challenge started.

| Strategy | Period | Trades | Win rate | Avg win / avg loss | Profit (sum of trade returns) | Profit factor | Indicators |
| --- | --- | --- | --- | --- | --- | --- | --- |
| trend | backtest in sample | 2537 | 26% | +2.82% / -1.34% | -638.9% | 0.75 | EMA20, EMA50, ATR14 (1 hour bars) |
| trend | backtest out of sample | 1169 | 26% | +2.74% / -1.23% | -212.8% | 0.80 | EMA20, EMA50, ATR14 (1 hour bars) |
| rsi2 | backtest in sample | 1180 | 53% | +0.52% / -0.98% | -222.5% | 0.59 | RSI2, EMA200, EMA5, ATR14 (1 hour bars) |
| rsi2 | backtest out of sample | 585 | 50% | +0.49% / -0.85% | -101.8% | 0.59 | RSI2, EMA200, EMA5, ATR14 (1 hour bars) |
| orb | backtest in sample | 528 | 51% | +0.79% / -0.81% | +1.5% | 1.01 | 30 minute opening range (5 minute bars) |
| orb | backtest out of sample | 215 | 43% | +0.76% / -0.68% | -13.6% | 0.84 | 30 minute opening range (5 minute bars) |
| breakout | backtest in sample | 270 | 28% | +4.52% / -1.51% | +50.8% | 1.17 | 50 bar high, EMA200, EMA50, ATR14 (1 hour bars) |
| breakout | backtest out of sample | 129 | 31% | +3.16% / -1.46% | -3.7% | 0.97 | 50 bar high, EMA200, EMA50, ATR14 (1 hour bars) |
| overnight | backtest in sample | 1150 | 48% | +1.02% / -0.85% | +55.3% | 1.11 | SMA20 (daily bars) |
| overnight | backtest out of sample | 519 | 50% | +0.98% / -0.98% | +0.1% | 1.00 | SMA20 (daily bars) |
| ibs | backtest in sample | 859 | 65% | +2.66% / -3.06% | +550.1% | 1.59 | IBS = (close - low) / (high - low), SMA200, ATR14 (daily bars) |
| ibs | backtest out of sample | 172 | 56% | +2.91% / -2.94% | +55.5% | 1.25 | IBS = (close - low) / (high - low), SMA200, ATR14 (daily bars) |
| rsi2d | backtest in sample | 580 | 70% | +2.37% / -3.65% | +340.2% | 1.54 | RSI2, SMA200, SMA5, ATR14 (daily bars) |
| rsi2d | backtest out of sample | 104 | 76% | +2.03% / -1.87% | +113.6% | 3.42 | RSI2, SMA200, SMA5, ATR14 (daily bars) |
| reversal | backtest in sample | 1340 | 52% | +1.28% / -1.23% | +106.8% | 1.14 | 1 day return, ranked across the universe (daily bars) |
| reversal | backtest out of sample | 166 | 55% | +1.32% / -1.41% | +16.6% | 1.16 | 1 day return, ranked across the universe (daily bars) |
| bbdip | backtest in sample | 230 | 67% | +2.73% / -3.01% | +191.7% | 1.84 | SMA20, 20 day standard deviation (Bollinger 20, 2), SMA200, ATR14 (daily bars) |
| bbdip | backtest out of sample | 26 | 77% | +3.26% / -0.28% | +63.6% | 38.76 | SMA20, 20 day standard deviation (Bollinger 20, 2), SMA200, ATR14 (daily bars) |
| trend | live | 7 | 0% | +0.00% / -0.51% | -3.5% | 0.00 | realized P&L $-1,326 |
| rsi2 | live | 0 | | | | | realized P&L $0 |
| orb | live | 0 | | | | | realized P&L $0 |
| breakout | live | 2 | 0% | +0.00% / -0.94% | -1.9% | 0.00 | realized P&L $-1,162 |
| overnight | live | 4 | 0% | +0.00% / -0.76% | -3.1% | 0.00 | realized P&L $-266 |
| ibs | live | 0 | | | | | realized P&L $0 |
| rsi2d | live | 0 | | | | | realized P&L $0 |
| reversal | live | 3 | 67% | +2.20% / -1.47% | +2.9% | 2.98 | realized P&L $292 |
| bbdip | live | 0 | | | | | realized P&L $0 |
| opt | live | 0 | | | | | realized P&L $0 |

Allocation weights now: {'rsi2d': 0.4, 'bbdip': 0.3, 'ibs': 0.3, 'reversal': 0}

## Rules

* **trend**: 1 hour bars. Long when close > EMA20 > EMA50; short (stocks only) when close < EMA20 < EMA50. Stop 1.5 x ATR14 from entry, take profit 4 x ATR14. Exit early when the opposite condition appears.
* **rsi2**: 1 hour bars, long only. Buy when close > EMA200 and RSI(2) < 10. Stop 2 x ATR14 below entry. Sell when close > EMA5, or after 12 bars.
* **orb**: 5 minute bars, regular session, long only. Opening range = high and low of 09:30 to 10:00 ET. From 10:00 to 14:30 ET, the first 5 minute close above the range high is a buy, stop at the range low. One trade per symbol per day. Take profit at 2R. Close at 15:50 ET.
* **breakout**: 1 hour bars, stocks and ETFs, long only. Buy when the close is above the highest high of the previous 50 bars and above EMA200. Stop 3 x ATR14 below entry, no fixed target. Sell when a bar closes below EMA50.
* **overnight**: Daily. At about 15:55 ET buy the stocks and ETFs whose price is above their 20 day simple moving average (strongest first, as many as the slots allow). Sell at the next regular open (09:30 to 09:35 ET). Emergency stop 3% below entry.
* **ibs**: Daily, long only, near the close (about 15:55 ET). Buy when today's IBS is below 0.1 (close in the bottom 10% of the day's range) and the close is above the 200 day simple moving average. Stop 3 x ATR14 (daily) below entry. Sell near the close on the first day the close is above the previous day's high, or after 5 trading days.
* **rsi2d**: Daily, long only, near the close (about 15:55 ET). Buy when RSI(2) of the daily closes is below 10 and the close is above the 200 day simple moving average. Stop 3 x ATR14 (daily) below entry. Sell near the close on the first day the close is above the 5 day simple moving average, or after 10 trading days.
* **reversal**: Daily, near the close (about 15:55 ET): buy the 2 stocks or ETFs of the universe with the worst return since yesterday's close. Sell at the next regular open (09:30 to 09:35 ET). Emergency stop 3% below entry.
* **bbdip**: Daily, long only, near the close (about 15:55 ET). Buy when the close is below the lower Bollinger band (20 day SMA minus 2 x the 20 day standard deviation of closes) and above the 200 day simple moving average. Stop 3 x ATR14 (daily) below entry. Sell near the close on the first day the close is above the previous day's high, or after 5 trading days.
* **opt**: once a day between 09:35 and 11:00 ET, buy the QQQ call (first 5 minute bar up) or put (down), nearest expiry 1 to 4 days out, strike nearest the money. Exit at minus 50%, plus 100%, or 15:45 ET the day before expiry.
