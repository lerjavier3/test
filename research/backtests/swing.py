"""Swing trading backtests on free daily data.

Usage: python3 research/backtests/swing.py <data_dir> <output_md>

Conventions
  * Signals are computed on the close of day t and filled at that same close
    (the bot is meant to run about 15 minutes before the close using live prices).
    A one day delayed fill is also reported as a robustness check.
  * Costs are charged per side as a fraction of the traded value.
  * No interest is earned on cash, no leverage, no shorting.
"""
import sys

import numpy as np
import pandas as pd

from common import load_close_panel, load_ohlcv, metrics, rsi, to_markdown, trade_stats

ETF_COST = 0.0002   # 2 bps per side for SPY/QQQ class ETFs
STOCK_COST = 0.001  # 10 bps per side for single stocks (spread plus slippage, conservative)


# ---------------------------------------------------------------- single asset

def stateful_position(entry, exit_, max_hold=None):
    """0/1 position decided at each close from entry/exit boolean series."""
    pos = np.zeros(len(entry))
    held, days = False, 0
    e, x = entry.values, exit_.values
    for i in range(len(e)):
        if held:
            days += 1
            if x[i] or (max_hold and days >= max_hold):
                held = False
        elif e[i]:
            held, days = True, 0
        pos[i] = 1.0 if held else 0.0
    return pd.Series(pos, index=entry.index)


def run_single(close, pos, cost, lag=0):
    """Daily returns of holding `pos` (decided at close t, earning return t+1)."""
    pos = pos.shift(lag).fillna(0)
    r = close.pct_change().fillna(0)
    held = pos.shift(1).fillna(0)
    turnover = pos.diff().abs().fillna(pos.abs())
    daily = held * r - turnover.shift(1).fillna(0) * cost
    trades, start = [], None
    p = pos.values
    for i in range(len(p)):
        if p[i] and start is None:
            start = i
        if start is not None and (not p[i] or i == len(p) - 1):
            end = i
            trades.append(close.iloc[end] / close.iloc[start] * (1 - cost) ** 2 - 1)
            start = None
    return daily, pos, trades


def index_tests(idx, label):
    rows = []
    sma200, sma5 = idx.rolling(200).mean(), idx.rolling(5).mean()
    r2 = rsi(idx, 2)
    warm = idx.index[200:]

    def add(name, pos, lag=0, cost=ETF_COST):
        d, p, t = run_single(idx, pos, cost, lag)
        d = d.loc[warm]
        for period, sl in (("full", slice(None)), ("1990-2009", slice(None, "2009")), ("2010-2022", slice("2010", None))):
            m = metrics(d.loc[sl], p.loc[warm].loc[sl])
            rows.append({"Strategy": name, "Period": period, **m, **(trade_stats(t) if period == "full" else {})})

    add("Buy and hold", pd.Series(1.0, index=idx.index))
    add("200d SMA trend filter", (idx > sma200).astype(float))
    rsi_pos = stateful_position((idx > sma200) & (r2 < 10), idx > sma5)
    add("RSI(2)<10 pullback, exit > 5d SMA", rsi_pos)
    add("RSI(2) pullback, filled 1 day late", rsi_pos, lag=1)
    rsi_pos5 = stateful_position((idx > sma200) & (r2 < 5), idx > sma5)
    add("RSI(2)<5 pullback (stricter)", rsi_pos5)
    return to_markdown(rows, f"{label}: single index tests")


# ---------------------------------------------------------------- portfolios

