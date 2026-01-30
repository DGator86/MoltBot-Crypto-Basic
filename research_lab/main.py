"""
Research Lab - Backtest Freqtrade strategies, pull data from CoinGecko, DeFiLlama, CryptoPanic
"""
import os
import requests
import pandas as pd
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import importlib.util
import sys

class ExternalDataFetcher:
    """Fetch data from external APIs"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
        
        # Allowlist for web fetch
        self.allowed_domains = [
            'api.coingecko.com',
            'pro-api.coingecko.com',
            'api.llama.fi',
            'cryptopanic.com'
        ]
    
    def init_database(self):
        """Initialize database for research data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS coingecko_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coin_id TEXT,
                timestamp INTEGER,
                price REAL,
                market_cap REAL,
                volume REAL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS defillama_tvl (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                protocol TEXT,
                timestamp INTEGER,
                tvl REAL,
                chain TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cryptopanic_news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                news_id TEXT UNIQUE,
                timestamp INTEGER,
                title TEXT,
                url TEXT,
                sentiment TEXT,
                currencies TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def fetch_coingecko_price(self, coin_id: str = "bitcoin") -> Dict:
        """Fetch price data from CoinGecko"""
        api_key = os.getenv("COINGECKO_API_KEY", "")
        
        # Use Pro API if key available, otherwise public API
        if api_key:
            url = f"https://pro-api.coingecko.com/api/v3/simple/price"
            headers = {"x-cg-pro-api-key": api_key}
        else:
            url = f"https://api.coingecko.com/api/v3/simple/price"
            headers = {}
        
        params = {
            "ids": coin_id,
            "vs_currencies": "usd",
            "include_market_cap": "true",
            "include_24hr_vol": "true"
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Save to database
            if coin_id in data:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO coingecko_prices (coin_id, timestamp, price, market_cap, volume)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    coin_id,
                    int(datetime.utcnow().timestamp()),
                    data[coin_id].get('usd', 0),
                    data[coin_id].get('usd_market_cap', 0),
                    data[coin_id].get('usd_24h_vol', 0)
                ))
                conn.commit()
                conn.close()
            
            return data
        except Exception as e:
            print(f"Error fetching CoinGecko data: {e}")
            return {}
    
    def fetch_defillama_tvl(self, protocol: str = "aave") -> Dict:
        """Fetch TVL data from DeFiLlama"""
        url = f"https://api.llama.fi/protocol/{protocol}"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Save to database
            if 'tvl' in data:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                for tvl_point in data.get('chainTvls', {}).get('Ethereum', {}).get('tvl', []):
                    cursor.execute("""
                        INSERT INTO defillama_tvl (protocol, timestamp, tvl, chain)
                        VALUES (?, ?, ?, ?)
                    """, (protocol, tvl_point['date'], tvl_point['totalLiquidityUSD'], 'Ethereum'))
                
                conn.commit()
                conn.close()
            
            return data
        except Exception as e:
            print(f"Error fetching DeFiLlama data: {e}")
            return {}
    
    def fetch_cryptopanic_news(self, currencies: str = "BTC") -> List[Dict]:
        """Fetch news from CryptoPanic"""
        api_key = os.getenv("CRYPTOPANIC_API_KEY", "")
        if not api_key:
            print("CryptoPanic API key not set")
            return []
        
        url = "https://cryptopanic.com/api/v1/posts/"
        params = {
            "auth_token": api_key,
            "currencies": currencies,
            "kind": "news"
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Save to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for news in data.get('results', []):
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO cryptopanic_news 
                        (news_id, timestamp, title, url, sentiment, currencies)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        str(news['id']),
                        int(datetime.fromisoformat(news['published_at'].replace('Z', '+00:00')).timestamp()),
                        news['title'],
                        news['url'],
                        news.get('metadata', {}).get('sentiment', 'neutral'),
                        json.dumps(news.get('currencies', []))
                    ))
                except Exception as e:
                    print(f"Error inserting news: {e}")
            
            conn.commit()
            conn.close()
            
            return data.get('results', [])
        except Exception as e:
            print(f"Error fetching CryptoPanic data: {e}")
            return []

