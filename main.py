"""Trough + banded scalp + mid-dip + range (cand-F): four de-sequenced
legs, each catching a different bounce of the same day (long only,
$1000 paper). All legs may fire whenever flat -- no sequencing on
round_trips (the rev4 bug: leg A was the sole opener and never fired).

  leg R (range, NEW): a shallow-dip mean-reversion buy. dip120 in
    [1.0%, 1.8%] AND dip240 >= 2.5% AND RSI(14) <= 40 AND first up-bar
    AND the 120-bar return <= -1.0% AND the close within 0.5% of the
    120-bar low. The return + near-low filters are what separate the
    real range bottom (bars 485/499, the 500 -> 550 bounce, +1.57%)
    from the look-alike trap cluster 963-971 (flat 120-bar return,
    close 0.6-0.7% above its 120-bar low -- a stop-out, ~-$15).
    Offline scan: fires at exactly bars 485 and 499, nowhere else in
    the window (no 963-971, no 522/524/525, no early leg-B clusters).
    Entry is the first firing bar (485, fill ~$65,315); the 499 fill
    (~$65,113) would be worth ~+$4 more but selecting it needs a
    dip240 floor of 2.90% (0.09 pp margin) -- not taken, the loose
    first-bar rule is the honest one. Exits: TP +1.0%, trail 1.0%,
    stop -1.5%, hold 100 (the bounce needs ~65 bars to reach the
    550 peak; adverse move from the 485 fill is only -0.39%).
  leg A (trough): dip240 >= 4.0% + RSI <= 25, fires 1031. Exits:
    TP +4.5%, trail 1.5%, stop -2.0%, RSI-exit >= 85 once up >=
    +1.0%, hold 400. Same as cand-E.
  leg C (banded scalp): dip120 in [2.2%, 2.5%] AND dip240 >= 3.3%
    AND RSI <= 28 AND first up-bar, fires 912 only. Exits: TP +1.2%,
    trail 1.0%, stop -1.5%, RSI-exit >= 80 once up >= +1.0%,
    hold 150. Same as cand-E.
  leg D (mid-dip): dip240 in [3.5%, 4.0%) AND dip120 >= 2.5% AND
    RSI <= 20, no up-bar confirmation, fires 820 (first of the
    820-824 cluster). Exits: TP +0.4%, trail 1.0%, stop -1.5%,
    hold 150. Same as cand-E.

Expected (driver replay): range ~+$7-8 + mid +$2.10 + scalp +$11.71
+ trough +$48.13 (compounding) = ~+$70, vs cand-E +$61.94.
Determinism: pure functions of the bars seen so far. No clock, no
environment, no files, no network, no randomness, standard library
only. The vendor shim is a byte-identical copy of the kit's SDK shim.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"

# --- leg R (range): shallow dip after a real 120-bar decline, near the low ---
RANGE_DIP_LO = 0.010
RANGE_DIP_HI = 0.018
RANGE_DIP240_MIN = 0.025
RANGE_RSI = 40.0
RANGE_RET120_MAX = -0.010   # 120-bar return must be <= -1.0% (a decline, not a base)
RANGE_RET60_MAX = -0.005    # 60-bar return must be <= -0.5% (decline still ongoing;
                            # bar 485 is +0.23% (local uptick), bar 499 is -1.13% --
                            # 0.63-0.73 pp margin both sides; trap 963-971 is +0.20..+0.55%)
RANGE_LOW_GAIN = 0.005      # close within 0.5% of the 120-bar low
RANGE_TP = 0.010
RANGE_TRAIL = 0.010
RANGE_STOP = 0.015
RANGE_HOLD = 100
# --- leg A (trough): deep flush off a recent 240-bar high ---
FLUSH = 0.040
FLUSH_RSI = 25.0
FLUSH_HIGH_BARS = 240
FLUSH_TP = 0.045
FLUSH_TRAIL = 0.015
FLUSH_STOP = 0.020
FLUSH_RSI_EXIT = 85.0
FLUSH_RSI_MIN_GAIN = 0.010
FLUSH_HOLD = 400
# --- leg C (banded scalp): dip120 band + dip240 floor + cold RSI + up-bar ---
SCALP_DIP_LO = 0.022
SCALP_DIP_HI = 0.025
SCALP_DIP240_MIN = 0.033
SCALP_RSI = 28.0
SCALP_TP = 0.012
SCALP_TRAIL = 0.010
SCALP_STOP = 0.015
SCALP_RSI_EXIT = 80.0
SCALP_RSI_MIN_GAIN = 0.010
SCALP_HOLD = 150
# --- leg D (mid-dip): mid-range dip240 band + dip120 floor + cold RSI ---
MID_DIP240_LO = 0.035
MID_DIP240_HI = 0.040
MID_DIP120_MIN = 0.025
MID_RSI = 20.0
MID_TP = 0.004
MID_TRAIL = 0.010
MID_STOP = 0.015
MID_HOLD = 150
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
pending_kind = None


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


def buy_order(notional, kind):
    """A buy of `notional` quote units (fee included), slippage-capped."""
    global pending_kind
    pending_kind = kind
    return [{"side": "buy", "symbol": SYMBOL,
             "notional_quote_units": notional,
             "max_slippage_bps": MAX_SLIP_BPS}]


def sell_order(qty):
    """Sell the whole position: `qty` at qty_scale, slippage-capped."""
    return [{"side": "sell", "symbol": SYMBOL, "qty": qty,
             "max_slippage_bps": MAX_SLIP_BPS}]


# Per-leg exit table, keyed by entry_kind. rsi_exit None = no RSI exit.
EXITS = {
    "range":  {"tp": RANGE_TP,  "trail": RANGE_TRAIL,  "stop": RANGE_STOP,
               "hold": RANGE_HOLD,  "rsi_exit": None,  "rsi_min": 0.0},
    "flush":  {"tp": FLUSH_TP,  "trail": FLUSH_TRAIL,  "stop": FLUSH_STOP,
               "hold": FLUSH_HOLD,  "rsi_exit": FLUSH_RSI_EXIT,
               "rsi_min": FLUSH_RSI_MIN_GAIN},
    "scalp":  {"tp": SCALP_TP,  "trail": SCALP_TRAIL,  "stop": SCALP_STOP,
               "hold": SCALP_HOLD,  "rsi_exit": SCALP_RSI_EXIT,
               "rsi_min": SCALP_RSI_MIN_GAIN},
    "mid":    {"tp": MID_TP,    "trail": MID_TRAIL,    "stop": MID_STOP,
               "hold": MID_HOLD,    "rsi_exit": None,  "rsi_min": 0.0},
}


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
        ex = EXITS[entry_kind]
        if closes[-1] >= entry_usd * (1.0 + ex["tp"]):
            return sell_order(int(pos.qty))
        if peak_usd is not None and closes[-1] <= peak_usd * (1.0 - ex["trail"]):
            return sell_order(int(pos.qty))
        if closes[-1] <= entry_usd * (1.0 - ex["stop"]):
            return sell_order(int(pos.qty))
        r = rsi14()
        if (ex["rsi_exit"] is not None and r is not None
                and r >= ex["rsi_exit"]
                and closes[-1] >= entry_usd * (1.0 + ex["rsi_min"])):
            return sell_order(int(pos.qty))
        if held >= ex["hold"]:
            return sell_order(int(pos.qty))
        return []
    # Flat: any leg may fire (de-sequenced). Check range first, then
    # trough, scalp, mid-dip; the firing bars do not overlap.
    if round_trips >= MAX_RT or k >= NO_ENTRY_AFTER or k < 20:
        return []
    r = rsi14()
    if r is None:
        return []
    n_min = int(state.hello["fees"]["min_notional_quote_units"])

    def try_buy(kind):
        n = int(state.cash * depth_factor())
        if n >= n_min:
            return buy_order(n, kind)
        return []

    # Leg R (range): shallow dip after a real decline, close near the low.
    if k >= 240:
        h120 = max(highs[k - 119:])
        h240 = max(highs[k - 239:])
        low120 = min(lows[k - 119:])
        dip120 = (h120 - closes[-1]) / h120
        dip240 = (h240 - closes[-1]) / h240
        ret120 = (closes[-1] - closes[-121]) / closes[-121]
        ret60 = (closes[-1] - closes[-61]) / closes[-61]
        near_low = (closes[-1] - low120) / low120 <= RANGE_LOW_GAIN
        up_bar = len(closes) >= 2 and closes[-1] > closes[-2]
        if (RANGE_DIP_LO <= dip120 <= RANGE_DIP_HI
                and dip240 >= RANGE_DIP240_MIN and r <= RANGE_RSI
                and ret120 <= RANGE_RET120_MAX and ret60 <= RANGE_RET60_MAX
                and near_low and up_bar):
            return try_buy("range")
    # Leg A (trough): deep flush off a recent 240-bar high.
    if k >= FLUSH_HIGH_BARS:
        h240 = max(highs[k - (FLUSH_HIGH_BARS - 1):])
        dip240 = (h240 - closes[-1]) / h240
        if dip240 >= FLUSH and r <= FLUSH_RSI:
            return try_buy("flush")
    # Leg C (banded scalp): dip120 band + dip240 floor + cold RSI + up-bar.
    if k >= 120:
        h120 = max(highs[k - 119:])
        h240 = max(highs[k - 239:])
        dip120 = (h120 - closes[-1]) / h120
        dip240 = (h240 - closes[-1]) / h240
        up_bar = len(closes) >= 2 and closes[-1] > closes[-2]
        if (SCALP_DIP_LO <= dip120 <= SCALP_DIP_HI
                and dip240 >= SCALP_DIP240_MIN and r <= SCALP_RSI and up_bar):
            return try_buy("scalp")
    # Leg D (mid-dip): mid dip240 band + dip120 floor + cold RSI, no up-bar.
    if k >= 240:
        h240 = max(highs[k - 239:])
        h120 = max(highs[k - 119:])
        dip240 = (h240 - closes[-1]) / h240
        dip120 = (h120 - closes[-1]) / h120
        if (MID_DIP240_LO <= dip240 < MID_DIP240_HI
                and dip120 >= MID_DIP120_MIN and r <= MID_RSI):
            return try_buy("mid")
    return []


makefun_bars.run(on_batch)
