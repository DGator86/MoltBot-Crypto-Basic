# Particle Bot (Timeframe-Agnostic, Prints-First)

Two reference packages were added under `packages/particle_bot/`:

- `mvp/` – minimal particle-regime MVP (event bus, features, regimes, fields, trajectory)
- `derivs/` – extended version with derivatives feeds (Binance futures, OKX public) and record/replay

These are research utilities. They are not wired to live trading. Use them to:

- Record market data and write append-only raw events
- Compute regime stack and trajectory cone
- Deterministically replay sessions for evaluation

Quick start (example):

```bash
# Example (from packages/particle_bot/derivs)
cd packages/particle_bot/derivs
python -m venv .venv && source .venv/bin/activate
pip install -e .
# See README.md inside for CLI flags like --mode record / --mode replayfile
```

Integration plan:
- Near-term: expose an adapter so Research Lab can ingest recorded JSONL/parquet events from particle bot
- Later: unify canonical event schema with market_data package and run shared feature/regime pipeline
