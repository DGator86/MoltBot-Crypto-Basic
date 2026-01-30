"""
Configuration for allowlisted web domains
"""

# Allowlisted domains for external API access
ALLOWED_DOMAINS = [
    # CoinGecko
    'api.coingecko.com',
    'pro-api.coingecko.com',
    
    # DeFiLlama
    'api.llama.fi',
    'yields.llama.fi',
    
    # CryptoPanic
    'cryptopanic.com',
    
    # Exchange APIs
    'api.binance.com',
    'api.binance.us',
    'api.coinbase.com',
    'api.exchange.coinbase.com',
    
    # WebSocket endpoints
    'stream.binance.com',
    'ws-feed.exchange.coinbase.com',
]

def is_domain_allowed(url: str) -> bool:
    """Check if a URL's domain is in the allowlist"""
    from urllib.parse import urlparse
    
    parsed = urlparse(url)
    domain = parsed.netloc
    
    return domain in ALLOWED_DOMAINS
