"""horarios semanales por profesional para C-06.

Revision aditiva: conserva las revisiones 006 y 007 y permite volver atras.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "008_horarios_profesional"
down_revision = "007_auditoria_consentimiento"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("horario_profesional"):
        return

    op.create_table(
        "horario_profesional",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(64),
            sa.ForeignKey("tenant.id"),
            nullable=False,
        ),
        sa.Column("profesional_id", sa.String(64), nullable=False),
        sa.Column("dia_semana", sa.SmallInteger(), nullable=False),
        sa.Column("hora_inicio", sa.Time(), nullable=False),
        sa.Column("hora_fin", sa.Time(), nullable=False),
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
            "dia_semana >= 0 AND dia_semana <= 6",
            name="ck_horario_profesional_dia_semana",
        ),
        sa.CheckConstraint(
            "hora_fin > hora_inicio",
            name="ck_horario_profesional_rango",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "profesional_id",
            "dia_semana",
            "hora_inicio",
            name="ux_horario_profesional_inicio",
        ),
    )
    op.create_index(
        "ix_horario_profesional_tenant_id",
        "horario_profesional",
        ["tenant_id"],
    )
    op.create_index(
        "ix_horario_profesional_profesional_id",
        "horario_profesional",
        ["profesional_id"],
    )


def downgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("horario_profesional"):
        return
    op.drop_index(
        "ix_horario_profesional_profesional_id",
        table_name="horario_profesional",
    )
    op.drop_index(
        "ix_horario_profesional_tenant_id",
        table_name="horario_profesional",
    )
    op.drop_table("horario_profesional")
