#!/bin/bash
# Start all services locally

echo "Starting Moltbot/OpenClaw Crypto Trader..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Create data directories
mkdir -p data/parquet

# Start Trading Core in background
echo "Starting Trading Core..."
python -m uvicorn trading_core.main:app --host 0.0.0.0 --port 8000 &
TRADING_CORE_PID=$!

# Wait for Trading Core to start
sleep 3

# Start Market Data in background
echo "Starting Market Data service..."
python market_data/main.py &
MARKET_DATA_PID=$!

# Start Research Lab in background
echo "Starting Research Lab..."
python research_lab/main.py &
RESEARCH_LAB_PID=$!

echo ""
echo "All services started!"
echo "Trading Core PID: $TRADING_CORE_PID"
echo "Market Data PID: $MARKET_DATA_PID"
echo "Research Lab PID: $RESEARCH_LAB_PID"
echo ""
echo "Trading Core API: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services..."

# Wait for interrupt
trap "echo 'Stopping services...'; kill $TRADING_CORE_PID $MARKET_DATA_PID $RESEARCH_LAB_PID; exit 0" SIGINT
wait
