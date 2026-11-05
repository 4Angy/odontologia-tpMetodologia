"""C-08 public booking tokens and audit."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "011_reserva_publica_tokens"
down_revision = "010_c05_contrato_clinico"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "config",
        sa.Column("public_payment_timeout_min", sa.Integer(), nullable=False, server_default="30"),
    )
    with op.batch_alter_table("config") as batch:
        batch.create_check_constraint(
            "ck_config_public_payment_timeout_gt_0",
            "public_payment_timeout_min > 0",
        )
    op.create_table(
        "public_token",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("turno_id", sa.String(64), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("revocation_reason", sa.String(120), nullable=True),
        sa.UniqueConstraint("tenant_id", "token_hash", "purpose", name="ux_public_token_tenant_hash_purpose"),
    )
    op.create_index("ix_public_token_tenant_turno", "public_token", ["tenant_id", "turno_id"])
    op.create_index("ix_public_token_expiry", "public_token", ["expires_at"])
    op.create_table(
        "public_audit",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("turno_id", sa.String(64), nullable=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("occurred_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_public_audit_tenant_turno", "public_audit", ["tenant_id", "turno_id"])


def downgrade() -> None:
    op.drop_index("ix_public_audit_tenant_turno", table_name="public_audit")
    op.drop_table("public_audit")
    op.drop_index("ix_public_token_expiry", table_name="public_token")
    op.drop_index("ix_public_token_tenant_turno", table_name="public_token")
    op.drop_table("public_token")
    with op.batch_alter_table("config") as batch:
        batch.drop_constraint("ck_config_public_payment_timeout_gt_0", type_="check")
        batch.drop_column("public_payment_timeout_min")
