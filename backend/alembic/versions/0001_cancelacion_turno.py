"""cancelación de turnos: crea `tenant` mínimo, `turno` mínimo y `config` mínima.

Solo si no existen (seed de C-06/C-07: esos changes extienden sin re-migrar).
R6: reversible — `downgrade` revierte lo creado por este `upgrade`.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_cancelacion_turno"
down_revision = None
branch_labels = None
depends_on = None


def _tiene_tabla(inspector, nombre: str) -> bool:
    return inspector.has_table(nombre)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if not _tiene_tabla(inspector, "tenant"):
        op.create_table(
            "tenant",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("nombre", sa.String(200), nullable=False, server_default="demo"),
        )

    if not _tiene_tabla(inspector, "turno"):
        op.create_table(
            "turno",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenant.id"), nullable=False, index=True),
            sa.Column("paciente_id", sa.String(64), nullable=False),
            sa.Column("profesional_id", sa.String(64), nullable=False, index=True),
            sa.Column("profesional_usuario_id", sa.String(64), nullable=True),
            sa.Column("prestacion_id", sa.String(64), nullable=True),
            sa.Column("inicio", sa.TIMESTAMP(timezone=True), nullable=False),
            sa.Column("fin", sa.TIMESTAMP(timezone=True), nullable=False),
            sa.Column("estado", sa.String(32), nullable=False, server_default="confirmado"),
            sa.Column("cancelled_by", sa.String(64), nullable=True),
            sa.Column("cancelled_at", sa.TIMESTAMP(timezone=True), nullable=True),
            sa.Column("motivo", sa.Text(), nullable=True),
            sa.Column("senia_pendiente_definicion", sa.Boolean(), nullable=False, server_default=sa.false()),
        )

    if not _tiene_tabla(inspector, "config"):
        op.create_table(
            "config",
            sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenant.id"), primary_key=True),
            sa.Column("antelacion_cancel_hs", sa.Integer(), nullable=False, server_default="24"),
            sa.CheckConstraint("antelacion_cancel_hs >= 0", name="ck_config_antelacion_ge_0"),
        )


def downgrade() -> None:
    op.drop_table("config")
    op.drop_table("turno")
    op.drop_table("tenant")
