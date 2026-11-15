# CAND-G — 6-leg de-sequenced dip bot (btc-race-24h-20261115-0828)

## Final result (local driver replay, fresh-kit level-14 bars)

| metric | value |
|---|---|
| Net PnL | **+$85.36** |
| Trades | 12 (6 round trips) |
| Fees | $4.96 |
| Max drawdown | 0.77% |
| Final cash | $1,085.36 (from $1,000) |
| Determinism | `--twice`: action logs byte-identical |
| cand-F on same bars | +$71.84 / 4 round trips |
| cand-E on same bars | +$61.94 / 3 round trips |
| cand-D on same bars | +$59.73 / 2 round trips |
| Oracle 4 RT | +$91.91 |

## Fills

| bar | side | price |
|---|---|---|
| 499 | BUY | $65,266.80 |
| 550 | SELL | $65,934.87 |
| 771 | BUY | — |
| 792 | SELL | — |
| 824 | BUY | — |
| 835 | SELL | — |
| 912 | BUY | $63,536.50 |
| 944 | SELL | $64,328.89 |
| 1031 | BUY | $62,330.28 |
| 1113 | SELL | $65,339.09 |
| 1398 | BUY | — |
| 1438 | SELL | — |

Leg R (499 -> 550): +$9.43 — the 500 -> 550 bounce, range leg.
Leg S (771 -> 792): the 768 -> 792 bounce (+1.13%), shallow leg.
Leg D (824 -> 835): the 824 -> 836 bounce, tightened mid-dip leg.
Leg C (912 -> 944): +$11.80 — the 912 -> 949 bounce, banded scalp.
Leg A (1031 -> 1113): +$48.54 — the trough trade.
Leg L (1398 -> 1438): the 1403 -> 1439 bounce, late leg.

## Design (from cand-G-exploration.md prose + offline bar scan)

Six legs, all de-sequenced (any may fire whenever flat). MAX_RT = 6, NO_ENTRY_AFTER = 1410.

- **Leg A (trough)** — unchanged from cand-F: dip240 >= 4.0% + RSI <= 25, fires 1031. Exit TP +4.5%, RSI-exit 85.
- **Leg C (banded scalp)** — unchanged from cand-F: dip120 in [2.2%, 2.5%] AND dip240 >= 3.3% AND RSI <= 28 AND first up-bar, fires 912. Exit TP +1.2%.
- **Leg D (mid-dip, tightened)** — dip240 in [3.5%, 4.0%) AND dip120 >= 2.5% AND **RSI <= 16.7** (was <= 20), no up-bar. Exit **TP +1.0%** (was +0.4%). Fires 824, exits 835. RSI plateau for firing at 824 is [16.0, 17.4) — 1.4 points wide; 16.7 sits mid-plateau. RSI 17.5 is a measured cliff (-$13.25).
- **Leg R (range)** — unchanged from cand-F: dip120 in [1.0%, 1.8%] AND dip240 >= 2.5% AND RSI <= 40 AND first up-bar AND ret120 <= -1.0% AND near-low <= 0.5% AND ret60 <= -0.5%. Fires 499. Exit TP +1.0%.
- **Leg S (shallow, NEW)** — dip120 in [1.5%, 2.2%] AND dip240 in [2.5%, 3.0%] AND RSI <= 40 AND ret60 <= -1.0% AND **ret120 <= -1.0%** AND first up-bar. Exit TP +0.4%, trail 1.0%, stop -1.5%, hold 150. Fires 771, exits 792. The ret120 filter separates 771 (ret120 -1.55%) from 985 (+0.06%) with a 1.61 pp gap. Without it the leg fires at 985 and blocks the trough leg.
- **Leg L (late, NEW)** — dip120 in [1.0%, 1.8%] AND dip240 in [1.85%, 2.5%] AND RSI <= 30 AND ret120 <= -1.0% AND ret60 <= -0.80% AND near-low <= 0.1% AND **first up-bar**. Exit TP +0.8%, trail 1.0%, stop -1.5%, hold 40. Fires 1398, exits 1438. Without the up-bar filter the leg fires at bar 357.

## Builder notes (from the build)

- The driver fills report `decided_bar` as a millisecond timestamp, not a bar index — the hold leg records `seq` at order send instead.
- RSI-exits use Wilder-smoothed RSI14 (simple-mean RSI would fire at bar 923, 81.31 — not allowed); entry RSI stays simple-mean.
- up-bar = close > previous close.

## Robustness (10 one-knob perturbations, base = +$85.36)

8/10 give exactly +$85.36 (plateau). D TP 0.9% -> +$83.75; D TP 1.1% -> +$85.64 (+$0.28, margin $6.15 — not taken). **D RSI 17.5 -> +$72.11 (CLIFF -$13.25)** — the only fragility; mitigated by using RSI 16.7 (mid-plateau).

## Rejected (measured)

- Trough entry delay (RSI 30 + up-bar): +$71.64 (-$0.20) — no clean delay to 1037.
- Leg C TP +1.5% as base: +$72.76 (+$0.92) but margin $7.72, cliff -$11.77.
- Leg R near-low 0.1% without up-bar as base: +$72.74 (+$0.90) but margin 0.02–0.03 pp.
- Leg S without ret120: +$10.17 — fires 985, blocks trough. POISON.
- Leg E (re-entry 870): +$70.90 (-$0.94) — blocks leg C.
- Leg L without up-bar: +$62.83 — fires 357. POISON.
- Leg L ret60 -0.9% (fires 1402): +$86.50 but ret60 window 0.02 pp — knife-edge.

## Files

- `main.py` — final candidate (written in 2+ messages from the prose spec, without reading any prior candidate's main.py)
- `vendor/` — kit SDK shim, byte-identical copy from base-rev4
- `CAND-G.md` (this file), `README.md`, `LICENSE` — MIT
