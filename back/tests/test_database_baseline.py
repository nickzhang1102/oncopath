"""Public database baseline contract tests."""
from pathlib import Path

from alembic.script import ScriptDirectory


BACKEND_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = BACKEND_ROOT / "migrations"
BASELINE_REVISION = "public_schema_baseline"


def test_public_migration_graph_has_one_root_and_head():
    script = ScriptDirectory(str(MIGRATIONS_DIR))
    revisions = list(script.walk_revisions())

    assert [revision.revision for revision in revisions] == [BASELINE_REVISION]
    assert script.get_base() == BASELINE_REVISION
    assert script.get_current_head() == BASELINE_REVISION


def test_public_baseline_is_a_static_schema_snapshot():
    baseline_path = next(
        (MIGRATIONS_DIR / "versions").glob("*public_schema_baseline.py")
    )
    source = baseline_path.read_text(encoding="utf-8")

    assert "down_revision: Union[str, None] = None" in source
    assert "CREATE EXTENSION IF NOT EXISTS vector" in source
    assert "Base.metadata" not in source
    assert "from app." not in source


def test_entrypoint_migrates_before_running_idempotent_seeds():
    entrypoint = (BACKEND_ROOT / "docker-entrypoint.sh").read_text(encoding="utf-8")
    seed_script = (BACKEND_ROOT / "scripts" / "init_fresh_db.py").read_text(
        encoding="utf-8"
    )

    migration_position = entrypoint.index("alembic -c /app/alembic.ini upgrade head")
    seed_position = entrypoint.index("python scripts/init_fresh_db.py")

    assert migration_position < seed_position
    assert "create_all" not in seed_script
    assert "stamp_alembic" not in seed_script
