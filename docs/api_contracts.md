# API contracts

trading_core (localhost:8001)
- GET /health
- GET /account
- GET /positions
- POST /orders {venue, symbol, side, type, size, price?} -> routes to Binance via CCXT
- POST /orders/cancel {client_order_id}
- GET /risk -> current risk config
- POST /risk/pause
- POST /risk/resume
- POST /risk/flatten

research_lab (localhost:8002)
- GET /health
- POST /ingest {urls[]}
- GET /candidates

Security:
- Bind services to localhost; keys only in trading_core; Coinbase data-only.
- POST /orders/preview {symbol, side, type, size, price?, mid_price?} -> {ok, slippage_bps, limit_bps}
- POST /risk/telemetry/pnl {pnl_pct} -> enforces daily loss kill switch