def run_portfolio(closes, entry, exit_, score, max_pos, cost, regime=None, max_hold=None, lag=0):
    """Equal slot portfolio: up to max_pos names, each bought with 1/max_pos of equity.

    entry/exit/score are DataFrames aligned to closes. Lower score = higher priority.
    """
    rets = closes.pct_change()
    dates = closes.index
    cash, hold = 1.0, {}  # hold: ticker -> [value, entry_index, entry_price]
    equity_curve, exposure, trades = [], [], []
    ent, ext, sc = entry.values, exit_.values, score.values
    reg = regime.reindex(dates).ffill().fillna(False).values if regime is not None else np.ones(len(dates), bool)
    cols = list(closes.columns)
    col_idx = {c: i for i, c in enumerate(cols)}
    rv = rets.values
    cv = closes.values
    for t in range(len(dates)):
        # mark to market
        for tk, h in hold.items():
            x = rv[t, col_idx[tk]]
            if not np.isnan(x):
                h[0] *= 1 + x
        s = t - lag
        if s >= 0:
            # exits
            for tk in list(hold):
                j = col_idx[tk]
                h = hold[tk]
                if ext[s, j] or np.isnan(cv[t, j]) or (max_hold and t - h[1] >= max_hold):
                    cash += h[0] * (1 - cost)
                    trades.append(cv[t - 1 if np.isnan(cv[t, j]) else t, j] / h[2] * (1 - cost) ** 2 - 1)
                    del hold[tk]
            # entries
            if reg[s] and len(hold) < max_pos:
                cand = np.where(ent[s] & ~np.isnan(cv[t]))[0]
                cand = [j for j in cand if cols[j] not in hold]
                cand.sort(key=lambda j: sc[s, j])
                equity = cash + sum(h[0] for h in hold.values())
                for j in cand[: max_pos - len(hold)]:
                    alloc = min(equity / max_pos, cash)
                    if alloc <= 0:
                        break
                    cash -= alloc
                    hold[cols[j]] = [alloc * (1 - cost), t, cv[t, j]]
        eq = cash + sum(h[0] for h in hold.values())
        equity_curve.append(eq)
        exposure.append(0 if eq <= 0 else sum(h[0] for h in hold.values()) / eq)
    eq = pd.Series(equity_curve, index=dates)
    return eq.pct_change().fillna(0), pd.Series(exposure, index=dates), trades


def run_rotation(closes, weights_fn, rebalance_dates, cost, regime=None):
    """Periodic rebalance into target weights; holdings drift between rebalances."""
    rets = closes.pct_change().fillna(0)
    vals = pd.Series(0.0, index=closes.columns)
    cash, out, expo = 1.0, [], []
    reb = set(rebalance_dates)
    for d in closes.index:
        vals *= 1 + rets.loc[d]
        if d in reb:
            equity = cash + vals.sum()
            w = weights_fn(d) if (regime is None or bool(regime.get(d, False))) else pd.Series(dtype=float)
            target = (w * equity).reindex(closes.columns).fillna(0)
            turnover = (target - vals).abs().sum()
            equity -= turnover * cost
            vals = target * (equity / max(target.sum(), 1e-12)) if target.sum() > 0 else target
            cash = equity - vals.sum()
        eq = cash + vals.sum()
        out.append(eq)
        expo.append(vals.sum() / eq if eq > 0 else 0)
    eq = pd.Series(out, index=closes.index)
    return eq.pct_change().fillna(0), pd.Series(expo, index=closes.index)


