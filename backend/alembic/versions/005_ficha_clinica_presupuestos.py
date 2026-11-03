"""ficha clínica + presupuestos: crea tablas de evolución, adjunto y presupuesto para C-05.

R6: el downgrade revierte sólo este slice; la base de 0001/002/003/004 queda intacta.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "005_ficha_clinica_presupuestos"
down_revision = "004_pacientes_optin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("evolucion"):
        op.create_table(
            "evolucion",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenant.id"), nullable=False),
            sa.Column("paciente_id", sa.String(64), sa.ForeignKey("paciente.id"), nullable=False),
            sa.Column("odontologo_id", sa.String(64), nullable=True),
            sa.Column("motivo", sa.String(200), nullable=False),
            sa.Column("detalle", sa.Text(), nullable=False),
            sa.Column("firma_simple", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("firma_timestamp", sa.TIMESTAMP(timezone=True), nullable=True),
            sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        )
        op.create_index("ix_evolucion_tenant_id", "evolucion", ["tenant_id"])
        op.create_index("ix_evolucion_paciente_id", "evolucion", ["paciente_id"])

    if not inspector.has_table("adjunto"):
        op.create_table(
            "adjunto",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenant.id"), nullable=False),
            sa.Column("paciente_id", sa.String(64), sa.ForeignKey("paciente.id"), nullable=False),
            sa.Column("nombre", sa.String(200), nullable=False),
            sa.Column("tipo", sa.String(100), nullable=False),
            sa.Column("tamano_bytes", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("url", sa.String(500), nullable=True),
            sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        )
        op.create_index("ix_adjunto_tenant_id", "adjunto", ["tenant_id"])
        op.create_index("ix_adjunto_paciente_id", "adjunto", ["paciente_id"])

    if not inspector.has_table("presupuesto"):
        op.create_table(
            "presupuesto",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenant.id"), nullable=False),
            sa.Column("paciente_id", sa.String(64), sa.ForeignKey("paciente.id"), nullable=False),
            sa.Column("total_cents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("estado", sa.String(32), nullable=False, server_default="activo"),
            sa.Column("notas", sa.Text(), nullable=True),
            sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        )
        op.create_index("ix_presupuesto_tenant_id", "presupuesto", ["tenant_id"])
        op.create_index("ix_presupuesto_paciente_id", "presupuesto", ["paciente_id"])

    if not inspector.has_table("presupuesto_item"):
        op.create_table(
            "presupuesto_item",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenant.id"), nullable=False),
            sa.Column("presupuesto_id", sa.String(64), sa.ForeignKey("presupuesto.id"), nullable=False),
            sa.Column("descripcion", sa.String(200), nullable=False),
            sa.Column("monto_cents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        )
        op.create_index("ix_presupuesto_item_tenant_id", "presupuesto_item", ["tenant_id"])
        op.create_index("ix_presupuesto_item_presupuesto_id", "presupuesto_item", ["presupuesto_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("presupuesto_item"):
        op.drop_index("ix_presupuesto_item_presupuesto_id", table_name="presupuesto_item")
        op.drop_index("ix_presupuesto_item_tenant_id", table_name="presupuesto_item")
        op.drop_table("presupuesto_item")

    if inspector.has_table("presupuesto"):
        op.drop_index("ix_presupuesto_paciente_id", table_name="presupuesto")
        op.drop_index("ix_presupuesto_tenant_id", table_name="presupuesto")
        op.drop_table("presupuesto")

    if inspector.has_table("adjunto"):
        op.drop_index("ix_adjunto_paciente_id", table_name="adjunto")
        op.drop_index("ix_adjunto_tenant_id", table_name="adjunto")
        op.drop_table("adjunto")

    if inspector.has_table("evolucion"):
        op.drop_index("ix_evolucion_paciente_id", table_name="evolucion")
        op.drop_index("ix_evolucion_tenant_id", table_name="evolucion")
        op.drop_table("evolucion")
