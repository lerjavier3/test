# Strategy scoreboard (PAPER challenge)

Updated 2026-10-06 16:24 ET. Backtest: 400 days of Alpaca bars, in sample before 2026-06-08, out of sample after (never tuned on). Per trade returns, unlevered, after costs. Live: Alpaca fills since the challenge started.

| Strategy | Period | Trades | Win rate | Avg win / avg loss | Profit (sum of trade returns) | Profit factor | Indicators |
| --- | --- | --- | --- | --- | --- | --- | --- |
| trend | backtest in sample | 2534 | 26% | +2.81% / -1.33% | -641.3% | 0.74 | EMA20, EMA50, ATR14 (1 hour bars) |
| trend | backtest out of sample | 1163 | 27% | +2.79% / -1.26% | -195.0% | 0.82 | EMA20, EMA50, ATR14 (1 hour bars) |
| rsi2 | backtest in sample | 1198 | 53% | +0.52% / -0.97% | -222.7% | 0.60 | RSI2, EMA200, EMA5, ATR14 (1 hour bars) |
| rsi2 | backtest out of sample | 552 | 50% | +0.50% / -0.86% | -99.7% | 0.58 | RSI2, EMA200, EMA5, ATR14 (1 hour bars) |
| orb | backtest in sample | 532 | 51% | +0.78% / -0.80% | -0.2% | 1.00 | 30 minute opening range (5 minute bars) |
| orb | backtest out of sample | 210 | 44% | +0.79% / -0.70% | -9.8% | 0.88 | 30 minute opening range (5 minute bars) |
| breakout | backtest in sample | 278 | 28% | +4.46% / -1.51% | +45.9% | 1.15 | 50 bar high, EMA200, EMA50, ATR14 (1 hour bars) |
| breakout | backtest out of sample | 117 | 28% | +3.66% / -1.49% | -4.9% | 0.96 | 50 bar high, EMA200, EMA50, ATR14 (1 hour bars) |
| overnight | backtest in sample | 1174 | 48% | +1.01% / -0.85% | +57.4% | 1.11 | SMA20 (daily bars) |
| overnight | backtest out of sample | 488 | 50% | +1.00% / -0.99% | +7.0% | 1.03 | SMA20 (daily bars) |
| trend | live | 5 | 0% | +0.00% / -0.43% | -2.1% | 0.00 | realized P&L $-481 |
| rsi2 | live | 0 | | | | | realized P&L $0 |
| orb | live | 0 | | | | | realized P&L $0 |
| breakout | live | 2 | 0% | +0.00% / -0.94% | -1.9% | 0.00 | realized P&L $-1,162 |
| overnight | live | 1 | 0% | +0.00% / -0.16% | -0.2% | 0.00 | realized P&L $-98 |
| opt | live | 0 | | | | | realized P&L $0 |

Allocation weights now: {'breakout': 0.4, 'overnight': 0.4, 'orb': 0.2}

## Rules

* **trend**: 1 hour bars. Long when close > EMA20 > EMA50; short (stocks only) when close < EMA20 < EMA50. Stop 1.5 x ATR14 from entry, take profit 4 x ATR14. Exit early when the opposite condition appears.
* **rsi2**: 1 hour bars, long only. Buy when close > EMA200 and RSI(2) < 10. Stop 2 x ATR14 below entry. Sell when close > EMA5, or after 12 bars.
* **orb**: 5 minute bars, regular session, long only. Opening range = high and low of 09:30 to 10:00 ET. From 10:00 to 14:30 ET, the first 5 minute close above the range high is a buy, stop at the range low. One trade per symbol per day. Take profit at 2R. Close at 15:50 ET.
* **breakout**: 1 hour bars, stocks and ETFs, long only. Buy when the close is above the highest high of the previous 50 bars and above EMA200. Stop 3 x ATR14 below entry, no fixed target. Sell when a bar closes below EMA50.
* **overnight**: Daily. At about 15:55 ET buy the stocks and ETFs whose price is above their 20 day simple moving average (strongest first, as many as the slots allow). Sell at the next regular open (09:30 to 09:35 ET). Emergency stop 3% below entry.
* **opt**: once a day between 09:35 and 11:00 ET, buy the QQQ call (first 5 minute bar up) or put (down), nearest expiry 1 to 4 days out, strike nearest the money. Exit at minus 50%, plus 100%, or 15:45 ET the day before expiry.
