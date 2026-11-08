"""Merge de heads 013 (lista espera) y 014 (cobros caja)."""
from __future__ import annotations

from alembic import op

revision = "015_merge_lista_espera_cobros"
down_revision = ("013_lista_espera", "014_cobros_caja")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
