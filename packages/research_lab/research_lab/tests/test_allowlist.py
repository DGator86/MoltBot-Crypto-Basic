from research_lab.ingest.allowlist import allowed

def test_allowlist():
    assert allowed('https://api.coingecko.com/api/v3/ping')
    assert not allowed('https://example.com')
