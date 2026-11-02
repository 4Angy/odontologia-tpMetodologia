"""auth tokens: tabla `auth_token` (familias de refresh + tokens de reset).

Task 1.1 de `c-03-auth-rbac-multirole`. R6: reversibilidad — el downgrade
elimina solo la tabla y sus índices; no toca nada de `0001`/`002`.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "003_auth_tokens"
down_revision = "002_tenancy_core_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("auth_token"):
        return
    op.create_table(
        "auth_token",
        sa.Column("id", sa.String(64), primary_key=True),  # id == jti del token
        sa.Column(
            "tenant_id", sa.String(64), sa.ForeignKey("tenant.id"), nullable=False
        ),
        sa.Column(
            "usuario_id", sa.String(64), sa.ForeignKey("usuario.id"), nullable=False
        ),
        sa.Column("familia_id", sa.String(64), nullable=False),
        sa.Column("proposito", sa.String(16), nullable=False),
        sa.Column(
            "revoked", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("used_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("expira", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "proposito IN ('refresh','reset')", name="ck_auth_token_proposito"
        ),
    )
    op.create_index("ix_auth_token_usuario_id", "auth_token", ["usuario_id"])
    op.create_index("ix_auth_token_familia_id", "auth_token", ["familia_id"])
    op.create_index(
        "ix_auth_token_tenant_familia", "auth_token", ["tenant_id", "familia_id"]
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("auth_token"):
        return
    op.drop_index("ix_auth_token_tenant_familia", table_name="auth_token")
    op.drop_index("ix_auth_token_familia_id", table_name="auth_token")
    op.drop_index("ix_auth_token_usuario_id", table_name="auth_token")
    op.drop_table("auth_token")
