# Strategy scoreboard (PAPER challenge)

Updated 2026-10-08 16:24 ET. Backtest: 400 days of Alpaca bars (1100 for daily strategies), in sample before 2026-06-10, out of sample after (never tuned on). Per trade returns, unlevered, after costs. Live: Alpaca fills since the challenge started.

| Strategy | Period | Trades | Win rate | Avg win / avg loss | Profit (sum of trade returns) | Profit factor | Indicators |
| --- | --- | --- | --- | --- | --- | --- | --- |
| trend | backtest in sample | 2538 | 26% | +2.82% / -1.33% | -630.6% | 0.75 | EMA20, EMA50, ATR14 (1 hour bars) |
| trend | backtest out of sample | 1168 | 27% | +2.75% / -1.24% | -205.7% | 0.81 | EMA20, EMA50, ATR14 (1 hour bars) |
| rsi2 | backtest in sample | 1182 | 53% | +0.52% / -0.98% | -223.1% | 0.59 | RSI2, EMA200, EMA5, ATR14 (1 hour bars) |
| rsi2 | backtest out of sample | 577 | 50% | +0.49% / -0.85% | -106.1% | 0.57 | RSI2, EMA200, EMA5, ATR14 (1 hour bars) |
| orb | backtest in sample | 527 | 51% | +0.78% / -0.81% | +0.9% | 1.00 | 30 minute opening range (5 minute bars) |
| orb | backtest out of sample | 218 | 43% | +0.78% / -0.69% | -11.6% | 0.86 | 30 minute opening range (5 minute bars) |
| breakout | backtest in sample | 276 | 28% | +4.47% / -1.51% | +44.2% | 1.15 | 50 bar high, EMA200, EMA50, ATR14 (1 hour bars) |
| breakout | backtest out of sample | 128 | 31% | +3.16% / -1.46% | -2.4% | 0.98 | 50 bar high, EMA200, EMA50, ATR14 (1 hour bars) |
| overnight | backtest in sample | 1159 | 48% | +1.01% / -0.85% | +56.6% | 1.11 | SMA20 (daily bars) |
| overnight | backtest out of sample | 508 | 49% | +0.99% / -0.97% | -6.9% | 0.97 | SMA20 (daily bars) |
| ibs | backtest in sample | 862 | 65% | +2.61% / -3.00% | +544.3% | 1.60 | IBS = (close - low) / (high - low), SMA200, ATR14 (daily bars) |
| ibs | backtest out of sample | 177 | 56% | +2.89% / -2.90% | +65.6% | 1.29 | IBS = (close - low) / (high - low), SMA200, ATR14 (daily bars) |
| rsi2d | backtest in sample | 584 | 70% | +2.37% / -3.63% | +347.5% | 1.55 | RSI2, SMA200, SMA5, ATR14 (daily bars) |
| rsi2d | backtest out of sample | 104 | 77% | +2.03% / -1.82% | +118.4% | 3.71 | RSI2, SMA200, SMA5, ATR14 (daily bars) |
| reversal | backtest in sample | 1340 | 52% | +1.28% / -1.23% | +105.5% | 1.13 | 1 day return, ranked across the universe (daily bars) |
| reversal | backtest out of sample | 166 | 55% | +1.31% / -1.40% | +14.4% | 1.14 | 1 day return, ranked across the universe (daily bars) |
| bbdip | backtest in sample | 228 | 66% | +2.69% / -2.99% | +170.3% | 1.73 | SMA20, 20 day standard deviation (Bollinger 20, 2), SMA200, ATR14 (daily bars) |
| bbdip | backtest out of sample | 28 | 79% | +3.21% / -0.28% | +69.0% | 42.02 | SMA20, 20 day standard deviation (Bollinger 20, 2), SMA200, ATR14 (daily bars) |
| trend | live | 7 | 0% | +0.00% / -0.51% | -3.5% | 0.00 | realized P&L $-1,326 |
| rsi2 | live | 0 | | | | | realized P&L $0 |
| orb | live | 0 | | | | | realized P&L $0 |
| breakout | live | 2 | 0% | +0.00% / -0.94% | -1.9% | 0.00 | realized P&L $-1,162 |
| overnight | live | 4 | 0% | +0.00% / -0.76% | -3.1% | 0.00 | realized P&L $-266 |
| ibs | live | 0 | | | | | realized P&L $0 |
| rsi2d | live | 0 | | | | | realized P&L $0 |
| reversal | live | 1 | 0% | +0.00% / -1.47% | -1.5% | 0.00 | realized P&L $-660 |
| bbdip | live | 0 | | | | | realized P&L $0 |
| opt | live | 0 | | | | | realized P&L $0 |

Allocation weights now: {'rsi2d': 0.4, 'ibs': 0.35, 'reversal': 0.25}

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
