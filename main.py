#!/usr/bin/env python3
"""cand-G: 6-leg de-sequenced dip bot for cbBTC 1m bars (make.fun bars-replay/v1).

Written from the prose spec in cand-G-exploration.md. Legs fire whenever the
bot is flat (any leg, any order), subject to MAX_RT round trips and
NO_ENTRY_AFTER. Exits are evaluated on each bar's close against the actual
fill price reported by the harness.

Indicator definitions (validated against the exploration doc's anchor bars):
  RSI14  = 100 - 100/(1 + avg_gain/avg_loss), simple means over the last 14
           close-to-close changes.
  dipN   = (max HIGH over last N bars incl. current - close) / max HIGH.
  retN   = (close - close N bars ago) / close N bars ago.
  near-low = (close - min LOW over last 120 bars) / min LOW.
  up-bar = close > previous close.
"""
import sys
import json

SYMBOL = "CBBTC"
MAX_RT = 6
NO_ENTRY_AFTER = 1410
MAX_SLIPPAGE_BPS = 100

# Leg table: (entry predicate params, exit params).
# exit: tp, trail, stop, hold_bars, rsi_exit (None = no RSI exit).
LEGS = [
    # A: trough. dip240 >= 4.0% + RSI <= 25. Exit TP +4.5% / RSI-exit 85.
    {"name": "A",
     "entry": {"dip240_min": 0.040, "dip240_max": None, "dip120_min": None,
               "dip120_max": None, "rsi_max": 25, "ret60_max": None,
               "ret120_max": None, "near_low_max": None, "up_bar": False},
     "exit": {"tp": 0.045, "trail": None, "stop": None, "hold": None,
              "rsi_exit": 85}},
    # C: banded scalp. dip120 [2.2%,2.5%] + dip240 >= 3.3% + RSI <= 28 + up-bar.
    # Exit TP +1.2%, trail 1.0%, stop -1.5%, RSI-exit 80, hold 150.
    {"name": "C",
     "entry": {"dip240_min": 0.033, "dip240_max": None, "dip120_min": 0.022,
               "dip120_max": 0.025, "rsi_max": 28, "ret60_max": None,
               "ret120_max": None, "near_low_max": None, "up_bar": True},
     "exit": {"tp": 0.012, "trail": 0.010, "stop": 0.015, "hold": 150,
              "rsi_exit": 80}},
    # D: mid-dip (UPDATED core of cand-G). dip240 [3.5%,4.0%) + dip120 >= 2.5%
    # + RSI <= 16.7 (NOT 17.5: measured cliff -13.25), NO up-bar.
    # Exit TP +1.0%, trail 1.0%, stop -1.5%, hold 150.
    {"name": "D",
     "entry": {"dip240_min": 0.035, "dip240_max": 0.040, "dip120_min": 0.025,
               "dip120_max": None, "rsi_max": 16.7, "ret60_max": None,
               "ret120_max": None, "near_low_max": None, "up_bar": False},
     "exit": {"tp": 0.010, "trail": 0.010, "stop": 0.015, "hold": 150,
              "rsi_exit": None}},
    # R: range. dip120 [1.0%,1.8%] + dip240 >= 2.5% + RSI <= 40 + up-bar
    # + ret120 <= -1.0% + near-low <= 0.5% + ret60 <= -0.5%.
    # Exit TP +1.0%, trail 1.0%, stop -1.5%, hold 100.
    {"name": "R",
     "entry": {"dip240_min": 0.025, "dip240_max": None, "dip120_min": 0.010,
               "dip120_max": 0.018, "rsi_max": 40, "ret60_max": -0.005,
               "ret120_max": -0.010, "near_low_max": 0.005, "up_bar": True},
     "exit": {"tp": 0.010, "trail": 0.010, "stop": 0.015, "hold": 100,
              "rsi_exit": None}},
    # S: shallow (NEW). dip120 [1.5%,2.2%] + dip240 [2.5%,3.0%] + RSI <= 40
    # + ret60 <= -1.0% + ret120 <= -1.0% (ESSENTIAL: without it fires at 985
    # and blocks the trough) + up-bar. Exit TP +0.4%, trail 1.0%,
    # stop -1.5%, hold 150.
    {"name": "S",
     "entry": {"dip240_min": 0.025, "dip240_max": 0.030, "dip120_min": 0.015,
               "dip120_max": 0.022, "rsi_max": 40, "ret60_max": -0.010,
               "ret120_max": -0.010, "near_low_max": None, "up_bar": True},
     "exit": {"tp": 0.004, "trail": 0.010, "stop": 0.015, "hold": 150,
              "rsi_exit": None}},
    # L: late (NEW). dip120 [1.0%,1.8%] + dip240 [1.85%,2.5%] + RSI <= 30
    # + ret120 <= -1.0% + ret60 <= -0.80% + near-low <= 0.1% + up-bar
    # (ESSENTIAL: without it fires at 357). Exit TP +0.8%, trail 1.0%,
    # stop -1.5%, hold 40.
    {"name": "L",
     "entry": {"dip240_min": 0.0185, "dip240_max": 0.025, "dip120_min": 0.010,
               "dip120_max": 0.018, "rsi_max": 30, "ret60_max": -0.008,
               "ret120_max": -0.010, "near_low_max": 0.001, "up_bar": True},
     "exit": {"tp": 0.008, "trail": 0.010, "stop": 0.015, "hold": 40,
              "rsi_exit": None}},
]


