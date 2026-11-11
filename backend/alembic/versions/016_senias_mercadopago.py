"""C-12 señas de Mercado Pago: tabla senia + columnas en prestacion y config."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "016_senias_mercadopago"
down_revision = "015_merge_lista_espera_cobros"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "senia",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("turno_id", sa.String(64), nullable=False),
        sa.Column("paciente_id", sa.String(64), sa.ForeignKey("paciente.id"), nullable=False),
        sa.Column("monto_cents", sa.Integer(), nullable=False),
        sa.Column("monto_afavor_cents", sa.Integer(), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="pendiente"),
        sa.Column("mp_preference_id", sa.String(128), nullable=False),
        sa.Column("mp_payment_id", sa.String(64), nullable=True),
        sa.Column("acreditada_at", sa.TIMESTAMP(timezone=True), nullable=True),
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
        sa.UniqueConstraint("mp_preference_id", name="ux_senia_mp_preference_id"),
        sa.UniqueConstraint("mp_payment_id", name="ux_senia_mp_payment_id"),
        sa.CheckConstraint("monto_cents > 0", name="ck_senia_monto_positivo"),
        sa.CheckConstraint(
            "estado IN ('pendiente', 'acreditada', 'devuelta', 'aplicada')",
            name="ck_senia_estado",
        ),
        sa.CheckConstraint(
            "monto_afavor_cents IS NULL OR monto_afavor_cents <= monto_cents",
            name="ck_senia_afavor_no_supera_monto",
        ),
    )
    op.create_index(
        "ix_senia_tenant_paciente", "senia", ["tenant_id", "paciente_id"]
    )
    op.create_index("ix_senia_tenant_turno", "senia", ["tenant_id", "turno_id"])
    op.create_index("ix_senia_turno_id", "senia", ["turno_id"])
    op.create_index("ix_senia_paciente_id", "senia", ["paciente_id"])

    # seña por prestación (override nullable: NULL = usar config global)
    op.add_column(
        "prestacion",
        sa.Column("senia_requerida", sa.Boolean(), nullable=True, server_default="true"),
    )
    op.add_column(
        "prestacion",
        sa.Column("senia_monto_cents", sa.Integer(), nullable=True),
    )
    # política de devolución (RN-CO-03)
    op.add_column(
        "config",
        sa.Column(
            "politica_devolucion_senia",
            sa.String(20),
            nullable=False,
            server_default="devuelve_100",
        ),
    )
    op.create_check_constraint(
        "ck_config_politica_devolucion_senia",
        "config",
        "politica_devolucion_senia IN ('no_devuelve', 'devuelve_50', 'devuelve_100')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_config_politica_devolucion_senia", "config", type_="check"
    )
    op.drop_column("config", "politica_devolucion_senia")
    op.drop_column("prestacion", "senia_monto_cents")
    op.drop_column("prestacion", "senia_requerida")
    op.drop_index("ix_senia_paciente_id", table_name="senia")
    op.drop_index("ix_senia_turno_id", table_name="senia")
    op.drop_index("ix_senia_tenant_turno", table_name="senia")
    op.drop_index("ix_senia_tenant_paciente", table_name="senia")
    op.drop_table("senia")
