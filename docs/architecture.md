# Architecture
Two services (trading_core, research_lab) + a thin moltbot_bridge. Market data and execution adapters are libraries used by trading_core. Research_lab has no keys and runs with network allowlist only.