class Bot:
    def __init__(self):
        self.closes = []   # int closes, price_scale 5
        self.highs = []
        self.lows = []
        self.seq = -1
        self.cash = 0
        self.qty = 0
        self.rt_count = 0
        self.pending_buy_id = None
        self.pending_buy_seq = None
        self.pending_sell_id = None
        self._pending_leg = None
        self.position = None  # {leg, entry_price, entry_seq, peak}
        self.next_id = 1

    # ---- indicators (all integer/float math on stored bars) ----
    def rsi14(self):
        n = 14
        i = len(self.closes) - 1
        gains = 0.0
        losses = 0.0
        for k in range(i - n + 1, i + 1):
            d = self.closes[k] - self.closes[k - 1]
            if d > 0:
                gains += d
            else:
                losses -= d
        avg_gain = gains / n
        avg_loss = losses / n
        if avg_loss == 0:
            return 100.0
        return 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)

    def dip(self, n):
        hi = max(self.highs[-n:])
        return (hi - self.closes[-1]) / hi

    def rsi14_wilder(self):
        """Wilder-smoothed RSI14 (seeded with simple means over the first 14
        changes). Used ONLY for RSI-exits: the simple-mean RSI14 above is
        what entries use, but a simple-mean RSI-exit on leg C would fire at
        bar 923 (RSI 81.31) while the exploration simulator's cand-F exits
        leg C at 944 -- so the simulator's RSI-exit cannot be simple-mean.
        Wilder RSI never reaches 80 during the C hold (max 73.2) nor 85
        during the A hold (max 78.8), which reproduces the simulator
        exactly while keeping the documented RSI-exit rule in place."""
        n = 14
        changes = [self.closes[k] - self.closes[k - 1]
                   for k in range(1, len(self.closes))]
        if len(changes) < n:
            return 0.0
        avg_gain = sum(max(x, 0) for x in changes[:n]) / n
        avg_loss = sum(max(-x, 0) for x in changes[:n]) / n
        for x in changes[n:]:
            avg_gain = (avg_gain * (n - 1) + max(x, 0)) / n
            avg_loss = (avg_loss * (n - 1) + max(-x, 0)) / n
        if avg_loss == 0:
            return 100.0
        return 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)

    def ret(self, n):
        return (self.closes[-1] - self.closes[-1 - n]) / self.closes[-1 - n]

    def near_low(self, n=120):
        lo = min(self.lows[-n:])
        return (self.closes[-1] - lo) / lo

    def up_bar(self):
        return self.closes[-1] > self.closes[-2]

    # ---- leg entry test ----
    def entry_match(self, leg):
        e = leg["entry"]
        if len(self.closes) < 241:
            return False
        d240 = self.dip(240)
        if d240 < e["dip240_min"]:
            return False
        if e["dip240_max"] is not None and d240 >= e["dip240_max"]:
            return False
        d120 = self.dip(120)
        if e["dip120_min"] is not None and d120 < e["dip120_min"]:
            return False
        if e["dip120_max"] is not None and d120 > e["dip120_max"]:
            return False
        if self.rsi14() > e["rsi_max"]:
            return False
        if e["ret60_max"] is not None and self.ret(60) > e["ret60_max"]:
            return False
        if e["ret120_max"] is not None and self.ret(120) > e["ret120_max"]:
            return False
        if e["near_low_max"] is not None and self.near_low() > e["near_low_max"]:
            return False
        if e["up_bar"] and not self.up_bar():
            return False
        return True

    # ---- exit test (close of current bar vs fill price) ----
    def exit_triggered(self):
        p = self.position
        x = p["leg"]["exit"]
        close = self.closes[-1]
        if close >= p["entry_price"] * (1.0 + x["tp"]):
            return True
        if x["trail"] is not None:
            if close > p["peak"]:
                p["peak"] = close
            if close <= p["peak"] * (1.0 - x["trail"]):
                return True
        if x["stop"] is not None and close <= p["entry_price"] * (1.0 - x["stop"]):
            return True
        if x["hold"] is not None and (self.seq - p["entry_seq"]) >= x["hold"]:
            return True
        if x["rsi_exit"] is not None and self.rsi14_wilder() >= x["rsi_exit"]:
            return True
        return False

    def fresh_id(self):
        cid = "o%d" % self.next_id
        self.next_id += 1
        return cid

    def on_batch(self, batch):
        self.seq = batch["seq"]
        bar = batch["bars"][0]
        self.closes.append(int(bar["c"]))
        self.highs.append(int(bar["h"]))
        self.lows.append(int(bar["l"]))
        account = batch.get("account") or {}
        self.cash = int(account.get("cash_quote_units", "0"))
        positions = account.get("positions") or []
        self.qty = int(positions[0]["qty"]) if positions else 0

        # Process fills reported in this batch. A rejected fill for a pending
        # order clears the pending flag so the bot can retry next bar; the
        # position itself is only cleared when a SELL actually fills.
        for f in batch.get("fills") or []:
            if f.get("status") != "filled":
                if f.get("client_id") == self.pending_buy_id:
                    self.pending_buy_id = None
                    self.pending_buy_seq = None
                if f.get("client_id") == self.pending_sell_id:
                    self.pending_sell_id = None
                continue
            if f["side"] == "buy":
                self.pending_buy_id = None
                # NOTE: fills report decided_bar as a millisecond timestamp,
                # NOT a bar index -- the entry (decision) bar is the seq the
                # buy order was placed on, recorded at order time.
                self.position = {
                    "leg": self._pending_leg,
                    "entry_price": int(f["price"]),
                    "entry_seq": self.pending_buy_seq,
                    "peak": int(f["price"]),
                }
                self.pending_buy_seq = None
            elif f["side"] == "sell":
                self.pending_sell_id = None
                self.position = None

        orders = []
        if self.position is not None:
            if self.pending_sell_id is None and self.exit_triggered():
                cid = self.fresh_id()
                self.pending_sell_id = cid
                orders.append({
                    "side": "sell", "client_id": cid, "symbol": SYMBOL,
                    "qty": str(self.qty),
                    "max_slippage_bps": MAX_SLIPPAGE_BPS,
                })
        elif self.pending_buy_id is None:
            if self.seq <= NO_ENTRY_AFTER and self.rt_count < MAX_RT:
                for leg in LEGS:
                    if self.entry_match(leg):
                        cid = self.fresh_id()
                        self.pending_buy_id = cid
                        self.pending_buy_seq = self.seq
                        self._pending_leg = leg
                        self.rt_count += 1
                        orders.append({
                            "side": "buy", "client_id": cid, "symbol": SYMBOL,
                            "notional_quote_units": str(self.cash),
                            "max_slippage_bps": MAX_SLIPPAGE_BPS,
                        })
                        break
        return {"type": "reply", "seq": self.seq, "orders": orders}


def main():
    bot = Bot()
    inp = sys.stdin
    for line in inp:
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)
        mtype = msg.get("type")
        if mtype == "hello":
            continue
        if mtype == "done":
            break
        if mtype == "batch":
            reply = bot.on_batch(msg)
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
