# MoltBot/OpenClaw Crypto Trader

A comprehensive cryptocurrency trading system with FastAPI backend, market data collection, research lab for backtesting, and TypeScript bridge for command-line control.

## Features

### Trading Core (FastAPI)
- **Exchange Integration**: Binance and Coinbase execution via CCXT and Coinbase Advanced Trade
- **Risk Management**: Hard risk kernel with position size and exposure limits
- **Safety Controls**: Flatten all positions and kill switch functionality
- **Order Management**: Market and limit orders with approval workflow

### Market Data Service
- **Real-time Data**: Binance WebSocket streams for depth, trades, and klines
- **Storage**: Dual storage in Parquet files and SQLite database
- **Efficient Processing**: Buffered writes for optimal performance

### Research Lab
- **Strategy Support**: Ingest and test Freqtrade strategies
- **Backtesting**: Walk-forward testing with realistic fees and slippage
- **External Data**: Integration with CoinGecko, DeFiLlama, and CryptoPanic

### TypeScript Moltbot Bridge
- **CLI Commands**: `status`, `positions`, `pause`, `flatten`, `propose`, `approve`
- **API Client**: Full-featured TypeScript client for Trading Core API

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Moltbot Bridge │────▶│  Trading Core    │────▶│  Exchanges      │
│  (TypeScript)   │     │  (FastAPI)       │     │  (Binance/CB)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               │
                        ┌──────▼──────────┐
                        │  Market Data    │
                        │  (WebSocket)    │
                        └──────┬──────────┘
                               │
                        ┌──────▼──────────┐
                        │  Research Lab   │
                        │  (Backtest)     │
                        └─────────────────┘
```

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker and Docker Compose (optional)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/DGator86/MoltBot-Crypto-Basic.git
cd MoltBot-Crypto-Basic
```

2. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. **Using Docker Compose (Recommended)**
```bash
docker-compose up -d
```

4. **Manual Setup**

**Python Services:**
```bash
# Install Python dependencies
pip install -r requirements.txt

# Run Trading Core
python -m uvicorn trading_core.main:app --host 0.0.0.0 --port 8000

# Run Market Data (in separate terminal)
python market_data/main.py

# Run Research Lab (in separate terminal)
python research_lab/main.py
```

**TypeScript Bridge:**
```bash
# Install Node dependencies
npm install

# Build TypeScript
npm run build

# Use CLI
node dist/index.js status
```

## Usage

### Trading Core API

**Check Status:**
```bash
curl http://localhost:8000/status
```

**Get Positions:**
```bash
curl http://localhost:8000/positions
```

**Pause Trading:**
```bash
curl -X POST http://localhost:8000/pause
```

**Flatten All Positions:**
```bash
curl -X POST http://localhost:8000/flatten
```

**Activate Kill Switch:**
```bash
curl -X POST http://localhost:8000/kill-switch
```

### Moltbot Bridge CLI

**Get Status:**
```bash
node dist/index.js status
```

**View Positions:**
```bash
node dist/index.js positions
```

**Pause Trading:**
```bash
node dist/index.js pause
```

**Flatten Positions:**
```bash
node dist/index.js flatten
```

**Propose a Trade:**
```bash
node dist/index.js propose \
  --exchange binance \
  --symbol BTC/USDT \
  --side buy \
  --type market \
  --amount 0.001
```

**Approve and Execute:**
```bash
node dist/index.js approve \
  --id <proposal_id> \
  --exchange binance \
  --symbol BTC/USDT \
  --side buy \
  --type market \
  --amount 0.001
```

## Configuration

### Risk Limits
Default risk limits are defined in `trading_core/main.py`:
- Max Position Size: $10,000
- Max Total Exposure: $50,000
- Max Leverage: 3x

### Allowlisted Domains
External API access is restricted to allowlisted domains in `config.py`:
- CoinGecko (api.coingecko.com)
- DeFiLlama (api.llama.fi)
- CryptoPanic (cryptopanic.com)
- Exchange APIs (Binance, Coinbase)

### Market Data Symbols
Default symbols for market data collection (in `market_data/main.py`):
- BTC/USDT
- ETH/USDT
- BNB/USDT

## Security

### CI/CD Security Scans
- **Python**: Safety (dependency scan) and Bandit (code scan)
- **TypeScript**: npm audit
- **Docker**: Trivy vulnerability scanning
- **Dependencies**: GitHub Dependency Review

### Best Practices
- All dependencies are pinned to specific versions
- Regular security scans via GitHub Actions
- Allowlisted domains for external API access
- Environment variables for sensitive credentials
- Risk limits enforced at the kernel level

## Development

### Running Tests

**Python:**
```bash
pytest --cov=trading_core --cov=market_data --cov=research_lab
```

**TypeScript:**
```bash
npm test
```

### Project Structure
```
MoltBot-Crypto-Basic/
├── trading_core/          # FastAPI trading engine
│   └── main.py
├── market_data/           # WebSocket data collection
│   └── main.py
├── research_lab/          # Backtesting and research
│   └── main.py
├── moltbot_bridge/        # TypeScript CLI bridge
│   └── src/
│       ├── bridge.ts
│       └── index.ts
├── .github/
│   └── workflows/
│       └── security.yml   # CI/CD with security scans
├── Dockerfile.*           # Docker images for each service
├── docker-compose.yml     # Multi-service orchestration
├── requirements.txt       # Python dependencies (pinned)
├── package.json          # Node dependencies (pinned)
└── config.py             # Allowlisted domains
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and security scans
5. Submit a pull request

## License

MIT License

## Disclaimer

This software is for educational purposes only. Trading cryptocurrencies carries significant risk. Always test thoroughly with paper trading before using real funds.