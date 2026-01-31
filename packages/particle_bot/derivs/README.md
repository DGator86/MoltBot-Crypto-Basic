# Particle Bot (prints-first, timeframe-agnostic)

This project treats **price as a single particle** that is continuously re-rendered by **prints (trades)** moving through a multi-field potential landscape.
“Timeframe agnostic” is implemented as **scale space**: micro → minor → major → macro (like your kingdom/phylum/class/family analogy), where each level has different definitions and thresholds.

What you get right now:
- **Live or replayable** event pipeline (trade prints + top-of-book deltas)
- Multi-scale **feature engine** (returns, CVD, imbalance proxies, etc.)
- Hierarchical **regime taxonomy** (Kingdom/Phylum/Class/Family)
- Price-grid **liquidity + positioning potentials**
- Monte Carlo **trajectory cone** over event-steps (not minutes)

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Run (LIVE) — Binance USD-M Futures (default)

Records normalized events to `data/raw/events.jsonl` and writes snapshots to `data/derived/snapshots.jsonl`.

Binance live mode ingests:
- aggTrade (prints)
- depth (partial book)
- markPrice stream (mark + index + funding)
- REST polling for open interest + basis

```bash
particle-bot --mode record --venue binance --symbols BTC,ETH,SOL
```

Stop after a fixed number of events (useful for testing):

```bash
particle-bot --mode record --venue binance --symbols BTC --max-events 5000
```

## Run (LIVE) — OKX Spot (public WS)

```bash
particle-bot --mode record --venue okx --symbols BTC,ETH,SOL --max-events 5000
```

## Replay a recorded session (deterministic)

```bash
particle-bot --mode replayfile --in data/raw/events.jsonl --max-events 200000
```

This replays the exact event order back through the same feature + regime + cone pipeline.

## Synthetic demo (no internet)

```bash
particle-bot --mode synthetic --symbols BTC --steps 3000
```

## Outputs

- `data/raw/events.jsonl` — normalized events (TradePrint / BookDelta / FundingTick / OITick / BasisTick)
- `data/derived/snapshots.jsonl` — per-snapshot outputs:
  - features at each scale
  - regime stack
  - cone summary (quantile bands)

## Config

Edit `config/default.yaml`:
- `snapshot_every_trades`: snapshot cadence (trade prints, not candles)
- `book_depth`: depth levels used for the liquidity field
- `scales`: your “taxonomy” zoom levels
- `cone`: Monte Carlo cone steps + path count

Binance-specific (optional):
- `binance.oi_poll_s`, `binance.basis_poll_s`, `binance.basis_period`, `binance.depth_ms`

## Notes (tell-it-like-it-is)

- This is **not** a profitable bot yet. It’s an engine scaffold:
  - ingestion → normalization → features → taxonomy → fields → forecast cone
- The cone is currently **heuristic physics** (OU-ish + potential gradient), not a trained model.
- The fastest path to real edge is: add liquidation maps, options positioning, and a learned regime router.

