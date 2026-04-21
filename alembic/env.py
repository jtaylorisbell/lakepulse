"""Alembic environment — resolves Lakebase connection via Databricks SDK."""

from logging.config import fileConfig
from urllib.parse import quote_plus

from sqlalchemy import engine_from_config, pool

from alembic import context
from config import LakebaseSettings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def _build_url(lb: LakebaseSettings) -> str:
    """Build a SQLAlchemy database URL from LakebaseSettings + OAuth."""
    host = lb.get_host()
    user = lb.get_user()
    password = lb.get_password()
    return (
        f"postgresql+psycopg://{quote_plus(user)}:{quote_plus(password)}"
        f"@{host}:5432/{lb.database}"
        f"?sslmode=require&connect_timeout=30&options=-csearch_path%3Dlakepulse"
    )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL without connecting)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode — connect to Lakebase via OAuth."""
    from sqlalchemy import create_engine

    lb = LakebaseSettings()
    url = _build_url(lb)
    connectable = create_engine(url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        from sqlalchemy import text
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS lakepulse"))
        connection.commit()
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
