"""Campos e índices de agenda interna para C-07.

Revisión aditiva y reversible sobre la tabla turno ya existente.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "009_turnos_agenda_interna"
down_revision = "008_horarios_profesional"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "turno",
        sa.Column("token_publico", sa.String(128), nullable=True),
    )
    op.add_column(
        "turno",
        sa.Column(
            "origen",
            sa.String(32),
            nullable=False,
            server_default="mostrador",
        ),
    )
    op.add_column("turno", sa.Column("senia_id", sa.String(64), nullable=True))
    op.add_column("turno", sa.Column("idempotency_key", sa.String(255), nullable=True))
    op.add_column(
        "turno",
        sa.Column(
            "sobreturno",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column("turno", sa.Column("sobreturno_motivo", sa.Text(), nullable=True))
    op.add_column(
        "turno",
        sa.Column("sobreturno_autorizado_por", sa.String(64), nullable=True),
    )
    op.create_index(
        "ix_turno_tenant_profesional_inicio",
        "turno",
        ["tenant_id", "profesional_id", "inicio"],
    )
    op.create_index(
        "ix_turno_tenant_inicio",
        "turno",
        ["tenant_id", "inicio"],
    )
    op.create_index(
        "ux_turno_token_publico",
        "turno",
        ["token_publico"],
        unique=True,
    )
    op.create_index(
        "ux_turno_tenant_idempotency_key",
        "turno",
        ["tenant_id", "idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ux_turno_tenant_idempotency_key", table_name="turno")
    op.drop_index("ux_turno_token_publico", table_name="turno")
    op.drop_index("ix_turno_tenant_inicio", table_name="turno")
    op.drop_index("ix_turno_tenant_profesional_inicio", table_name="turno")
    op.drop_column("turno", "sobreturno_autorizado_por")
    op.drop_column("turno", "sobreturno_motivo")
    op.drop_column("turno", "sobreturno")
    op.drop_column("turno", "idempotency_key")
    op.drop_column("turno", "senia_id")
    op.drop_column("turno", "origen")
    op.drop_column("turno", "token_publico")
