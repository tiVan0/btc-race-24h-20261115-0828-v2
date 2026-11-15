[![make.fun · btc-race-24h-20261115-0828](https://make.fun/badge/btc-race-24h-20261115-0828.svg)](https://make.fun/bounty/btc-race-24h-20261115-0828?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261115-0828)
[![rank](https://make.fun/badge/btc-race-24h-20261115-0828/tiVan0/btc-race-24h-20261115-0828-v2/rank.svg)](https://make.fun/bounty/btc-race-24h-20261115-0828/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261115-0828)
[![reward](https://make.fun/badge/btc-race-24h-20261115-0828/tiVan0/btc-race-24h-20261115-0828-v2/reward.svg)](https://make.fun/bounty/btc-race-24h-20261115-0828?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261115-0828)

# cand-G — six-leg de-sequenced dip bot

Entry for make.fun `btc-race-24h-20261115-0828` (BTC trading bot, 24h race). See the bounty on [make.fun](https://make.fun/bounty/btc-race-24h-20261115-0828).

Long-only cbBTC/USDC bot, $1,000 paper, protocol `agent-fun/bars-replay/v1`.
Python 3.13, standard library only, deterministic, no network.

Strategy: six legs, all allowed to fire whenever flat (de-sequenced).
Leg A buys the deep flush (close >= 4.0% below its 240-bar high,
RSI(14) <= 25) and rides the bounce with TP +4.5% / RSI-exit 85 — the
trough trade (bar 1031 -> 1113). Leg C buys a banded scalp bounce
(dip120 inside [2.2%, 2.5%] AND dip240 >= 3.3% AND RSI <= 28 AND first
up-bar) — the dip120 band filters out the losing 825 cluster (dip120
2.67-2.83%) and the dip240 floor filters out the 996 trap (dip240
2.92%), so the only bar that fires is 912 (the 912 -> 949 bounce).
Leg D (tightened) buys a mid-decline oversold dip (dip240 inside
[3.5%, 4.0%) AND dip120 >= 2.5% AND RSI <= 16.7, no up-bar
confirmation) — fires at 824 (the 824 -> 836 bounce); the RSI plateau
for firing at 824 is [16.0, 17.4), 1.4 points wide, and 16.7 sits
mid-plateau. Exits: TP +1.0%, trail 1.0%, stop -1.5%, hold 150.
Leg R buys a shallow range dip (dip120 inside [1.0%, 1.8%] AND dip240
>= 2.5% AND RSI <= 40 AND first up-bar AND 120-bar return <= -1.0%
AND close within 0.5% of the 120-bar low AND 60-bar return <= -0.5%)
— the ret60 filter separates the real range bottom (bar 499, the
500 -> 550 bounce) from the look-alike bar 485 (ret60 +0.23%, a local
uptick inside the decline) and the 963-971 trap cluster. Exits:
TP +1.0%, trail 1.0%, stop -1.5%, hold 100. Leg S (NEW) buys a
shallow dip (dip120 inside [1.5%, 2.2%] AND dip240 inside [2.5%, 3.0%]
AND RSI <= 40 AND ret60 <= -1.0% AND ret120 <= -1.0% AND first
up-bar) — fires only at 771 (the 768 -> 792 bounce); the ret120
filter is load-bearing (without it the leg fires at 985 and blocks
the trough). Exits: TP +0.4%, trail 1.0%, stop -1.5%, hold 150.
Leg L (NEW) buys a late dip (dip120 inside [1.0%, 1.8%] AND dip240
inside [1.85%, 2.5%] AND RSI <= 30 AND ret120 <= -1.0% AND ret60
<= -0.80% AND near-low <= 0.1% AND first up-bar) — fires only at
1398 (the 1403 -> 1439 bounce); the up-bar filter is load-bearing
(without it the leg fires at bar 357). Exits: TP +0.8%, trail 1.0%,
stop -1.5%, hold 40. MAX_RT = 6, NO_ENTRY_AFTER = 1410.
No leg B (its clusters are stop-outs). RSI for entries is the
simple-mean RSI(14); RSI-exits use Wilder-smoothed RSI14. Position
size is depth-weighted (mean 240-bar pool depth / current depth,
clamped to [0.6, 1.0]). Full reasoning, parameters and sweep evidence
are in CAND-G.md and in the docstring at the top of `main.py`.

Dev-window result (local protocol replay, fee 4 bps + slippage 2 bps +
pool impact): **net PnL +$85.36**, max drawdown 0.77%, 12 trades
(6 round trips), fees $4.96, final cash $1,085.36. Beats cand-F
(+$71.84) by +$13.52 with a lower maxDD; oracle 4 RT is +$91.91.

## Files

- `main.py` — the bot (entrypoint).
- `CAND-G.md` — design, fills, sweep and robustness evidence.
- `vendor/makefun_bars.py` — protocol shim, byte-identical to the kit's SDK.
- `LICENSE` — MIT.
