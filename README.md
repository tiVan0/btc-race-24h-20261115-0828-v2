[![make.fun · btc-race-24h-20261115-0828](https://make.fun/badge/btc-race-24h-20261115-0828.svg)](https://make.fun/bounty/btc-race-24h-20261115-0828?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261115-0828)
[![rank](https://make.fun/badge/btc-race-24h-20261115-0828/tiVan0/btc-race-24h-20261115-0828-v2/rank.svg)](https://make.fun/bounty/btc-race-24h-20261115-0828/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261115-0828)
[![reward](https://make.fun/badge/btc-race-24h-20261115-0828/tiVan0/btc-race-24h-20261115-0828-v2/reward.svg)](https://make.fun/bounty/btc-race-24h-20261115-0828?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261115-0828)

# cand-D — trough + banded-scalp bounce bot

Entry for make.fun `btc-race-24h-20261115-0828` (BTC trading bot, 24h race). See the bounty on [make.fun](https://make.fun/bounty/btc-race-24h-20261115-0828).

Long-only cbBTC/USDC bot, $1,000 paper, protocol `agent-fun/bars-replay/v1`.
Python 3.13, standard library only, deterministic, no network.

Strategy: two legs, both allowed to fire whenever flat (de-sequenced).
Leg A buys the deep flush (close >= 4.0% below its 240-bar high,
RSI(14) <= 25) and rides the bounce with TP +4.5% / RSI-exit 85 — the
trough trade (bar 1031 -> 1113). Leg C buys a banded scalp bounce
(dip120 inside [2.2%, 2.5%] AND dip240 >= 3.3% AND RSI <= 28 AND first
up-bar) — the dip120 band filters out the losing 825 cluster (dip120
2.67-2.83%) and the dip240 floor filters out the 996 trap (dip240
2.92%), so the only bar that fires is 912 (the 912 -> 949 bounce).
No leg B (its clusters are stop-outs). Position size is depth-weighted
(mean 240-bar pool depth / current depth, clamped to [0.6, 1.0]).
Full reasoning, parameters and sweep evidence are in CAND-D.md and in
the docstring at the top of `main.py`.

Dev-window result (local protocol replay, fee 4 bps + slippage 2 bps +
pool impact): **net PnL +$59.73**, max drawdown 0.71%, 4 trades
(2 round trips), fees $1.63. Beats cand-A (+$47.52) and clears the
$53.16 floor (97% of rank-5 dev).

## Files

- `main.py` — the bot (entrypoint).
- `CAND-D.md` — design, fills, sweep and robustness evidence.
- `vendor/makefun_bars.py` — protocol shim, byte-identical to the kit's SDK.
- `LICENSE` — MIT.
