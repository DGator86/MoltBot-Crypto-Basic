# Particle Bot MVP (prints-first, timeframe-agnostic)

This MVP runs **deterministically** on a replayable synthetic event stream and outputs:
- Regime stack (Kingdom/Phylum/Class/Family) at multiple zoom scales
- Simple liquidity/positioning fields on a price grid
- Monte Carlo trajectory "cone" (bands) over event-steps (not minutes)

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
particle-bot --mode replay --symbol BTC --steps 3000 --out data/derived/out.json
```

## Notes
- **Primary truth = prints** (`TRADE_PRINT`). Candle data is never used here.
- "Timeframe agnostic" is implemented via **scale-space windows**: micro/minor/major/macro defined in `scales.py`.

## What you can replace later
- `mock_feed.py` with real exchange websocket collectors
- rule thresholds with learned models
- add ETH/SOL in the same pipeline
