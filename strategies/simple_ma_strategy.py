"""
Example Freqtrade strategy for testing
This is a simple moving average crossover strategy
"""
import pandas as pd

class SimpleMAStrategy:
    """
    Simple Moving Average Crossover Strategy
    Buy when fast MA crosses above slow MA
    Sell when fast MA crosses below slow MA
    """
    
    # Strategy parameters
    minimal_roi = {
        "0": 0.10,
        "30": 0.05,
        "60": 0.02
    }
    
    stoploss = -0.10
    
    def populate_indicators(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Add indicators to the dataframe
        """
        # Calculate moving averages
        dataframe['sma_fast'] = dataframe['close'].rolling(window=10).mean()
        dataframe['sma_slow'] = dataframe['close'].rolling(window=30).mean()
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Add buy signals to the dataframe
        """
        dataframe.loc[
            (
                (dataframe['sma_fast'] > dataframe['sma_slow']) &
                (dataframe['sma_fast'].shift(1) <= dataframe['sma_slow'].shift(1))
            ),
            'enter_long'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Add sell signals to the dataframe
        """
        dataframe.loc[
            (
                (dataframe['sma_fast'] < dataframe['sma_slow']) &
                (dataframe['sma_fast'].shift(1) >= dataframe['sma_slow'].shift(1))
            ),
            'exit_long'] = 1
        
        return dataframe
