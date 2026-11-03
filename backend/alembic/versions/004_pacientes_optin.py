"""pacientes + opt-in: crea tabla `paciente` y `optin` para C-04.

R6: el downgrade revierte solo este slice; la base de 0001/002/003 queda intacta.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "004_pacientes_optin"
down_revision = "003_auth_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("paciente"):
        op.create_table(
            "paciente",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenant.id"), nullable=False),
            sa.Column("nombre", sa.String(120), nullable=False),
            sa.Column("apellido", sa.String(120), nullable=False),
            sa.Column("dni", sa.String(20), nullable=True),
            sa.Column("telefono", sa.String(30), nullable=True),
            sa.Column("email", sa.String(255), nullable=True),
            sa.Column("fecha_nac", sa.TIMESTAMP(timezone=True), nullable=True),
            sa.Column("notas", sa.Text(), nullable=True),
            sa.Column("saldo", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        )
        op.create_index("ix_paciente_tenant_id", "paciente", ["tenant_id"])
        op.create_index("ix_paciente_apellido", "paciente", ["tenant_id", "apellido"])
        op.create_index("ix_paciente_telefono", "paciente", ["tenant_id", "telefono"])
        op.create_index("ix_paciente_dni", "paciente", ["tenant_id", "dni"])
        op.create_unique_constraint("ux_paciente_tenant_dni", "paciente", ["tenant_id", "dni"])
        op.create_unique_constraint("ux_paciente_tenant_telefono", "paciente", ["tenant_id", "telefono"])

    if not inspector.has_table("optin"):
        op.create_table(
            "optin",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenant.id"), nullable=False),
            sa.Column("paciente_id", sa.String(64), sa.ForeignKey("paciente.id"), nullable=False),
            sa.Column("canal", sa.String(20), nullable=False, server_default="whatsapp"),
            sa.Column("estado", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_optin_paciente_id", "optin", ["paciente_id"])
        op.create_unique_constraint("ux_optin_tenant_paciente_canal", "optin", ["tenant_id", "paciente_id", "canal"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("optin"):
        op.drop_constraint("ux_optin_tenant_paciente_canal", "optin", type_="unique")
        op.drop_index("ix_optin_paciente_id", table_name="optin")
        op.drop_table("optin")

    if inspector.has_table("paciente"):
        op.drop_constraint("ux_paciente_tenant_telefono", "paciente", type_="unique")
        op.drop_constraint("ux_paciente_tenant_dni", "paciente", type_="unique")
        op.drop_index("ix_paciente_dni", table_name="paciente")
        op.drop_index("ix_paciente_telefono", table_name="paciente")
        op.drop_index("ix_paciente_apellido", table_name="paciente")
        op.drop_index("ix_paciente_tenant_id", table_name="paciente")
        op.drop_table("paciente")