class FreqtradeStrategyLoader:
    """Load and validate Freqtrade strategies"""
    
    def __init__(self, strategy_dir: str = "/app/strategies"):
        self.strategy_dir = strategy_dir
        os.makedirs(strategy_dir, exist_ok=True)
    
    def load_strategy(self, strategy_name: str):
        """Load a Freqtrade strategy from file"""
        strategy_path = os.path.join(self.strategy_dir, f"{strategy_name}.py")
        
        if not os.path.exists(strategy_path):
            raise FileNotFoundError(f"Strategy {strategy_name} not found")
        
        # Load the module
        spec = importlib.util.spec_from_file_location(strategy_name, strategy_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[strategy_name] = module
        spec.loader.exec_module(module)
        
        # Find the strategy class
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and attr_name != 'IStrategy':
                return attr
        
        raise ValueError(f"No strategy class found in {strategy_name}")
    
    def list_strategies(self) -> List[str]:
        """List all available strategies"""
        strategies = []
        for file in os.listdir(self.strategy_dir):
            if file.endswith('.py') and not file.startswith('_'):
                strategies.append(file[:-3])
        return strategies

class Backtester:
    """Simple backtesting engine with fees and slippage"""
    
    def __init__(self, initial_capital: float = 10000.0, 
                 fee_rate: float = 0.001, slippage_rate: float = 0.0005):
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
        self.slippage_rate = slippage_rate
    
    def calculate_fees(self, amount: float) -> float:
        """Calculate trading fees"""
        return amount * self.fee_rate
    
    def calculate_slippage(self, amount: float) -> float:
        """Calculate slippage"""
        return amount * self.slippage_rate
    
    def backtest(self, data: pd.DataFrame, strategy) -> Dict:
        """
        Run backtest on historical data
        
        Args:
            data: DataFrame with OHLCV data
            strategy: Strategy instance with populate_indicators and populate_entry_trend
        
        Returns:
            Dictionary with backtest results
        """
        capital = self.initial_capital
        position = 0.0
        trades = []
        
        # This is a simplified backtest - real implementation would use the strategy
        for i in range(len(data)):
            row = data.iloc[i]
            
            # Simplified buy signal (replace with actual strategy)
            if position == 0 and i > 0:
                # Buy
                amount_to_invest = capital * 0.95  # Keep some cash
                fees = self.calculate_fees(amount_to_invest)
                slippage = self.calculate_slippage(amount_to_invest)
                cost = amount_to_invest + fees + slippage
                
                if cost <= capital:
                    position = amount_to_invest / row['close']
                    capital -= cost
                    trades.append({
                        'type': 'buy',
                        'price': row['close'],
                        'amount': position,
                        'timestamp': row['timestamp']
                    })
            
            # Simplified sell signal
            elif position > 0 and i > 10:
                # Sell
                sale_value = position * row['close']
                fees = self.calculate_fees(sale_value)
                slippage = self.calculate_slippage(sale_value)
                proceeds = sale_value - fees - slippage
                
                capital += proceeds
                trades.append({
                    'type': 'sell',
                    'price': row['close'],
                    'amount': position,
                    'timestamp': row['timestamp']
                })
                position = 0.0
        
        # Close any open position
        if position > 0:
            sale_value = position * data.iloc[-1]['close']
            fees = self.calculate_fees(sale_value)
            slippage = self.calculate_slippage(sale_value)
            capital += sale_value - fees - slippage
        
        final_value = capital
        profit = final_value - self.initial_capital
        profit_pct = (profit / self.initial_capital) * 100
        
        return {
            'initial_capital': self.initial_capital,
            'final_value': final_value,
            'profit': profit,
            'profit_pct': profit_pct,
            'trades': trades,
            'num_trades': len(trades)
        }
    
    def walk_forward(self, data: pd.DataFrame, strategy, 
                    train_window: int = 100, test_window: int = 20) -> List[Dict]:
        """
        Walk-forward optimization
        
        Args:
            data: Full dataset
            train_window: Size of training window
            test_window: Size of test window
            strategy: Strategy to test
        
        Returns:
            List of backtest results for each window
        """
        results = []
        
        for i in range(0, len(data) - train_window - test_window, test_window):
            # Train window
            train_data = data.iloc[i:i+train_window]
            
            # Test window
            test_data = data.iloc[i+train_window:i+train_window+test_window]
            
            # Run backtest on test window
            result = self.backtest(test_data, strategy)
            result['window_start'] = i + train_window
            result['window_end'] = i + train_window + test_window
            results.append(result)
        
        return results

def main():
    """Main entry point for research lab"""
    db_path = os.getenv("DATABASE_URL", "sqlite:///data/research.db").replace("sqlite:///", "")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Initialize components
    fetcher = ExternalDataFetcher(db_path)
    strategy_loader = FreqtradeStrategyLoader()
    backtester = Backtester()
    
    # Fetch external data
    print("Fetching CoinGecko data...")
    fetcher.fetch_coingecko_price("bitcoin")
    fetcher.fetch_coingecko_price("ethereum")
    
    print("Fetching DeFiLlama data...")
    fetcher.fetch_defillama_tvl("aave")
    
    print("Fetching CryptoPanic news...")
    fetcher.fetch_cryptopanic_news("BTC,ETH")
    
    print("Research Lab initialized successfully")

if __name__ == "__main__":
    main()
