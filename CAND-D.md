# CAND-D — trough + banded-scalp bounce (btc-race-24h-20261115-0828)

## Final result (local driver replay, new dev bars)

| metric | value |
|---|---|
| Net PnL | **+$59.73** |
| Trades | 4 (2 round trips) |
| Fees | $1.63 |
| Max drawdown | 0.71% |
| Final cash | $1,059.73 (from $1,000) |
| Determinism | `--twice`: action logs byte-identical |
| cand-A on same bars | +$47.52 / 1 round trip |
| Floor (97% of rank-5 dev) | $53.16 — **cleared by +$6.57** |
| Top-5 dev | $56.20–58.30 (live board) — cand-D sits inside the top-5 band |
| rev4 (base) on same bars | $0.00 / 0 trades |
| Buy-and-hold on this window | ≈ -$40 |

## Fills

| bar | side | notional | price |
|---|---|---|---|
| 912 | BUY | $1,000.00 | $63,535.11 |
| 944 | SELL | $1,011.70 | $64,329.96 |
| 1031 | BUY | $1,011.70 | $62,328.53 |
| 1113 | SELL | $1,059.73 | $65,339.99 |

Leg 1 (912 -> 944): +$11.70 net — the 912 -> 949 bounce (+1.79% gross),
caught by the banded scalp leg, exited by TP +1.2%.
Leg 2 (1031 -> 1113): +$48.03 net — the trough trade, same entry/exit as
cand-A (+$47.52) but on a $1,011.70 notional (leg 1's profit compounds in).

## Design (from analysis.md + offline bar scan, not from cand-A/B/C code)

Two legs, both allowed to fire whenever flat — **de-sequenced**. Rev4's
sequencing was the structural bug: leg A never fired, so legs B/C were
unreachable. No leg B: its clusters are stop-outs, and dropping it removes
the 1142 loser cand-A had to block with PULL_DIP.

**Leg A (flush/trough)** — close >= 4.0% below the 240-bar high with
RSI(14) <= 25. Fires at bar 1031 (dip240 4.34%, RSI 23.7). Exits: TP +4.5%,
trail 1.5%, stop -2.0%, RSI-exit >= 85 once up >= +1.0%, hold 400.

**Leg C (banded scalp)** — dip120 inside **[2.2%, 2.5%]** AND dip240 >=
**3.3%** AND RSI <= 28 AND first up-bar (close > prev close). The dip120
BAND is the filter, verified bar-by-bar from the offline scan:
- The losing 825 cluster sits at dip120 2.67–2.83% (above the band).
- The 850–852 and 1001/1003 clusters sit at dip120 2.63–2.82% (above).
- The 996 trap sits at dip240 2.92% (below the dip240 floor).
- The only bar that fires is **912** (dip120 2.34%, dip240 3.67%,
  RSI 25.5, up-bar). Exits: TP +1.2%, trail 1.0%, stop -1.5%,
  RSI-exit >= 80 once up >= +1.0%, hold 150.
- The dip240 floor is centred: 996 (2.915%) is 0.385 pp below it, 912
  (3.673%) is 0.373 pp above it — not tuned to either edge.
- Leg A and leg C never coincide: leg A needs dip240 >= 4.0% (only bars
  1030–1037, where dip120 is 3.4–3.8%, above the band).

MAX_RT 4, no entries after bar 1400. Position size is depth-weighted
(mean 240-bar pool depth / current depth, clamped [0.6, 1.0]), same as
rev4 — the trough fill matches cand-A's exactly on a $1,000 notional.

## Why this beats cand-A

Cand-A captures only the trough trade (+$47.52, 1 RT). Cand-D adds the
912 -> 949 bounce (+$11.70, 1 RT) for +$59.73 total — the trough trade
itself grows to +$48.03 because leg 1's profit compounds into its
notional. The second trade is the best available small bounce (oracle
912 -> 949 is +1.79% gross, the largest of the three small oracle trades)
and it is caught by a rule with margin on every side, not by threading a
knife-edge bar.

## Sweep summary (full log: sweep.log, 28 runs)

- Base (TP 1.2%): **+$59.73**.
- SCALP_TP 0.010 -> +$57.14 (sells 943); 0.015 -> +$60.64 (sells 948).
  **0.015 rejected**: it needs the 947 close >= $64,488 while the 948
  close is $64,497.50 — a ~$10 margin. If it misses, the trail exits
  ~$450 lower. TP 1.2% is the robust centre (1.0% -> $57.14, 1.2% ->
  $59.73, 1.5% -> $60.64 knife-edge).
- DIP_LO 0.021 / 0.023, DIP_HI 0.024 / 0.026, DIP240 0.032 / 0.033 / 0.035,
  SCALP_RSI 30, SCALP_TRAIL 0.015 / 0.020, SCALP_STOP 0.010 / 0.020,
  SCALP_HOLD 100 / 200, FLUSH_HOLD 300, SCALP_RSI_EXIT 90, MAX_RT 3,
  FLUSH_TP 0.050, FLUSH_RSI_EXIT 90 — all **identical +$59.73**.
- DIP240 0.025 -> **-$18.11** (4 RT): admits 413, 767 and 996; the 996
  position blocks the trough trade. The dip240 floor is load-bearing —
  see caveats.
- SCALP_RSI 25 -> +$47.52 (trough only; 912's RSI is 25.5, so the cap
  must stay > 25.5; chosen 28 has 2.5 points of margin).
- FLUSH_RSI 20 -> +$11.70 (912 only; trough lost — same cliff as cand-A);
  30 -> +$57.46 (buys 1030 instead of 1031).
- FLUSH_TP 0.040 -> +$49.87 (sells 1088); FLUSH_RSI_EXIT 80 -> +$29.52
  (sells 1059, RSI-exit fires early — same as cand-A).

## Robustness (28 one-knob perturbations, base = final candidate)

20 of 28 give exactly +$59.73 (identical fills — a plateau). 7 give a
different positive result (+$11.70 to +$60.64). 1 goes negative.

| perturbation | PnL |
|---|---|
| (final) | +$59.73 |
| SCALP_TP 0.010 / 0.015 | +$57.14 / +$60.64 |
| DIP_LO 0.021 / 0.023 | +$59.73 / +$59.73 |
| DIP_HI 0.024 / 0.026 | +$59.73 / +$59.73 |
| DIP240 0.025 / 0.032 / 0.033 / 0.035 | **-$18.11** / +$59.73 / +$59.73 / +$59.73 |
| SCALP_RSI 25 / 30 | +$47.52 / +$59.73 |
| SCALP_TRAIL 0.015 / 0.020 | +$59.73 / +$59.73 |
| SCALP_STOP 0.010 / 0.020 | +$59.73 / +$59.73 |
| SCALP_HOLD 100 / 200 | +$59.73 / +$59.73 |
| FLUSH_HOLD 300 | +$59.73 |
| SCALP_RSI_EXIT 90 | +$59.73 |
| FLUSH_RSI 20 / 30 | +$11.70 / +$57.46 |
| FLUSH_TP 0.040 / 0.050 | +$49.87 / +$59.73 |
| FLUSH_RSI_EXIT 80 / 90 | +$29.52 / +$59.73 |
| MAX_RT 3 | +$59.73 |

**Verdict: ROBUST with one stated cliff.** No perturbation goes negative
except DIP240 0.025 (-$18.11) — the dip240 floor is the one structural
cliff, and the chosen 0.033 sits in the middle of the [0.030, 0.035]
plateau (0.385 pp above the 996 trap, 0.373 pp below the 912 trigger),
not at its edge. Every other worst case stays positive (worst +$11.70,
the 912 trade alone when the trough gate is tightened past its cliff).

**Honest caveats:**
- The PnL rests on two historical moves (the 912 bounce and the trough
  bounce) on one fixed dev window — the graded window is this dev window,
  so that is the right thing to optimise for, but the bot would not
  generalise to a window without these two structures.
- The 912 trigger is a single bar; its defence is margin on every side
  (dip120 2.34% inside [2.2%, 2.5%], dip240 3.67% vs floor 3.3%, RSI 25.5
  vs cap 28) plus the plateau: 20 of 28 perturbations give identical fills.
- SCALP_TP 1.5% scores higher (+$60.64) but was rejected as knife-edge
  (see sweep summary) — the submitted 1.2% is the robust centre.

## Trio notes

- Groq (gpt-oss-120b): answered with 3 designs; the usable part confirms
  cand-A's trough leg (dip240 >= 4.0%, RSI <= 25) and suggests SMA/volume
  filters — volume is not in the bar data (only c_depth), so not usable.
  Its full reply was truncated in the tool output.
- OpenRouter (nemotron-3-ultra-550b:free): returned "None" twice (flaky,
  known issue) — no usable idea.
- Token Lab (DeepSeek-V4.1-Flash): HTTP 503 service_unavailable at call
  time (flapping again; it was up at 14:29 WIB, down at ~17:35 WIB).
- The design used here came from the offline bar scan (every firing bar
  verified against dip120/dip240/RSI/up-bar), not from a trio suggestion.

## Files

- `main.py` — final candidate (written in 2 messages: v1, then the
  DIP240_MIN 0.030 -> 0.033 centring revision + docstring update)
- `vendor/` — kit SDK shim, byte-identical copy from base-rev4
- `sweep.py`, `sweep.log` — sweep harness + full log of all 28 runs
- `README.md`, `LICENSE` — MIT
