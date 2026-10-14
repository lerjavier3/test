# Strategy scoreboard (PAPER challenge)

Updated 2026-10-14 16:20 ET. Backtest: 400 days of Alpaca bars (1100 for daily strategies), in sample before 2026-06-16, out of sample after (never tuned on). Per trade returns, unlevered, after costs. Live: Alpaca fills since the challenge started.

| Strategy | Period | Trades | Win rate | Avg win / avg loss | Profit (sum of trade returns) | Profit factor | Indicators |
| --- | --- | --- | --- | --- | --- | --- | --- |
| trend | backtest in sample | 2531 | 26% | +2.84% / -1.35% | -668.6% | 0.74 | EMA20, EMA50, ATR14 (1 hour bars) |
| trend | backtest out of sample | 1176 | 27% | +2.71% / -1.21% | -183.8% | 0.82 | EMA20, EMA50, ATR14 (1 hour bars) |
| rsi2 | backtest in sample | 1147 | 53% | +0.52% / -0.99% | -205.2% | 0.61 | RSI2, EMA200, EMA5, ATR14 (1 hour bars) |
| rsi2 | backtest out of sample | 585 | 51% | +0.50% / -0.84% | -96.3% | 0.60 | RSI2, EMA200, EMA5, ATR14 (1 hour bars) |
| orb | backtest in sample | 531 | 51% | +0.79% / -0.80% | +0.5% | 1.00 | 30 minute opening range (5 minute bars) |
| orb | backtest out of sample | 211 | 44% | +0.79% / -0.69% | -9.7% | 0.88 | 30 minute opening range (5 minute bars) |
| breakout | backtest in sample | 277 | 28% | +4.44% / -1.51% | +45.4% | 1.15 | 50 bar high, EMA200, EMA50, ATR14 (1 hour bars) |
| breakout | backtest out of sample | 126 | 32% | +3.12% / -1.47% | -1.1% | 0.99 | 50 bar high, EMA200, EMA50, ATR14 (1 hour bars) |
| overnight | backtest in sample | 1133 | 48% | +0.96% / -0.85% | +17.0% | 1.03 | SMA20 (daily bars) |
| overnight | backtest out of sample | 539 | 49% | +0.96% / -0.96% | -16.4% | 0.94 | SMA20 (daily bars) |
| ibs | backtest in sample | 851 | 65% | +2.67% / -3.08% | +533.3% | 1.57 | IBS = (close - low) / (high - low), SMA200, ATR14 (daily bars) |
| ibs | backtest out of sample | 177 | 56% | +2.87% / -3.05% | +52.5% | 1.22 | IBS = (close - low) / (high - low), SMA200, ATR14 (daily bars) |
| rsi2d | backtest in sample | 572 | 70% | +2.42% / -3.65% | +353.4% | 1.57 | RSI2, SMA200, SMA5, ATR14 (daily bars) |
| rsi2d | backtest out of sample | 107 | 74% | +2.03% / -2.71% | +84.7% | 2.12 | RSI2, SMA200, SMA5, ATR14 (daily bars) |
| reversal | backtest in sample | 1340 | 52% | +1.28% / -1.24% | +97.9% | 1.12 | 1 day return, ranked across the universe (daily bars) |
| reversal | backtest out of sample | 166 | 55% | +1.32% / -1.45% | +11.7% | 1.11 | 1 day return, ranked across the universe (daily bars) |
| bbdip | backtest in sample | 221 | 66% | +2.89% / -3.05% | +193.8% | 1.85 | SMA20, 20 day standard deviation (Bollinger 20, 2), SMA200, ATR14 (daily bars) |
| bbdip | backtest out of sample | 26 | 77% | +3.26% / -0.28% | +63.6% | 38.76 | SMA20, 20 day standard deviation (Bollinger 20, 2), SMA200, ATR14 (daily bars) |
| trend | live | 7 | 0% | +0.00% / -0.51% | -3.5% | 0.00 | realized P&L $-1,326 |
| rsi2 | live | 0 | | | | | realized P&L $0 |
| orb | live | 0 | | | | | realized P&L $0 |
| breakout | live | 2 | 0% | +0.00% / -0.94% | -1.9% | 0.00 | realized P&L $-1,162 |
| overnight | live | 4 | 0% | +0.00% / -0.76% | -3.1% | 0.00 | realized P&L $-266 |
| ibs | live | 2 | 100% | +4.41% / +0.00% | +8.8% | inf | realized P&L $852 |
| rsi2d | live | 1 | 100% | +1.53% / +0.00% | +1.5% | inf | realized P&L $70 |
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
