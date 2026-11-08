"""C-10 lista de espera automatica: tabla lista_espera y TTL configurable."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "013_lista_espera"
down_revision = "012_notificaciones"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "config",
        sa.Column("lista_espera_ttl_hs", sa.Integer(), nullable=False, server_default="2"),
    )
    with op.batch_alter_table("config") as batch:
        batch.create_check_constraint(
            "ck_config_lista_espera_ttl_ge_0", "lista_espera_ttl_hs >= 0"
        )

    op.create_table(
        "lista_espera",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("paciente_id", sa.String(64), sa.ForeignKey("paciente.id"), nullable=False),
        sa.Column("profesional_id", sa.String(64), nullable=True),
        sa.Column("prestacion_id", sa.String(64), nullable=True),
        sa.Column("prioridad", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estado", sa.String(20), nullable=False, server_default="activa"),
        sa.Column("motivo_omision", sa.String(40), nullable=True),
        sa.Column("hueco_profesional_id", sa.String(64), nullable=True),
        sa.Column("hueco_inicio", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("hueco_fin", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("hueco_prestacion_id", sa.String(64), nullable=True),
        sa.Column("ofrecido_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "estado IN ('activa', 'ofrecida', 'convertida', 'vencida')",
            name="ck_lista_espera_estado",
        ),
    )
    op.create_index("ix_lista_espera_tenant_id", "lista_espera", ["tenant_id"])
    op.create_index("ix_lista_espera_tenant_estado_prioridad", "lista_espera", ["tenant_id", "estado", "prioridad"])
    op.create_index("ix_lista_espera_tenant_estado_expires", "lista_espera", ["tenant_id", "estado", "expires_at"])
    op.create_index("ix_lista_espera_tenant_paciente", "lista_espera", ["tenant_id", "paciente_id"])


def downgrade() -> None:
    op.drop_index("ix_lista_espera_tenant_paciente", table_name="lista_espera")
    op.drop_index("ix_lista_espera_tenant_estado_expires", table_name="lista_espera")
    op.drop_index("ix_lista_espera_tenant_estado_prioridad", table_name="lista_espera")
    op.drop_index("ix_lista_espera_tenant_id", table_name="lista_espera")
    op.drop_table("lista_espera")
    with op.batch_alter_table("config") as batch:
        batch.drop_constraint("ck_config_lista_espera_ttl_ge_0", type_="check")
        batch.drop_column("lista_espera_ttl_hs")
