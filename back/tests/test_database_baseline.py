"""Public database baseline contract tests."""
from pathlib import Path

from alembic.script import ScriptDirectory


BACKEND_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = BACKEND_ROOT / "migrations"
BASELINE_REVISION = "public_schema_baseline"
COMPATIBILITY_REVISION = "drop_billing_appointment"
SCHEMA_COMPAT_REVISION = "public_schema_compat"
REQUEST_ID_REVISION = "agentteams_request_id"
LAUNCH_INTENTS_REVISION = "agentteams_launch_intents"
PAYLOAD_RETENTION_REVISION = "agentteams_payload_retention"
MANUAL_REVIEW_AUDIT_REVISION = "agentteams_review_audit"
DROP_PROMPT_CONFIG_REVISION = "drop_prompt_config_system_prompt"
SHARE_TOKEN_REVISION = "share_token_256bit"
DROP_FOLLOW_UP_REVISION = "drop_follow_up_reminder"


def test_public_migration_graph_is_tracked_and_self_contained():
    script = ScriptDirectory(str(MIGRATIONS_DIR))
    revisions = list(script.walk_revisions())

    assert [revision.revision for revision in revisions] == [
        DROP_FOLLOW_UP_REVISION,
        SHARE_TOKEN_REVISION,
        DROP_PROMPT_CONFIG_REVISION,
        MANUAL_REVIEW_AUDIT_REVISION,
        PAYLOAD_RETENTION_REVISION,
        LAUNCH_INTENTS_REVISION,
        REQUEST_ID_REVISION,
        SCHEMA_COMPAT_REVISION,
        COMPATIBILITY_REVISION,
        BASELINE_REVISION,
    ]
    assert script.get_base() == BASELINE_REVISION
    assert script.get_current_head() == DROP_FOLLOW_UP_REVISION

    alembic_config = (BACKEND_ROOT / "alembic.ini").read_text(encoding="utf-8")
    dockerignore = (BACKEND_ROOT / ".dockerignore").read_text(encoding="utf-8")
    assert "migrations/private_versions" not in alembic_config
    assert "migrations/private_versions/" in dockerignore


def test_public_baseline_is_a_static_schema_snapshot():
    baseline_path = next(
        (MIGRATIONS_DIR / "versions").glob("*public_schema_baseline.py")
    )
    source = baseline_path.read_text(encoding="utf-8")

    assert "down_revision: Union[str, None] = None" in source
    # 向量搜索已移除：基线迁移不得再依赖 pgvector 扩展（防回归守卫）
    assert "CREATE EXTENSION" not in source
    assert "consultation_external_sessions" in source
    assert "Base.metadata" not in source
    assert "from app." not in source


def test_private_deployment_compatibility_marker_is_noop_after_baseline():
    script = ScriptDirectory(str(MIGRATIONS_DIR))
    compatibility = script.get_revision(COMPATIBILITY_REVISION)
    source = Path(compatibility.path).read_text(encoding="utf-8")

    assert compatibility.down_revision == BASELINE_REVISION
    assert "op." not in source
    assert "drop_table" not in source
    assert "create_table" not in source


def test_schema_compatibility_revision_follows_private_deployment_marker():
    script = ScriptDirectory(str(MIGRATIONS_DIR))
    compatibility = script.get_revision(SCHEMA_COMPAT_REVISION)
    source = Path(compatibility.path).read_text(encoding="utf-8")

    assert compatibility.down_revision == COMPATIBILITY_REVISION
    assert "private_versions" not in source
    assert "consultation_external_sessions" in source


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
    assert 'RUN_DB_MIGRATIONS="${RUN_DB_MIGRATIONS:-true}"' in entrypoint
    assert "跳过 schema 迁移和种子初始化" in entrypoint
