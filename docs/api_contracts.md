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

- POST /simulate/paper { ohlcv, orders, config? }
- POST /sweeps/start { ohlcv, fast_range, slow_range, fee_bps?, slippage_bps?, max_workers? }
- GET /sweeps/status/{sweep_id}

- POST /learn/regime/start { ohlcv, level, windows? } -> async training; returns job_id
- GET /learn/regime/status/{job_id} -> training status and model path
- POST /score/regime { ohlcv, level } -> predictions and probabilities

Levels supported: kingdom, phylum, clazz (positioning), order (liquidity topology), family (microstructure). For clazz, you can pass aux: { funding:[], oi:[], basis:[] } aligned to ohlcv.

- POST /ingest/derivs { path, ohlcv? } -> extracts funding/oi/basis arrays and builds volume profile/HVN/LVN if ohlcv provided
