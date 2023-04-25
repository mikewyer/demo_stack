"""Unit tests for frontend/app"""

from frontend import app


def test_health() -> None:
    """Checks health check has been implemented"""
    assert app.health_check() == "ok"
