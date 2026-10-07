# Strategy scoreboard (PAPER challenge)

Updated 2026-10-07 10:59 ET. Backtest: 400 days of Alpaca bars (1100 for daily strategies), in sample before 2026-06-09, out of sample after (never tuned on). Per trade returns, unlevered, after costs. Live: Alpaca fills since the challenge started.

| Strategy | Period | Trades | Win rate | Avg win / avg loss | Profit (sum of trade returns) | Profit factor | Indicators |
| --- | --- | --- | --- | --- | --- | --- | --- |
| rsi2d | backtest in sample | 582 | 70% | +2.37% / -3.54% | +363.8% | 1.60 | RSI2, SMA200, SMA5, ATR14 (daily bars) |
| rsi2d | backtest out of sample | 105 | 78% | +2.02% / -2.49% | +108.9% | 2.90 | RSI2, SMA200, SMA5, ATR14 (daily bars) |
| ibs | backtest in sample | 866 | 64% | +2.61% / -3.03% | +514.6% | 1.55 | IBS = (close - low) / (high - low), SMA200, ATR14 (daily bars) |
| ibs | backtest out of sample | 176 | 56% | +2.91% / -2.78% | +73.8% | 1.34 | IBS = (close - low) / (high - low), SMA200, ATR14 (daily bars) |
| trend | live | 6 | 0% | +0.00% / -0.40% | -2.4% | 0.00 | realized P&L $-650 |
| rsi2 | live | 0 | | | | | realized P&L $0 |
| orb | live | 0 | | | | | realized P&L $0 |
| breakout | live | 2 | 0% | +0.00% / -0.94% | -1.9% | 0.00 | realized P&L $-1,162 |
| overnight | live | 4 | 0% | +0.00% / -0.76% | -3.1% | 0.00 | realized P&L $-266 |
| ibs | live | 0 | | | | | realized P&L $0 |
| rsi2d | live | 0 | | | | | realized P&L $0 |
| reversal | live | 0 | | | | | realized P&L $0 |
| opt | live | 0 | | | | | realized P&L $0 |

Allocation weights now: {'ibs': 0.6, 'reversal': 0.4}

## Rules

* **trend**: 1 hour bars. Long when close > EMA20 > EMA50; short (stocks only) when close < EMA20 < EMA50. Stop 1.5 x ATR14 from entry, take profit 4 x ATR14. Exit early when the opposite condition appears.
* **rsi2**: 1 hour bars, long only. Buy when close > EMA200 and RSI(2) < 10. Stop 2 x ATR14 below entry. Sell when close > EMA5, or after 12 bars.
* **orb**: 5 minute bars, regular session, long only. Opening range = high and low of 09:30 to 10:00 ET. From 10:00 to 14:30 ET, the first 5 minute close above the range high is a buy, stop at the range low. One trade per symbol per day. Take profit at 2R. Close at 15:50 ET.
* **breakout**: 1 hour bars, stocks and ETFs, long only. Buy when the close is above the highest high of the previous 50 bars and above EMA200. Stop 3 x ATR14 below entry, no fixed target. Sell when a bar closes below EMA50.
* **overnight**: Daily. At about 15:55 ET buy the stocks and ETFs whose price is above their 20 day simple moving average (strongest first, as many as the slots allow). Sell at the next regular open (09:30 to 09:35 ET). Emergency stop 3% below entry.
* **ibs**: Daily, long only, near the close (about 15:55 ET). Buy when today's IBS is below 0.1 (close in the bottom 10% of the day's range) and the close is above the 200 day simple moving average. Stop 3 x ATR14 (daily) below entry. Sell near the close on the first day the close is above the previous day's high, or after 5 trading days.
* **rsi2d**: Daily, long only, near the close (about 15:55 ET). Buy when RSI(2) of the daily closes is below 10 and the close is above the 200 day simple moving average. Stop 3 x ATR14 (daily) below entry. Sell near the close on the first day the close is above the 5 day simple moving average, or after 10 trading days.
* **reversal**: Daily, near the close (about 15:55 ET): buy the 2 stocks or ETFs of the universe with the worst return since yesterday's close. Sell at the next regular open (09:30 to 09:35 ET). Emergency stop 3% below entry.
* **opt**: once a day between 09:35 and 11:00 ET, buy the QQQ call (first 5 minute bar up) or put (down), nearest expiry 1 to 4 days out, strike nearest the money. Exit at minus 50%, plus 100%, or 15:45 ET the day before expiry.
