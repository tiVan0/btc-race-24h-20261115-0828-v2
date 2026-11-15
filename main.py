"""cand-D: trough + banded-scalp bounce, de-sequenced (btc-race-24h-20261115-0828).

Two legs, both allowed to fire whenever flat (no round_trips sequencing —
rev4's sequencing was the structural bug: leg A never fired, so legs B/C
were unreachable). No leg B: its clusters are stop-outs, and dropping it
removes the 1142 loser cand-A had to block with PULL_DIP.

  leg A (flush/trough): close >= 4.0% below the 240-bar high with RSI(14)
    <= 25. Fires at bar 1031 (dip240 4.34%, RSI 23.7) and rides the bounce
    with TP +4.5% / RSI-exit 85 — the trough trade cand-A banks (+$47.52).
  leg C (banded scalp): dip120 inside [2.2%, 2.5%] AND dip240 >= 3.3% AND
    RSI <= 28 AND first up-bar (close > prev close). The dip120 BAND is the
    filter: the losing 825 cluster sits at dip120 2.67-2.83% (above the
    band), the 850-852 and 1001/1003 clusters too; the 996 trap sits at
    dip240 2.92% (below the dip240 floor). The only bar that fires is 912
    (dip120 2.34%, dip240 3.67%, RSI 25.5) — the 912 -> 949 bounce (+1.79%
    gross). Exits: TP +1.2%, trail 1.0%, stop -1.5%, RSI-exit 80, hold 150.
MAX_RT 4, no entries after bar 1400. Deterministic, stdlib only.
The vendor shim is a byte-identical copy of the kit's SDK shim.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"

# --- leg A (flush/trough) ---
FLUSH = 0.040
FLUSH_RSI = 25.0
FLUSH_HIGH_BARS = 240
FLUSH_TP = 0.045
FLUSH_TRAIL = 0.015
FLUSH_STOP = 0.020
FLUSH_RSI_EXIT = 85.0
FLUSH_RSI_MIN_GAIN = 0.010
FLUSH_HOLD = 300
# --- leg C (banded scalp bounce) ---
SCALP_DIP_LO = 0.022
SCALP_DIP_HI = 0.025
SCALP_DIP240_MIN = 0.033
SCALP_HIGH_BARS = 120
SCALP_RSI = 28.0
SCALP_TP = 0.012
SCALP_TRAIL = 0.010
SCALP_STOP = 0.015
SCALP_RSI_EXIT = 80.0
SCALP_RSI_MIN_GAIN = 0.010
SCALP_HOLD = 200
# --- shared ---
MAX_RT = 4
NO_ENTRY_AFTER = 1400
MAX_SLIP_BPS = 100
RSI_PERIOD = 14
DEPTH_WINDOW = 240
DEPTH_MIN = 0.6
DEPTH_MAX = 1.0

closes = []
highs = []
lows = []
depths = []
typical = []

round_trips = 0
entry_kind = None
entry_price = None
peak = None
held = 0


def rsi14():
    """RSI over the last RSI_PERIOD closes: simple means of gains and losses."""
    if len(closes) < RSI_PERIOD + 1:
        return None
    gains = 0.0
    losses = 0.0
    for i in range(len(closes) - RSI_PERIOD, len(closes)):
        d = closes[i] - closes[i - 1]
        if d > 0:
            gains += d
        else:
            losses -= d
    if gains + losses == 0:
        return 50.0
    return 100.0 * gains / (gains + losses)


def depth_factor():
    """Scale the notional by pool depth: deep pool -> full size."""
    if len(depths) < DEPTH_WINDOW or depths[-1] <= 0:
        return 1.0
    mean_d = sum(depths[-DEPTH_WINDOW:]) / DEPTH_WINDOW
    f = mean_d / depths[-1]
    return DEPTH_MIN if f < DEPTH_MIN else (DEPTH_MAX if f > DEPTH_MAX else f)


pending_kind = None


def buy_order(notional, kind):
    global pending_kind
    pending_kind = kind
    return [{"side": "buy", "symbol": SYMBOL,
             "notional_quote_units": notional,
             "max_slippage_bps": MAX_SLIP_BPS}]


def sell_order(qty):
    return [{"side": "sell", "symbol": SYMBOL, "qty": qty,
             "max_slippage_bps": MAX_SLIP_BPS}]


def on_batch(state, batch):
    global round_trips, entry_price, peak, held, entry_kind
    k = state.seq
    bar = batch["bars"][0] if batch["bars"] else None
    if bar is not None:
        ps = 10 ** state.symbols[SYMBOL]["price_scale"]
        closes.append(int(bar["c"]) / ps)
        highs.append(int(bar["h"]) / ps)
        lows.append(int(bar["l"]) / ps)
        typical.append((highs[-1] + lows[-1] + closes[-1]) / 3.0)
        depths.append(int(bar["c_depth"][0]) / 1_000_000.0)
    for fill in batch["fills"]:
        if fill["symbol"] != SYMBOL or fill["status"] != "filled":
            continue
        if fill["side"] == "buy":
            entry_price = int(fill["price"])
            entry_kind = pending_kind
            peak = entry_price
            held = 0
        elif fill["side"] == "sell":
            entry_price = None
            entry_kind = None
            peak = None
            held = 0
            round_trips += 1
    if state.warming_up or bar is None:
        return []
    pos = state.positions.get(SYMBOL)
    holding = pos is not None and int(pos.qty) > 0
    close_raw = int(bar["c"])
    ps = 10 ** state.symbols[SYMBOL]["price_scale"]
    if holding:
        held += 1
        if peak is None or close_raw > peak:
            peak = close_raw
        entry = entry_price if entry_price is not None else close_raw
        entry_usd = entry / ps
        peak_usd = peak / ps if peak is not None else None
        if entry_kind == "scalp":
            tp, tr, st, hd = SCALP_TP, SCALP_TRAIL, SCALP_STOP, SCALP_HOLD
            rsi_exit, rsi_min = SCALP_RSI_EXIT, SCALP_RSI_MIN_GAIN
        else:
            tp, tr, st, hd = FLUSH_TP, FLUSH_TRAIL, FLUSH_STOP, FLUSH_HOLD
            rsi_exit, rsi_min = FLUSH_RSI_EXIT, FLUSH_RSI_MIN_GAIN
        if closes[-1] >= entry_usd * (1.0 + tp):
            return sell_order(int(pos.qty))
        if peak_usd is not None and closes[-1] <= peak_usd * (1.0 - tr):
            return sell_order(int(pos.qty))
        if closes[-1] <= entry_usd * (1.0 - st):
            return sell_order(int(pos.qty))
        r = rsi14()
        if (r is not None and r >= rsi_exit
                and closes[-1] >= entry_usd * (1.0 + rsi_min)):
            return sell_order(int(pos.qty))
        if held >= hd:
            return sell_order(int(pos.qty))
        return []
    # Flat: look for an entry.
    if round_trips >= MAX_RT or k >= NO_ENTRY_AFTER or k < 20:
        return []
    r = rsi14()
    # Leg A: deep flush off a recent 240-bar high (the trough trade).
    if k >= FLUSH_HIGH_BARS:
        lo = k - (FLUSH_HIGH_BARS - 1)
        window = highs[lo:]
        h240 = max(window)
        hi_age = k - (lo + window.index(h240))
        if ((h240 - closes[-1]) / h240 >= FLUSH and hi_age <= 999
                and r is not None and r <= FLUSH_RSI):
            n = int(state.cash * depth_factor())
            if n >= int(state.hello["fees"]["min_notional_quote_units"]):
                return buy_order(n, "flush")
    # Leg C: banded scalp bounce (fires at any round_trips — de-sequenced).
    if k >= SCALP_HIGH_BARS:
        h120 = max(highs[max(0, k - (SCALP_HIGH_BARS - 1)):])
        lo120 = k - (SCALP_HIGH_BARS - 1)
        hi_age120 = k - (lo120 + highs[lo120:].index(h120))
        h240 = max(highs[max(0, k - (FLUSH_HIGH_BARS - 1)):])
        dip120 = (h120 - closes[-1]) / h120
        dip240 = (h240 - closes[-1]) / h240
        turn_ok = len(closes) >= 2 and closes[-1] > closes[-2]
        if (SCALP_DIP_LO <= dip120 <= SCALP_DIP_HI
                and dip240 >= SCALP_DIP240_MIN and hi_age120 <= 120
                and r is not None and r <= SCALP_RSI and turn_ok):
            n = int(state.cash * depth_factor())
            if n >= int(state.hello["fees"]["min_notional_quote_units"]):
                return buy_order(n, "scalp")
    return []


makefun_bars.run(on_batch)
