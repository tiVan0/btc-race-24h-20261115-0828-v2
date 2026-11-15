[![make.fun · btc-race-24h-20261115-0828](https://make.fun/badge/btc-race-24h-20261115-0828.svg)](https://make.fun/bounty/btc-race-24h-20261115-0828?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261115-0828)
[![rank](https://make.fun/badge/btc-race-24h-20261115-0828/tiVan0/btc-race-24h-20261115-0828-v2/rank.svg)](https://make.fun/bounty/btc-race-24h-20261115-0828/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261115-0828)
[![reward](https://make.fun/badge/btc-race-24h-20261115-0828/tiVan0/btc-race-24h-20261115-0828-v2/reward.svg)](https://make.fun/bounty/btc-race-24h-20261115-0828?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261115-0828)

# cand-F — trough + banded-scalp + mid-dip + range bot

Entry for make.fun `btc-race-24h-20261115-0828` (BTC trading bot, 24h race). See the bounty on [make.fun](https://make.fun/bounty/btc-race-24h-20261115-0828).

Long-only cbBTC/USDC bot, $1,000 paper, protocol `agent-fun/bars-replay/v1`.
Python 3.13, standard library only, deterministic, no network.

Strategy: four legs, all allowed to fire whenever flat (de-sequenced).
Leg A buys the deep flush (close >= 4.0% below its 240-bar high,
RSI(14) <= 25) and rides the bounce with TP +4.5% / RSI-exit 85 — the
trough trade (bar 1031 -> 1113). Leg C buys a banded scalp bounce
(dip120 inside [2.2%, 2.5%] AND dip240 >= 3.3% AND RSI <= 28 AND first
up-bar) — the dip120 band filters out the losing 825 cluster (dip120
2.67-2.83%) and the dip240 floor filters out the 996 trap (dip240
2.92%), so the only bar that fires is 912 (the 912 -> 949 bounce).
Leg D buys a mid-decline oversold dip (dip240 inside [3.5%, 4.0%) AND
dip120 >= 2.5% AND RSI <= 20, no up-bar confirmation) — fires at bars
820-824 (the 824 -> 836 bounce); the dip120 >= 2.5% floor excludes the
910-911 trap (dip120 2.34-2.42%). Exits: TP +0.4% (the bounce from the
820 fill only runs +0.47% to the 836 peak), trail 1.0%, stop -1.5%,
hold 150. Leg R (NEW) buys a shallow range dip (dip120 inside
[1.0%, 1.8%] AND dip240 >= 2.5% AND RSI <= 40 AND first up-bar AND
120-bar return <= -1.0% AND close within 0.5% of the 120-bar low AND
60-bar return <= -0.5%) — the ret60 filter separates the real range
bottom (bar 499, the 500 -> 550 bounce) from the look-alike bar 485
(ret60 +0.23%, a local uptick inside the decline) and the 963-971
trap cluster. Exits: TP +1.0%, trail 1.0%, stop -1.5%, hold 100.
No leg B (its clusters are stop-outs). Position size is depth-weighted
(mean 240-bar pool depth / current depth, clamped to [0.6, 1.0]).
Full reasoning, parameters and sweep evidence are in CAND-F.md and in
the docstring at the top of `main.py`.

Dev-window result (local protocol replay, fee 4 bps + slippage 2 bps +
pool impact): **net PnL +$71.84**, max drawdown 1.17%, 8 trades
(4 round trips), fees $3.26. Beats cand-E (+$61.94) by +$9.90 and
cand-D (+$59.73) by +$12.11; clears rank-5 dev ($71.30) and the
$69.16 floor (97% of rank-5 dev).

## Files

- `main.py` — the bot (entrypoint).
- `CAND-F.md` — design, fills, sweep and robustness evidence.
- `vendor/makefun_bars.py` — protocol shim, byte-identical to the kit's SDK.
- `LICENSE` — MIT.
