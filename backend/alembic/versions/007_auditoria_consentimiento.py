"""Auditoría compartida y evidencia técnica de opt-in (C-04).

La evidencia conserva canal vía `optin`, actor, instante UTC y versión del texto;
no representa una conclusión de validez legal del consentimiento.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "007_auditoria_consentimiento"
down_revision = "006_catalogo_agenda_base"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("optin"):
        columns = {column["name"] for column in inspector.get_columns("optin")}
        if "consentimiento_version" not in columns:
            op.add_column(
                "optin",
                sa.Column("consentimiento_version", sa.String(80), nullable=True),
            )
        if "consentimiento_actor_id" not in columns:
            op.add_column(
                "optin",
                sa.Column("consentimiento_actor_id", sa.String(64), nullable=True),
            )
        if "consentimiento_at" not in columns:
            op.add_column(
                "optin",
                sa.Column("consentimiento_at", sa.TIMESTAMP(timezone=True), nullable=True),
            )

    if not inspector.has_table("audit_event"):
        op.create_table(
            "audit_event",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenant.id"), nullable=False),
            sa.Column("actor_id", sa.String(64), sa.ForeignKey("usuario.id"), nullable=False),
            sa.Column("accion", sa.String(100), nullable=False),
            sa.Column("recurso", sa.String(80), nullable=False),
            sa.Column("recurso_id", sa.String(64), nullable=False),
            sa.Column("campos", sa.JSON(), nullable=False),
            sa.Column("consentimiento_version", sa.String(80), nullable=True),
            sa.Column("invalidated_destination_hash", sa.String(64), nullable=True),
            sa.Column(
                "ocurrido_at",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )
        op.create_index("ix_audit_event_tenant_id", "audit_event", ["tenant_id"])
        op.create_index("ix_audit_event_actor_id", "audit_event", ["actor_id"])
        op.create_index("ix_audit_event_recurso_id", "audit_event", ["recurso_id"])
        op.create_index("ix_audit_event_ocurrido_at", "audit_event", ["ocurrido_at"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("audit_event"):
        for index_name in (
            "ix_audit_event_ocurrido_at",
            "ix_audit_event_recurso_id",
            "ix_audit_event_actor_id",
            "ix_audit_event_tenant_id",
        ):
            op.drop_index(index_name, table_name="audit_event")
        op.drop_table("audit_event")

    if inspector.has_table("optin"):
        columns = {column["name"] for column in inspector.get_columns("optin")}
        for column_name in (
            "consentimiento_at",
            "consentimiento_actor_id",
            "consentimiento_version",
        ):
            if column_name in columns:
                op.drop_column("optin", column_name)
