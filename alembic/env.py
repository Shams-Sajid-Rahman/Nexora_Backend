"""Alembic env — target metadata is Base.metadata from all modules.
DATABASE_URL comes from env (falls back to alembic.ini)."""
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.db.base import Base
import app.modules.core.models  # noqa: F401
import app.modules.hr.models  # noqa: F401
import app.modules.payroll.models  # noqa: F401
import app.modules.inventory.models  # noqa: F401
import app.modules.purchase.models  # noqa: F401
import app.modules.sales.models  # noqa: F401
import app.modules.finance.models  # noqa: F401
import app.modules.projects.models  # noqa: F401
import app.modules.support.models  # noqa: F401
import app.modules.reports.models  # noqa: F401
import app.modules.workflow.models  # noqa: F401
import app.modules.ai.models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    cfg = config.get_section(config.config_ini_section, {})
    if os.environ.get("DATABASE_URL"):
        cfg["sqlalchemy.url"] = os.environ["DATABASE_URL"]
    connectable = engine_from_config(cfg, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
