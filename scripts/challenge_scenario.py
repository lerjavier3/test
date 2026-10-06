"""Dry run one challenge_run tick under a forced session, time and fake positions (no orders).

  python3 scripts/challenge_scenario.py <session> <HH:MM> [YYYY-MM-DD] [--pos]
"""
import sys, datetime, json
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import challenge as ch, challenge_run as cr
real_get = ch.get
FAKE = {}
def fake_get(path, params=None, base=ch.API):
    if path in FAKE: return FAKE[path](params)
    return real_get(path, params, base)
ch.get = fake_get
ch.save_state = lambda s: None
sess = sys.argv[1]; hhmm = sys.argv[2]
ch.session_now = lambda clock: sess
ET = ch.ET
h, m = map(int, hhmm.split(':'))
D = [int(x) for x in (sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith("--") else "2026-10-07").split("-")]
# Real bars fetched before the clock is faked; forced signals: trend long NVDA, trend short TSLA,
# overnight AAPL and MSFT, orb long QQQ.
import strategies as S
DATA = cr.market_data("regular")
for tf in DATA.values():
    for sym, d in tf.items():
        for ind in d["ind"].values():
            ind["sym"] = sym
cr.market_data = lambda session: DATA
FORCED = {("breakout", "NVDA"): "long", ("orb", "QQQ"): "long", ("overnight", "AAPL"): "long",
          ("overnight", "MSFT"): "long", ("trend", "TSLA"): "short"}  # trend has weight 0: must not trade
def forced(name):
    def entry(ind, bars, i):
        side = FORCED.get((name, ind.get("sym")))
        return (side, bars[i]["c"] * (0.98 if side == "long" else 1.02), 2.0) if side else None
    return entry
for n in S.ALL:
    S.ALL[n].entry = forced(n)
now = datetime.datetime(*D, h, m, tzinfo=ET)
class FakeDT(datetime.datetime):
    @classmethod
    def now(cls, tz=None): return now if tz else now.replace(tzinfo=None)
cr.datetime.datetime = FakeDT
FAKE['/v2/stocks/QQQ/bars'] = lambda p: {"bars": [{"o": 750, "c": 752}]}
pos = []
if '--pos' in sys.argv:
    pos = [
     {"symbol":"AMD","asset_class":"us_equity","qty":"100","current_price":"600","market_value":"60000","avg_entry_price":"620","unrealized_plpc":"-0.03"},
     {"symbol":"ETHUSD","asset_class":"crypto","qty":"2","current_price":"2700","market_value":"5400","avg_entry_price":"2600","unrealized_plpc":"0.04"},
     {"symbol":"QQQ261009C00756000","asset_class":"us_option","qty":"10","current_price":"3.0","market_value":"3000","avg_entry_price":"7.0","unrealized_plpc":"-0.57"},
     {"symbol":"QQQ","asset_class":"us_equity","qty":"300","current_price":"756","market_value":"226800","avg_entry_price":"750","unrealized_plpc":"0.01"},
     {"symbol":"IWM","asset_class":"us_equity","qty":"200","current_price":"280","market_value":"56000","avg_entry_price":"290","unrealized_plpc":"-0.034"},
    ]
    FAKE['/v2/positions'] = lambda p: pos
FAKE['/v2/orders'] = lambda p: []
cr.Tick.__init__.__defaults__
orig_init = cr.Tick.__init__
def init(self, dry):
    orig_init(self, dry); self.state['mental_stops'] = {"IWM": {"stop": 285, "side": "buy"}}
cr.Tick.__init__ = init
code, t, lines = cr.tick(True)
print(code); print("\n".join(lines))
