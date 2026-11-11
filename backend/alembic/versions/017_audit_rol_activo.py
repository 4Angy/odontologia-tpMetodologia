"""C-13 hardening: rol activo en la auditoria de mutaciones (DD-06)."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "017_audit_rol_activo"
down_revision = "016_senias_mercadopago"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("audit_event"):
        columns = {column["name"] for column in inspector.get_columns("audit_event")}
        if "rol_activo" not in columns:
            op.add_column(
                "audit_event",
                sa.Column("rol_activo", sa.String(32), nullable=True),
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("audit_event"):
        columns = {column["name"] for column in inspector.get_columns("audit_event")}
        if "rol_activo" in columns:
            op.drop_column("audit_event", "rol_activo")