def portfolio_tests(closes, regime, label, start, cost=STOCK_COST, max_pos=5, splits=(), quality=None):
    rows = []
    sma200, sma5 = closes.rolling(200).mean(), closes.rolling(5).mean()
    r2 = rsi(closes, 2)
    mom126 = closes.pct_change(126)
    hi55 = closes.rolling(55).max().shift(1)
    lo20 = closes.rolling(20).min().shift(1)
    tradable = closes > 5
    if quality is not None:
        tradable &= quality

    def add(name, daily, expo, trades=None):
        daily, expo = daily.loc[start:], expo.loc[start:]
        periods = [("full", slice(None))] + [(f"{a} to {b}", slice(a, b)) for a, b in splits]
        for period, sl in periods:
            m = metrics(daily.loc[sl], expo.loc[sl])
            extra = trade_stats(trades) if (trades is not None and period == "full") else {}
            rows.append({"Strategy": name, "Period": period, **m, **extra})

    # benchmark: equal weight buy and hold of the whole universe, monthly rebalanced
    eq_bh = closes.pct_change().loc[start:].mean(axis=1).fillna(0)
    add("Equal weight universe (benchmark)", eq_bh, pd.Series(1.0, index=eq_bh.index))

    entry = (closes > sma200) & (r2 < 5) & tradable
    exit_ = closes > sma5
    for nm, reg, mh, lag in (
        ("RSI(2) pullback, 5 slots", None, None, 0),
        ("RSI(2) pullback + market filter", regime, None, 0),
        ("RSI(2) pullback + filter + 10d time stop", regime, 10, 0),
        ("RSI(2) pullback + filter, filled 1 day late", regime, None, 1),
    ):
        d, e, t = run_portfolio(closes, entry, exit_, r2, max_pos, cost, reg, mh, lag)
        add(nm, d, e, t)

    br_entry = (closes > hi55) & tradable
    br_exit = closes < lo20
    d, e, t = run_portfolio(closes, br_entry, br_exit, -mom126, max_pos, cost, regime)
    add("55d breakout / 20d low exit + filter", d, e, t)

    month_ends = closes.groupby(closes.index.to_period("M")).tail(1).index
    month_ends = month_ends[month_ends >= pd.Timestamp(start)]

    def top_mom(d, n=max_pos):
        m = mom126.loc[d]
        m = m[(closes.loc[d] > sma200.loc[d]) & tradable.loc[d]].dropna()
        top = m.nlargest(n).index
        return pd.Series(1.0 / n, index=top) if len(top) else pd.Series(dtype=float)

    d, e = run_rotation(closes, top_mom, month_ends, cost)
    add("Momentum top 5 (6m), monthly, no filter", d, e)
    d, e = run_rotation(closes, top_mom, month_ends, cost, regime)
    add("Momentum top 5 (6m), monthly + filter", d, e)
    return to_markdown(rows, f"{label}: portfolio tests ({max_pos} slots, {cost*1e4:.0f} bps per side)")


def main(data_dir, out_md):
    sections = ["# Swing trading backtest results", "",
                "Generated by `research/backtests/swing.py`. See `research/RESEARCH.md` for interpretation.", ""]

    idx = load_close_panel(f"{data_dir}/sp500_index.csv.gz")["SP500"].dropna()
    sections.append(index_tests(idx, "S&P 500 index 1990 to 2022"))

    sp_reg = idx > idx.rolling(200).mean()
    large = load_close_panel(f"{data_dir}/sp500_dataset.csv.gz")
    sections.append(portfolio_tests(large, sp_reg, "20 S&P 500 large caps 1990 to 2022", "1991-01-01",
                                    cost=0.0005, splits=(("1991", "2009"), ("2010", "2022"))))

    qqq = load_ohlcv(data_dir, "qqq")["close"]
    q_reg = qqq > qqq.rolling(200).mean()
    nas = load_close_panel(f"{data_dir}/nasdaq_dataset.csv.gz")
    nas = nas.loc[:, nas.notna().mean() > 0.9]
    sections.append(portfolio_tests(nas, q_reg, f"{nas.shape[1]} Nasdaq stocks 2018 to 2023", "2018-11-01",
                                    splits=(("2018-11", "2020-12"), ("2021", "2023"))))

    # Same universe, but only names a live bot could size sensibly: price above $20 and
    # 100 day annualised volatility under 40% (a rough stand in for "liquid large cap").
    vol100 = nas.pct_change().rolling(100).std() * np.sqrt(252)
    quality = (nas > 20) & (vol100 < 0.40)
    sections.append(portfolio_tests(nas, q_reg, "Nasdaq stocks 2018 to 2023, quality filter (price > $20, vol < 40%)",
                                    "2018-11-01", splits=(("2018-11", "2020-12"), ("2021", "2023")), quality=quality))

    with open(out_md, "w") as f:
        f.write("\n".join(sections))
    print("\n".join(sections))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
