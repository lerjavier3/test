# Daily reviews and strategy changes (PAPER challenge)

## 2026-10-06 (08:30 ET, user request)

* Equity $99,990 (Alpaca), holding SPY 77 and AVGO 164 from the 08:26 ET breakout entries.
* Change: entries now also take trend signals (close and EMA20 on the same side of EMA50), not only 20 bar breakouts. Breakouts still go first, then the strongest trends, up to 6 positions.
* Why: the user asked for the account to hold positions and be used actively; breakout only entries left it in cash most of the time.
* Unchanged: stops, $25,000 floor, paper guard, leverage caps.

## 2026-10-06 (10:10 ET, user request)

* Change: the $25,000 equity floor is removed (`equity_floor` set to 0 in `trading/state.json`). The user accepted that Alpaca may restrict the account if equity drops low.
* Unchanged: paper only guard, a stop on every position, buy only options, unique order ids, 1.9x overnight cap, end at 04:30 ET on 2026-10-13.

## 2026-10-06 (10:20 ET, user request)

* Change: goal raised to 5x minimum ($500,000, no upper limit). Deadline moved to 2026-10-20 18:00 SGT. Last stock session 2026-10-19 (stocks and options close at 15:50 ET); crypto runs until 04:30 ET on 2026-10-20 (16:30 SGT), then everything is closed and the final report written.
* Updated: `trading/state.json` (target_equity, target_date, stocks_end_et, end_after_et), summary labels and history window in the scripts, tests, RUNNER.md, skill and README.

## 2026-10-06 (10:55 ET, user request: multiple strategies)

* Equity $101,703 (Alpaca).
* Built: shared strategy definitions (`scripts/strategies.py`), a backtester on 400 days of Alpaca bars with the last 120 days out of sample (`scripts/strategy_backtest.py`), a variant search (`scripts/strategy_search.py`) and `trading/journal/strategy-scoreboard.md`.
* Tested: the live hourly trend strategy loses after costs (profit factor 0.74 in sample, 0.82 out of sample, 27% win rate), RSI(2) pullbacks lose (0.60 / 0.58, average loss bigger than average win), 15 minute ORB about breakeven (0.90 / 0.96). Variant search: hourly breakouts on stocks only (50 bar high, 3 ATR stop, exit below EMA50) 1.15 / 0.97; overnight hold of stocks above their 20 day average 1.11 / 1.03; 30 minute ORB longs 1.00 / 0.88; daily IBS had too few trades in 400 days to judge.
* Change: live weights breakout 0.4, overnight 0.4, orb (30 minute, long only) 0.2. Trend and rsi2 get weight 0: no new trades, their open positions are still managed by their exit rules. No strategy is clearly profitable out of sample yet, so the search continues every day.

## 2026-10-06 (11:08 ET, user request: safeguards and playbook)

* Every stock position now gets a real GTC stop order at the broker as a backup (placed last in each tick, so nothing closed in the same tick gets one); closing a position cancels its orders from a fresh Alpaca list.
* Earnings: no stock is held overnight into its report. Dates in `trading/earnings.json` (from a web search, not all confirmed): none of the traded stocks reports before 2026-10-20; TSLA is expected 2026-10-21.
* Weekend crypto cash reserve (`crypto_reserve`, now 0 because no crypto strategy is working yet).
* `trading/PLAYBOOK.md` created; no strategy qualifies yet.

## 2026-10-06 (daily review, 16:30 ET)

* Alpaca equity $100,195.68 (previous close $100,000): day +$195.68 (+0.2%), total +0.2%. Open: SPY 77, AVGO 164 (trend, before the change), GOOGL 171, META 11, AMZN 2 (overnight).
* Closed today (Alpaca fills, one entry per order): trend 5 (IWM, TSLA, QQQ, BTC, ETH), all losses, $-481; breakout 2 (NVDA, AMD), both losses, $-1,162; overnight 1 (MSFT), loss, $-98. Too few trades to judge any strategy.
* Fixed: the scoreboard counted every partial fill as a trade (35 "trades" instead of 8); fills are now merged per order.
* Fixed: churn at the overnight limit. MSFT was bought at 15:53 up to 1.9x, a small move put gross just above 1.9x and the 15:58 trim sold it at a loss. Late and overnight entries now stop at 1.8x, while the trim stays at 1.9x.
* No weight change (breakout 0.4, overnight 0.4, orb 0.2). Backtests unchanged: no strategy is profitable in both periods with margin to spare; the search continues.
* Earnings: no traded stock reports within 7 days (TSLA expected 2026-10-21).

## 2026-10-07 (02:53 ET, user request: wider search)

* Tested (scripts/strategy_ideas.py, 400 days of 5 minute bars or 1100 days of daily bars, last 120 days out of sample): intraday momentum (first 30 minutes predicting the last 30) loses (profit factor 0.59 to 0.66 in sample); gap fade and gap and go lose or are flat in sample (0.78 to 0.96); NR7 breakouts lose (0.65 to 0.80). Cross-sectional reversal (buy the worst 1 day stock at the close, sell at the next open) 1.11 in sample, 1.34 out of sample, 60% wins out of sample. IBS < 0.1 above SMA200: ETFs 2.98 / 2.78 (68% / 65% wins, average win bigger than average loss), stocks 1.83 / 1.63 (65% / 62%). With a 3 ATR stop added (required on every trade) IBS on all 12 symbols: 1.80 in sample, 62% wins out of sample. Crypto daily trend above SMA50: 1.92 / 9.42 but only 9 out of sample trades, too few; kept as a candidate.
* Change: new live weights ibs 0.5, reversal 0.25, overnight 0.25. Breakout (0.96 out of sample) and orb (0.88) go to weight 0; their open positions are still managed by their exit rules.

