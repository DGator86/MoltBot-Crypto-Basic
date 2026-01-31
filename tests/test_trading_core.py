"""
Tests for Trading Core API
"""
import pytest
from fastapi.testclient import TestClient
from trading_core.main import app, state

client = TestClient(app)

def test_root():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "Trading Core"

def test_health():
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()
    assert "timestamp" in response.json()

def test_status():
    """Test status endpoint"""
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert "is_paused" in data
    assert "kill_switch_active" in data
    assert "positions_count" in data
    assert "risk_limits" in data

def test_positions():
    """Test positions endpoint"""
    response = client.get("/positions")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_pause_resume():
    """Test pause and resume"""
    # Pause
    response = client.post("/pause")
    assert response.status_code == 200
    assert response.json()["status"] == "paused"
    
    # Verify paused
    status = client.get("/status").json()
    assert status["is_paused"] == True
    
    # Resume
    response = client.post("/resume")
    assert response.status_code == 200
    assert response.json()["status"] == "resumed"
    
    # Verify resumed
    status = client.get("/status").json()
    assert status["is_paused"] == False

def test_propose_trade():
    """Test trade proposal"""
    order = {
        "exchange": "binance",
        "symbol": "BTC/USDT",
        "side": "buy",
        "type": "market",
        "amount": 0.001
    }
    
    response = client.post("/propose", json=order)
    assert response.status_code == 200
    data = response.json()
    assert "proposal_id" in data
    assert "risk_check" in data
    assert "order" in data

def test_risk_check_when_paused():
    """Test that orders fail when trading is paused"""
    # Pause trading
    client.post("/pause")
    
    order = {
        "exchange": "binance",
        "symbol": "BTC/USDT",
        "side": "buy",
        "type": "market",
        "amount": 0.001
    }
    
    # Proposal should show failed risk check
    response = client.post("/propose", json=order)
    assert response.status_code == 200
    data = response.json()
    assert data["risk_check"]["passed"] == False
    assert "paused" in data["risk_check"]["reason"].lower()
    
    # Resume
    client.post("/resume")

def test_kill_switch_deactivate():
    """Test kill switch deactivation"""
    # Deactivate (should work even if not active)
    response = client.post("/kill-switch/deactivate")
    assert response.status_code == 200
    assert "kill_switch_deactivated" in response.json()["status"]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
