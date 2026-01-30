"""
Market Data Service - Collects market data from Binance WebSocket and stores to Parquet/SQLite
"""
import asyncio
import websockets
import json
import pandas as pd
import sqlite3
from datetime import datetime
import os
from pathlib import Path
from typing import Dict, List
import pyarrow as pa
import pyarrow.parquet as pq

class BinanceWebSocketClient:
    """WebSocket client for Binance market data"""
    
    def __init__(self, symbols: List[str], db_path: str, parquet_dir: str):
        self.symbols = symbols
        self.db_path = db_path
        self.parquet_dir = Path(parquet_dir)
        self.parquet_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self.init_database()
        
        # Data buffers
        self.depth_buffer = []
        self.trades_buffer = []
        self.klines_buffer = []
        self.buffer_size = 100
        
    def init_database(self):
        """Initialize SQLite database with tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Depth table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS depth (
                timestamp INTEGER,
                symbol TEXT,
                bids TEXT,
                asks TEXT,
                PRIMARY KEY (timestamp, symbol)
            )
        """)
        
        # Trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER,
                symbol TEXT,
                price REAL,
                quantity REAL,
                is_buyer_maker INTEGER
            )
        """)
        
        # Klines table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS klines (
                timestamp INTEGER,
                symbol TEXT,
                interval TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                PRIMARY KEY (timestamp, symbol, interval)
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_klines_symbol ON klines(symbol)")
        
        conn.commit()
        conn.close()
    
    def save_to_sqlite(self, table: str, data: List[Dict]):
        """Save data to SQLite"""
        if not data:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if table == 'depth':
                for item in data:
                    cursor.execute("""
                        INSERT OR REPLACE INTO depth (timestamp, symbol, bids, asks)
                        VALUES (?, ?, ?, ?)
                    """, (item['timestamp'], item['symbol'], 
                          json.dumps(item['bids']), json.dumps(item['asks'])))
            
            elif table == 'trades':
                for item in data:
                    cursor.execute("""
                        INSERT INTO trades (timestamp, symbol, price, quantity, is_buyer_maker)
                        VALUES (?, ?, ?, ?, ?)
                    """, (item['timestamp'], item['symbol'], item['price'], 
                          item['quantity'], item['is_buyer_maker']))
            
            elif table == 'klines':
                for item in data:
                    cursor.execute("""
                        INSERT OR REPLACE INTO klines 
                        (timestamp, symbol, interval, open, high, low, close, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (item['timestamp'], item['symbol'], item['interval'],
                          item['open'], item['high'], item['low'], 
                          item['close'], item['volume']))
            
            conn.commit()
        finally:
            conn.close()
    
    def save_to_parquet(self, table: str, data: List[Dict]):
        """Save data to Parquet files"""
        if not data:
            return
        
        df = pd.DataFrame(data)
        
        # Partition by date
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms').dt.date
        
        for date, group in df.groupby('date'):
            parquet_file = self.parquet_dir / table / f"{date}.parquet"
            parquet_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Append or create
            if parquet_file.exists():
                existing_df = pd.read_parquet(parquet_file)
                combined_df = pd.concat([existing_df, group], ignore_index=True)
                combined_df.to_parquet(parquet_file, index=False)
            else:
                group.to_parquet(parquet_file, index=False)
    
    async def handle_depth(self, msg: Dict):
        """Handle depth/orderbook updates"""
        data = {
            'timestamp': msg['E'],
            'symbol': msg['s'],
            'bids': msg['b'][:10],  # Top 10 bids
            'asks': msg['a'][:10],  # Top 10 asks
        }
        
        self.depth_buffer.append(data)
        
        if len(self.depth_buffer) >= self.buffer_size:
            self.save_to_sqlite('depth', self.depth_buffer)
            self.save_to_parquet('depth', self.depth_buffer)
            self.depth_buffer = []
    
    async def handle_trade(self, msg: Dict):
        """Handle trade updates"""
        data = {
            'timestamp': msg['T'],
            'symbol': msg['s'],
            'price': float(msg['p']),
            'quantity': float(msg['q']),
            'is_buyer_maker': int(msg['m'])
        }
        
        self.trades_buffer.append(data)
        
        if len(self.trades_buffer) >= self.buffer_size:
            self.save_to_sqlite('trades', self.trades_buffer)
            self.save_to_parquet('trades', self.trades_buffer)
            self.trades_buffer = []
    
    async def handle_kline(self, msg: Dict):
        """Handle kline/candlestick updates"""
        k = msg['k']
        if k['x']:  # Only process closed candles
            data = {
                'timestamp': k['t'],
                'symbol': msg['s'],
                'interval': k['i'],
                'open': float(k['o']),
                'high': float(k['h']),
                'low': float(k['l']),
                'close': float(k['c']),
                'volume': float(k['v'])
            }
            
            self.klines_buffer.append(data)
            
            if len(self.klines_buffer) >= self.buffer_size:
                self.save_to_sqlite('klines', self.klines_buffer)
                self.save_to_parquet('klines', self.klines_buffer)
                self.klines_buffer = []
    
    async def subscribe_depth(self, symbol: str):
        """Subscribe to depth updates for a symbol"""
        stream = f"{symbol.lower()}@depth20@100ms"
        url = f"wss://stream.binance.com:9443/ws/{stream}"
        
        async with websockets.connect(url) as ws:
            print(f"Connected to depth stream for {symbol}")
            async for message in ws:
                msg = json.loads(message)
                await self.handle_depth(msg)
    
    async def subscribe_trades(self, symbol: str):
        """Subscribe to trade updates for a symbol"""
        stream = f"{symbol.lower()}@trade"
        url = f"wss://stream.binance.com:9443/ws/{stream}"
        
        async with websockets.connect(url) as ws:
            print(f"Connected to trades stream for {symbol}")
            async for message in ws:
                msg = json.loads(message)
                await self.handle_trade(msg)
    
    async def subscribe_klines(self, symbol: str, interval: str = "1m"):
        """Subscribe to kline updates for a symbol"""
        stream = f"{symbol.lower()}@kline_{interval}"
        url = f"wss://stream.binance.com:9443/ws/{stream}"
        
        async with websockets.connect(url) as ws:
            print(f"Connected to klines stream for {symbol} ({interval})")
            async for message in ws:
                msg = json.loads(message)
                await self.handle_kline(msg)
    
    async def run(self):
        """Run all WebSocket subscriptions"""
        tasks = []
        
        for symbol in self.symbols:
            tasks.append(asyncio.create_task(self.subscribe_depth(symbol)))
            tasks.append(asyncio.create_task(self.subscribe_trades(symbol)))
            tasks.append(asyncio.create_task(self.subscribe_klines(symbol, "1m")))
            tasks.append(asyncio.create_task(self.subscribe_klines(symbol, "5m")))
        
        await asyncio.gather(*tasks)

async def main():
    """Main entry point"""
    # Configuration
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    db_path = os.getenv("DATABASE_URL", "sqlite:///data/market_data.db").replace("sqlite:///", "")
    parquet_dir = os.getenv("PARQUET_DIR", "/app/data/parquet")
    
    # Ensure data directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Create client and run
    client = BinanceWebSocketClient(symbols, db_path, parquet_dir)
    
    try:
        await client.run()
    except KeyboardInterrupt:
        print("Shutting down...")
    except Exception as e:
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
