"""Docker Compose startup-order contracts."""

from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _compose() -> dict:
    return yaml.safe_load(
        (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    )


def test_only_backend_owns_database_initialization():
    services = _compose()["services"]

    assert "RUN_DB_MIGRATIONS=true" in services["backend"]["environment"]
    assert (
        "RUN_DB_MIGRATIONS=false"
        in services["agentteams-launch-worker"]["environment"]
    )


def test_launch_worker_waits_for_migrated_healthy_backend():
    services = _compose()["services"]
    backend = services["backend"]
    worker = services["agentteams-launch-worker"]

    assert "/api/v1/health" in " ".join(backend["healthcheck"]["test"])
    assert worker["depends_on"]["backend"] == {
        "condition": "service_healthy"
    }


def test_frontend_waits_for_healthy_backend():
    frontend = _compose()["services"]["frontend"]

    assert frontend["depends_on"]["backend"] == {
        "condition": "service_healthy"
    }
