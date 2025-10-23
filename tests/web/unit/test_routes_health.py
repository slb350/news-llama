"""
Unit tests for health check endpoints.

Tests for /health/generation endpoint that returns generation metrics.
"""

import pytest
from fastapi.testclient import TestClient
from src.web.app import app
from src.web.services import generation_service


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_metrics():
    """Reset metrics before each test."""
    # Create fresh metrics instance
    generation_service.metrics = generation_service.GenerationMetrics()
    yield


class TestGenerationHealthEndpoint:
    """Tests for GET /health/generation endpoint."""

    def test_health_generation_returns_200(self, client):
        """Should return 200 OK."""
        response = client.get("/health/generation")
        assert response.status_code == 200

    def test_health_generation_returns_json(self, client):
        """Should return JSON response."""
        response = client.get("/health/generation")
        assert response.headers["content-type"] == "application/json"

    def test_health_generation_initial_state(self, client):
        """Should return zeros for fresh metrics."""
        response = client.get("/health/generation")
        data = response.json()

        assert data["total_generated"] == 0
        assert data["total_failed"] == 0
        assert data["success_rate"] == 0
        assert data["average_duration_seconds"] == 0.0
        assert data["queue_depth"] == 0

    def test_health_generation_after_success(self, client):
        """Should reflect recorded success."""
        # Record a success
        generation_service.metrics.record_success(duration_seconds=600.0)

        response = client.get("/health/generation")
        data = response.json()

        assert data["total_generated"] == 1
        assert data["total_failed"] == 0
        assert data["success_rate"] == 1.0
        assert data["average_duration_seconds"] == 600.0

    def test_health_generation_after_failure(self, client):
        """Should reflect recorded failure."""
        # Record a failure
        generation_service.metrics.record_failure()

        response = client.get("/health/generation")
        data = response.json()

        assert data["total_generated"] == 0
        assert data["total_failed"] == 1
        assert data["success_rate"] == 0

    def test_health_generation_mixed_results(self, client):
        """Should calculate correct metrics for mixed results."""
        # Record mixed results
        generation_service.metrics.record_success(600.0)
        generation_service.metrics.record_success(900.0)
        generation_service.metrics.record_failure()

        response = client.get("/health/generation")
        data = response.json()

        assert data["total_generated"] == 2
        assert data["total_failed"] == 1
        # 2 successes out of 3 total
        assert abs(data["success_rate"] - 0.6666666666666666) < 0.0001
        # Average of 600 and 900
        assert data["average_duration_seconds"] == 750.0
