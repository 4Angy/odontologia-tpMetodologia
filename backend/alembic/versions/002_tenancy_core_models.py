"""tenancy core models: extiende `tenant` y `config`, crea `usuario`.

R6: reversibilidad. El downgrade elimina solo los objetos agregados por esta
migración y preserves el esquema base de `0001`.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "002_tenancy_core_models"
down_revision = "0001_cancelacion_turno"
branch_labels = None
depends_on = None


def _slug_value(value: str) -> str:
    import re

    slug = (value or "").strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        slug = "tenant"
    return slug


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return any(
        column["name"] == column_name
        for column in inspector.get_columns(table_name)
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_column(inspector, "tenant", "slug"):
        op.add_column("tenant", sa.Column("slug", sa.String(100), nullable=True))

    """Backfill explícito; si hay conflictos, falla con un mensaje que nombra los tenants."""
    conflicts = bind.execute(
        sa.text(
            """
            SELECT slug, array_agg(id ORDER BY id) AS ids
            FROM (
                SELECT id, lower(regexp_replace(COALESCE(NULLIF(trim(nombre), ''), id), '[^a-z0-9]+', '-', 'g')) AS slug
                FROM tenant
            ) t
            GROUP BY slug HAVING count(*) > 1
            """
        )
    ).fetchall()
    if conflicts:
        detailed = ", ".join(f"{row[0]}={row[1]}" for row in conflicts)
        raise ValueError(f"Hay tenants con slug conflictivo: {detailed}")

    bind.execute(
        sa.text(
            """
            UPDATE tenant
            SET slug = lower(regexp_replace(COALESCE(NULLIF(trim(nombre), ''), id), '[^a-z0-9]+', '-', 'g'))
            WHERE slug IS NULL OR slug = ''
            """
        )
    )
    op.execute("ALTER TABLE tenant ALTER COLUMN slug SET NOT NULL")

    if not _has_column(inspector, "tenant", "email_contacto"):
        op.add_column("tenant", sa.Column("email_contacto", sa.String(255), nullable=True))
    if not _has_column(inspector, "tenant", "tz"):
        op.add_column(
            "tenant",
            sa.Column(
                "tz",
                sa.String(64),
                nullable=False,
                server_default="America/Argentina/Buenos_Aires",
            ),
        )
    if not _has_column(inspector, "tenant", "created_at"):
        op.add_column(
            "tenant",
            sa.Column(
                "created_at",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
            ),
        )
        op.execute("ALTER TABLE tenant ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP")

    if not inspector.has_table("usuario"):
        op.create_table(
            "usuario",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenant.id"), nullable=False),
            sa.Column("nombre", sa.String(200), nullable=True),
            sa.Column("email", sa.String(255), nullable=False),
            sa.Column("password_hash", sa.String(255), nullable=True),
            sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.false(), default=True),
            sa.Column("roles", sa.Text(), nullable=False, server_default="{}"),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
            ),
            sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        )
        op.create_index("ux_usuario_tenant_email", "usuario", ["tenant_id", "email"], unique=True)
        op.execute("ALTER TABLE usuario ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP")
        op.execute("ALTER TABLE usuario ALTER COLUMN updated_at SET DEFAULT CURRENT_TIMESTAMP")

    if not _has_column(inspector, "config", "senia_requerida"):
        op.add_column(
            "config",
            sa.Column("senia_requerida", sa.Boolean(), nullable=False, server_default=sa.false()),
        )

    op.create_index("ux_tenant_slug", "tenant", ["slug"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("usuario"):
        op.drop_index("ux_usuario_tenant_email", table_name="usuario")
        op.drop_table("usuario")

    if inspector.has_index("ux_tenant_slug", "tenant"):
        op.drop_index("ux_tenant_slug", table_name="tenant")

    if _has_column(inspector, "config", "senia_requerida"):
        op.drop_column("config", "senia_requerida")

    for column_name in ("created_at", "tz", "email_contacto", "slug"):
        if _has_column(inspector, "tenant", column_name):
            op.drop_column("tenant", column_name)
