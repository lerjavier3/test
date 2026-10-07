# Strategy scoreboard (PAPER challenge)

Updated 2026-10-07 02:51 ET. Backtest: 400 days of Alpaca bars (1100 for daily strategies), in sample before 2026-06-09, out of sample after (never tuned on). Per trade returns, unlevered, after costs. Live: Alpaca fills since the challenge started.

| Strategy | Period | Trades | Win rate | Avg win / avg loss | Profit (sum of trade returns) | Profit factor | Indicators |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ibs | backtest in sample | 284 | 65% | +2.94% / -3.01% | +241.0% | 1.80 | IBS = (close - low) / (high - low), SMA200, ATR14 (daily bars) |
| ibs | backtest out of sample | 60 | 62% | +2.48% / -2.53% | +33.7% | 1.58 | IBS = (close - low) / (high - low), SMA200, ATR14 (daily bars) |
| reversal | backtest in sample | 670 | 52% | +1.21% / -1.16% | +41.2% | 1.11 | 1 day return, ranked across the universe (daily bars) |
| reversal | backtest out of sample | 82 | 60% | +1.18% / -1.31% | +14.7% | 1.34 | 1 day return, ranked across the universe (daily bars) |
| trend | live | 5 | 0% | +0.00% / -0.43% | -2.1% | 0.00 | realized P&L $-481 |
| rsi2 | live | 0 | | | | | realized P&L $0 |
| orb | live | 0 | | | | | realized P&L $0 |
| breakout | live | 2 | 0% | +0.00% / -0.94% | -1.9% | 0.00 | realized P&L $-1,162 |
| overnight | live | 1 | 0% | +0.00% / -0.16% | -0.2% | 0.00 | realized P&L $-98 |
| ibs | live | 0 | | | | | realized P&L $0 |
| reversal | live | 0 | | | | | realized P&L $0 |
| opt | live | 0 | | | | | realized P&L $0 |

Allocation weights now: {'breakout': 0.4, 'overnight': 0.4, 'orb': 0.2}

## Rules

* **trend**: 1 hour bars. Long when close > EMA20 > EMA50; short (stocks only) when close < EMA20 < EMA50. Stop 1.5 x ATR14 from entry, take profit 4 x ATR14. Exit early when the opposite condition appears.
* **rsi2**: 1 hour bars, long only. Buy when close > EMA200 and RSI(2) < 10. Stop 2 x ATR14 below entry. Sell when close > EMA5, or after 12 bars.
* **orb**: 5 minute bars, regular session, long only. Opening range = high and low of 09:30 to 10:00 ET. From 10:00 to 14:30 ET, the first 5 minute close above the range high is a buy, stop at the range low. One trade per symbol per day. Take profit at 2R. Close at 15:50 ET.
* **breakout**: 1 hour bars, stocks and ETFs, long only. Buy when the close is above the highest high of the previous 50 bars and above EMA200. Stop 3 x ATR14 below entry, no fixed target. Sell when a bar closes below EMA50.
* **overnight**: Daily. At about 15:55 ET buy the stocks and ETFs whose price is above their 20 day simple moving average (strongest first, as many as the slots allow). Sell at the next regular open (09:30 to 09:35 ET). Emergency stop 3% below entry.
* **ibs**: Daily, long only, near the close (about 15:55 ET). Buy when today's IBS is below 0.1 (close in the bottom 10% of the day's range) and the close is above the 200 day simple moving average. Stop 3 x ATR14 (daily) below entry. Sell near the close on the first day the close is above the previous day's high, or after 5 trading days.
* **reversal**: Daily, near the close (about 15:55 ET): buy the one stock or ETF of the universe with the worst return since yesterday's close. Sell at the next regular open (09:30 to 09:35 ET). Emergency stop 3% below entry.
* **opt**: once a day between 09:35 and 11:00 ET, buy the QQQ call (first 5 minute bar up) or put (down), nearest expiry 1 to 4 days out, strike nearest the money. Exit at minus 50%, plus 100%, or 15:45 ET the day before expiry.