## 2026-10-07 (10:57 ET, user request: more trades)

* Change: the daily strategies now trade a wider liquid universe of 38 symbols (the 12 before plus sector ETFs and large caps) instead of 12. Left out until after the challenge: JPM, BAC, UNH, NFLX, PEP, KO, XOM, CVX (earnings may fall before 2026-10-20 or dates unclear).
* Backtests on the 38 symbols (1100 days, last 120 out of sample): IBS 866 trades in sample, 64% wins, profit factor 1.55; out of sample 176 trades (about 4 times more than on 12 symbols), 56% wins, average win +2.91% vs loss -2.79%, profit factor 1.34. Reversal with the 2 worst stocks a day: 1.14 / 1.10 (54% wins out of sample); 3 worst was flat out of sample (0.99). Overnight on the wide universe loses (0.99 / 0.92), so it is retired.
* Weights: ibs 0.6, reversal 0.4. Limits raised to 6 positions per strategy and 12 in total; leverage caps unchanged.

## 2026-10-07 (11:05 ET, more ideas tested)

* Daily ideas on the 38 symbol universe (1100 days, last 120 out of sample, 3 ATR stop): daily RSI(2) < 10 above SMA200, exit close above SMA5: 70% wins, profit factor 1.60 in sample; 78% wins, 2.90 out of sample (105 trades; average loss bigger than average win, profitable through the win rate). RSI(2) < 5: 1.54 / 7.06 (52 trades). IBS < 0.1 with RSI(2) < 20: 1.71 / 2.11. Three lower closes: 1.26 / 2.87. Down 3% day: 1.28 / 1.64. IBS < 0.2: 1.30 / 1.32.
* Change: daily RSI(2) < 10 (rsi2d) goes live. Weights rsi2d 0.4, ibs 0.35, reversal 0.25. One position per symbol, so overlapping signals never double up.

## 2026-10-07 (daily review, 16:30 ET)

* Alpaca equity $99,861.92 (previous close $99,975.90): day -$113.98 (-0.1%), total -0.1%. Open: AVGO 164 (trend, from 2026-10-06), QCOM 133 (rsi2d), META 37 (ibs), COIN 252 (reversal), all entered 15:52 ET.
* Fixed: the reversal strategy bought only 1 of its 2 picks because the first used its whole capital share; each pick now gets half of the share.
* Tested on the 38 symbols (1100 days, last 120 out of sample): RSI(2) < 10 exiting at RSI(2) > 70: 1.56 / 3.29; Williams %R(2) oversold: 1.47 / 1.78; close below the 5 day low: 1.43 / 2.05. All profitable out of sample, none beats the live rsi2d in sample (1.60). No weight change.

## 2026-10-08 (07:00 ET, user request: be bolder)

* Alpaca equity $97,869.73 before the open (previous close $99,900.36).
* Change: risk per trade raised from 2.5% to 4% of equity at equal weights (scaled by each strategy's weight). Position caps (1.0x intraday, 0.6x late and overnight), the 3.5x / 1.8x gross caps, stops and one position per symbol are unchanged.

## 2026-10-08 (07:20 ET, user request: size up on near perfect setups)

* Tested A+ setups on the 38 symbols (1100 days, last 120 out of sample): RSI(2) < 5 and IBS < 0.15 above SMA200: 144 trades in sample, 69% wins, average win +2.71% vs loss -2.85%, profit factor 2.16 (RSI(2) < 10 alone: 1.55); out of sample 26 trades, 92% wins, 14.25. Stricter RSI(2) < 3 and IBS < 0.1 was worse in sample (1.37).
* Change: rsi2d and ibs entries that are also A+ get double risk (8% of equity) and may use up to 1x equity in one position, beyond the strategy's share, within the combined 1.8x overnight / 3.5x intraday caps. Stops unchanged.

## 2026-10-08 (07:35 ET, user request: risk up to 10% on the best setups)

* Change: A+ setups (RSI(2) < 5 and IBS < 0.15, above SMA200) now risk 10% of equity (was 8%), up to 1x equity in one position. Normal setups stay at 4%. Combined caps and stops unchanged. The search for new setups continues in every daily review.

## 2026-10-08 (daily review, 16:30 ET)

* Alpaca equity $96,885 (−3.1% since start). Today: COIN reversal sold at the open (−$660). Near the close the bot bought SMH (rsi2d), NVDA (ibs), ORCL and INTC (reversal); AVGO and META still held. 6 positions, 1.79x.
* Tested (new families in `scripts/strategy_ideas.py`, wide universe, 1100 days, in sample vs last 120 days):
  * Down streak (n lower closes, above SMA200): n5 PF 2.25 / 12.9 (only 23 trades out of sample), n3 PF 1.30 / 2.87.
  * Bollinger dip (close below SMA20 minus k standard deviations, above SMA200): 2.0sd PF 1.82 / 42.0 (79% wins out of sample), 1.5sd PF 1.32 / 5.97, 2.5sd PF 2.71 / all 10 out of sample trades won.
  * Cross-sectional reversal limited to symbols above SMA200: k2 PF 1.19 / 1.08, no better than the live reversal.
* Change: promoted `bbdip` (Bollinger 20, 2 dip above SMA200, IBS style exit, stop 3 ATR). Official backtest with stops: 228 trades in sample, 66% wins, PF 1.73; 28 trades out of sample, 79% wins, avg +3.21% vs −0.28%, PF 42. It beats ibs (1.60 / 1.29) and reversal (1.13 / 1.14) in both periods. Weights now rsi2d 0.4, bbdip 0.3, ibs 0.3, reversal 0 (it still sells ORCL and INTC at the next open). A+ sizing now also applies to bbdip signals. Tests pass.
* Earnings: nothing within 7 days for held or universe stocks.
