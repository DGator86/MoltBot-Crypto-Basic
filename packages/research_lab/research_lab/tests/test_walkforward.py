import pandas as pd
from research_lab.backtest.walkforward import walkforward

def test_walkforward_runs():
    df = pd.DataFrame({'close': [100 + i*0.1 for i in range(100)]})
    res = walkforward(df, n_splits=2)
    assert isinstance(res, list)
    assert len(res) == 2
