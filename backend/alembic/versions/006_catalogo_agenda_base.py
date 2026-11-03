"""catalogo agenda base: profesionales, prestaciones y bloqueos para C-06.

R6: el downgrade revierte sólo este slice; la base de 0001/002/003/004/005 queda intacta.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "006_catalogo_agenda_base"
down_revision = "005_ficha_clinica_presupuestos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("profesional"):
        op.create_table(
            "profesional",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenant.id"), nullable=False),
            sa.Column("usuario_id", sa.String(64), nullable=True),
            sa.Column("nombre", sa.String(200), nullable=False),
            sa.Column("color_agenda", sa.String(16), nullable=True),
            sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        )
        op.create_index("ix_profesional_tenant_id", "profesional", ["tenant_id"])
        op.create_index("ix_profesional_usuario_id", "profesional", ["usuario_id"])

    if not inspector.has_table("prestacion"):
        op.create_table(
            "prestacion",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenant.id"), nullable=False),
            sa.Column("nombre", sa.String(120), nullable=False),
            sa.Column("duracion_min", sa.Integer(), nullable=False, server_default="30"),
            sa.Column("precio_ref", sa.Integer(), nullable=True),
            sa.Column("activa", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        )
        op.create_index("ix_prestacion_tenant_id", "prestacion", ["tenant_id"])

    if not inspector.has_table("bloqueo"):
        op.create_table(
            "bloqueo",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenant.id"), nullable=False),
            sa.Column("profesional_id", sa.String(64), nullable=False),
            sa.Column("inicio", sa.TIMESTAMP(timezone=True), nullable=False),
            sa.Column("fin", sa.TIMESTAMP(timezone=True), nullable=False),
            sa.Column("motivo", sa.Text(), nullable=True),
            sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        )
        op.create_index("ix_bloqueo_tenant_id", "bloqueo", ["tenant_id"])
        op.create_index("ix_bloqueo_profesional_id", "bloqueo", ["profesional_id"])

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.get_columns("config"):
        return

    existing = inspector.get_columns("config")
    columns = {c["name"] for c in existing}
    if "antelacion_reserva_hs" not in columns:
        op.add_column("config", sa.Column("antelacion_reserva_hs", sa.Integer(), nullable=False, server_default="2"))
    if "recordatorio_t_48h" not in columns:
        op.add_column("config", sa.Column("recordatorio_t_48h", sa.Boolean(), nullable=False, server_default=sa.true()))
    if "recordatorio_t_24h" not in columns:
        op.add_column("config", sa.Column("recordatorio_t_24h", sa.Boolean(), nullable=False, server_default=sa.true()))

    op.create_check_constraint("ck_config_reserva_antelacion_ge_0", "config", "antelacion_reserva_hs >= 0")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("config"):
        cols = {c["name"] for c in inspector.get_columns("config")}
        for name in ["recordatorio_t_24h", "recordatorio_t_48h", "antelacion_reserva_hs"]:
            if name in cols:
                op.drop_column("config", name)
        for name in ["ck_config_reserva_antelacion_ge_0"]:
            try:
                op.drop_constraint(name, "config", type_="check")
            except Exception:
                pass

    if inspector.has_table("bloqueo"):
        op.drop_index("ix_bloqueo_profesional_id", table_name="bloqueo")
        op.drop_index("ix_bloqueo_tenant_id", table_name="bloqueo")
        op.drop_table("bloqueo")

    if inspector.has_table("prestacion"):
        op.drop_index("ix_prestacion_tenant_id", table_name="prestacion")
        op.drop_table("prestacion")

    if inspector.has_table("profesional"):
        op.drop_index("ix_profesional_usuario_id", table_name="profesional")
        op.drop_index("ix_profesional_tenant_id", table_name="profesional")
        op.drop_table("profesional")
