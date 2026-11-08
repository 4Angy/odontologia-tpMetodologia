"""C-11 cobros y caja manual: tablas cobro y cierre_caja."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "014_cobros_caja"
down_revision = "012_notificaciones"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cobro",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("paciente_id", sa.String(64), sa.ForeignKey("paciente.id"), nullable=False),
        sa.Column("turno_id", sa.String(64), nullable=True),
        sa.Column("monto_cents", sa.Integer(), nullable=False),
        sa.Column("medio", sa.String(20), nullable=False),
        sa.Column("concepto", sa.String(200), nullable=False),
        sa.Column("usuario_id", sa.String(64), nullable=False),
        sa.Column("fecha", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint("monto_cents >= 0", name="ck_cobro_monto_no_negativo"),
        sa.CheckConstraint(
            "medio IN ('efectivo', 'transferencia', 'mp', 'otro')",
            name="ck_cobro_medio",
        ),
    )
    op.create_index("ix_cobro_tenant_fecha", "cobro", ["tenant_id", "fecha"])
    op.create_index("ix_cobro_tenant_paciente", "cobro", ["tenant_id", "paciente_id"])

    op.create_table(
        "cierre_caja",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("fecha", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("total_efectivo_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_transferencia_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_mp_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_otro_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("usuario_id", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "fecha", name="ux_cierre_tenant_fecha"),
        sa.CheckConstraint("total_efectivo_cents >= 0", name="ck_cierre_efectivo_no_negativo"),
        sa.CheckConstraint("total_transferencia_cents >= 0", name="ck_cierre_transferencia_no_negativo"),
        sa.CheckConstraint("total_mp_cents >= 0", name="ck_cierre_mp_no_negativo"),
        sa.CheckConstraint("total_otro_cents >= 0", name="ck_cierre_otro_no_negativo"),
    )
    op.create_index("ix_cierre_tenant_fecha", "cierre_caja", ["tenant_id", "fecha"])


def downgrade() -> None:
    op.drop_index("ix_cierre_tenant_fecha", table_name="cierre_caja")
    op.drop_table("cierre_caja")
    op.drop_index("ix_cobro_tenant_paciente", table_name="cobro")
    op.drop_index("ix_cobro_tenant_fecha", table_name="cobro")
    op.drop_table("cobro")