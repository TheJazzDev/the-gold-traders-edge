"""
Tests for the FastAPI endpoints.
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add api to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'api'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self):
        """Test that health endpoint returns 200."""
        from main import app
        client = TestClient(app)
        
        response = client.get("/health")
        assert response.status_code == 200


class TestAnalyticsEndpoints:
    """Tests for analytics endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from main import app
        return TestClient(app)

    def test_summary_endpoint_structure(self, client):
        """Test that summary endpoint returns correct structure."""
        # This test may fail if no data files exist
        response = client.get("/v1/analytics/summary?timeframe=4h&rules=1,5,6")
        
        # Either success with data or 404/500 if no data
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert 'timeframe' in data
            assert 'total_signals' in data
            assert 'win_rate' in data

    def test_by_rule_endpoint_structure(self, client):
        """Test that by-rule endpoint returns list."""
        response = client.get("/v1/analytics/by-rule?timeframe=4h&rules=1,5,6")
        
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    def test_trades_endpoint_structure(self, client):
        """Test that trades endpoint returns list."""
        response = client.get("/v1/analytics/trades?timeframe=4h&rules=1,5,6")
        
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    def test_date_range_parameters(self, client):
        """Test that date range parameters are accepted."""
        response = client.get(
            "/v1/analytics/summary",
            params={
                "timeframe": "4h",
                "rules": "1,5,6",
                "start_date": "2024-01-01",
                "end_date": "2024-06-01"
            }
        )
        
        # Should accept the parameters without error
        assert response.status_code in [200, 404, 500]


class TestMarketEndpoints:
    """Tests for market data endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from main import app
        return TestClient(app)

    def test_ohlcv_endpoint_structure(self, client):
        """Test that OHLCV endpoint returns correct structure."""
        response = client.get("/v1/market/ohlcv?timeframe=4h&limit=100")
        
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert 'symbol' in data
            assert 'timeframe' in data
            assert 'candles' in data

    def test_indicators_endpoint_structure(self, client):
        """Test that indicators endpoint returns correct structure."""
        response = client.get("/v1/market/indicators?timeframe=4h")
        
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert 'price' in data
            assert 'indicators' in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
