"""Public deployment readiness endpoint coverage."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.responses import JSONResponse

import app.main as main_module
from app.main import app, health_check


def test_health_routes_include_reverse_proxy_path():
    paths = {route.path for route in app.routes}

    assert "/health" in paths
    assert "/api/v1/health" in paths


def _connection_context(execute_side_effect=None):
    connection = AsyncMock()
    connection.execute.side_effect = execute_side_effect
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=connection)
    context.__aexit__ = AsyncMock(return_value=False)
    return context


@pytest.mark.asyncio
async def test_health_check_reports_database_readiness(monkeypatch):
    test_engine = MagicMock()
    test_engine.connect.return_value = _connection_context()
    monkeypatch.setattr(
        main_module,
        "engine",
        test_engine,
    )

    response = await health_check()

    assert response["status"] == "ok"
    assert response["database_ready"] is True


@pytest.mark.asyncio
async def test_health_check_returns_503_when_database_is_unavailable(monkeypatch):
    test_engine = MagicMock()
    test_engine.connect.return_value = _connection_context(RuntimeError("offline"))
    monkeypatch.setattr(
        main_module,
        "engine",
        test_engine,
    )

    response = await health_check()

    assert isinstance(response, JSONResponse)
    assert response.status_code == 503
    assert json.loads(response.body) == {
        "status": "unavailable",
        "version": "2.0.0",
        "database_ready": False,
    }
