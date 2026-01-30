# Runbook
- docker compose up --build
- Check http://localhost:8001/health and :8002/health

Research API quick test:
- POST /backtest with ohlcv: [{"close":100}, ...]
- POST /evaluate similarly; /promote with candidate JSON.
