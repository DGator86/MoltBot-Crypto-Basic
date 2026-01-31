"""Test CoinGecko API integration"""
import os
import sys

# Add packages to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'packages', 'research_lab'))


def test_coingecko_module_loads():
    """Test that the CoinGecko module can be imported"""
    import importlib.util
    
    module_path = os.path.join(os.path.dirname(__file__), '..', 'packages', 'research_lab', 'research_lab', 'data_sources', 'coingecko.py')
    spec = importlib.util.spec_from_file_location("coingecko", module_path)
    coingecko = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(coingecko)
    
    assert coingecko is not None


def test_coingecko_api_key_configuration():
    """Test that CoinGecko uses Pro API when API key is set"""
    # Set API key
    os.environ['COINGECKO_API_KEY'] = 'CG-krJCp3qpAfGUnTb5qDXezUzz'
    
    # Direct import of the module
    import sys
    import importlib.util
    
    module_path = os.path.join(os.path.dirname(__file__), '..', 'packages', 'research_lab', 'research_lab', 'data_sources', 'coingecko.py')
    spec = importlib.util.spec_from_file_location("coingecko", module_path)
    coingecko = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(coingecko)
    
    # Verify Pro API is used
    assert coingecko.API_KEY == 'CG-krJCp3qpAfGUnTb5qDXezUzz'
    assert coingecko.BASE == 'https://pro-api.coingecko.com/api/v3'


def test_coingecko_no_api_key_configuration():
    """Test that CoinGecko uses public API when no API key is set"""
    # Clear API key
    if 'COINGECKO_API_KEY' in os.environ:
        del os.environ['COINGECKO_API_KEY']
    
    # Direct import of the module
    import sys
    import importlib.util
    
    module_path = os.path.join(os.path.dirname(__file__), '..', 'packages', 'research_lab', 'research_lab', 'data_sources', 'coingecko.py')
    spec = importlib.util.spec_from_file_location("coingecko_no_key", module_path)
    coingecko = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(coingecko)
    
    # Verify public API is used
    assert coingecko.API_KEY == ''
    assert coingecko.BASE == 'https://api.coingecko.com/api/v3'


def test_market_chart_function_signature():
    """Test that market_chart function has correct signature"""
    import importlib.util
    import inspect
    
    module_path = os.path.join(os.path.dirname(__file__), '..', 'packages', 'research_lab', 'research_lab', 'data_sources', 'coingecko.py')
    spec = importlib.util.spec_from_file_location("coingecko", module_path)
    coingecko = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(coingecko)
    
    sig = inspect.signature(coingecko.market_chart)
    params = list(sig.parameters.keys())
    
    assert 'symbol_id' in params
    assert 'vs_currency' in params
    assert 'days' in params
