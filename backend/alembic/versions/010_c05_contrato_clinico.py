"""Completa ADR-003, adjuntos privados y estados de presupuesto (C-05)."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "010_c05_contrato_clinico"
down_revision = "009_turnos_agenda_interna"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("evolucion"):
        columns = {column["name"] for column in inspector.get_columns("evolucion")}
        with op.batch_alter_table("evolucion") as batch:
            if "profesional_id" not in columns:
                batch.add_column(sa.Column("profesional_id", sa.String(64), nullable=True))
            if "fecha" not in columns:
                batch.add_column(sa.Column("fecha", sa.TIMESTAMP(timezone=True), nullable=True))
            if "pieza_fdi_slot" not in columns:
                batch.add_column(sa.Column("pieza_fdi_slot", sa.String(16), nullable=True))
            if "pieza_fdi_numero" not in columns:
                batch.add_column(sa.Column("pieza_fdi_numero", sa.Integer(), nullable=True))
            if "odontograma_ref" not in columns:
                batch.add_column(sa.Column("odontograma_ref", sa.String(64), nullable=True))
            if "firmado_at" not in columns:
                batch.add_column(sa.Column("firmado_at", sa.TIMESTAMP(timezone=True), nullable=True))
            if "profesional_id" not in columns:
                batch.create_foreign_key(
                    "fk_evolucion_profesional_id_profesional",
                    "profesional",
                    ["profesional_id"],
                    ["id"],
                )
            if "ck_evolucion_ancla_fdi_completa" not in {
                constraint.get("name")
                for constraint in inspector.get_check_constraints("evolucion")
            }:
                batch.create_check_constraint(
                    "ck_evolucion_ancla_fdi_completa",
                    "(pieza_fdi_slot IS NULL) = (pieza_fdi_numero IS NULL)",
                )
        bind.execute(
            sa.text(
                "UPDATE evolucion SET fecha = created_at "
                "WHERE fecha IS NULL"
            )
        )
        bind.execute(
            sa.text(
                "UPDATE evolucion SET firmado_at = firma_timestamp "
                "WHERE firmado_at IS NULL AND firma_timestamp IS NOT NULL"
            )
        )
        bind.execute(
            sa.text(
                "UPDATE evolucion SET profesional_id = ("
                "SELECT profesional.id FROM profesional "
                "WHERE profesional.tenant_id = evolucion.tenant_id "
                "AND profesional.usuario_id = evolucion.odontologo_id "
                "LIMIT 1) "
                "WHERE profesional_id IS NULL AND odontologo_id IS NOT NULL"
            )
        )
        with op.batch_alter_table("evolucion") as batch:
            batch.alter_column(
                "fecha",
                existing_type=sa.TIMESTAMP(timezone=True),
                nullable=False,
            )
        indexes = {index["name"] for index in inspector.get_indexes("evolucion")}
        if "ix_evolucion_tenant_paciente_fecha" not in indexes:
            op.create_index(
                "ix_evolucion_tenant_paciente_fecha",
                "evolucion",
                ["tenant_id", "paciente_id", "fecha"],
            )

    if inspector.has_table("adjunto"):
        columns = {column["name"] for column in inspector.get_columns("adjunto")}
        if "storage_key" not in columns:
            with op.batch_alter_table("adjunto") as batch:
                batch.add_column(sa.Column("storage_key", sa.String(512), nullable=True))
                batch.create_unique_constraint("uq_adjunto_storage_key", ["storage_key"])

    if inspector.has_table("presupuesto"):
        bind.execute(
            sa.text(
                "UPDATE presupuesto SET estado = 'aceptado' "
                "WHERE estado = 'activo'"
            )
        )
        constraints = {
            constraint.get("name")
            for constraint in inspector.get_check_constraints("presupuesto")
        }
        if "ck_presupuesto_estado" not in constraints:
            with op.batch_alter_table("presupuesto") as batch:
                batch.create_check_constraint(
                    "ck_presupuesto_estado",
                    "estado IN ('borrador', 'aprobado', 'aceptado')",
                )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("presupuesto"):
        with op.batch_alter_table("presupuesto") as batch:
            batch.drop_constraint("ck_presupuesto_estado", type_="check")
        bind.execute(
            sa.text(
                "UPDATE presupuesto SET estado = 'activo' "
                "WHERE estado IN ('borrador', 'aprobado', 'aceptado')"
            )
        )

    if inspector.has_table("adjunto"):
        columns = {column["name"] for column in inspector.get_columns("adjunto")}
        if "storage_key" in columns:
            with op.batch_alter_table("adjunto") as batch:
                batch.drop_constraint("uq_adjunto_storage_key", type_="unique")
                batch.drop_column("storage_key")

    if inspector.has_table("evolucion"):
        indexes = {index["name"] for index in inspector.get_indexes("evolucion")}
        if "ix_evolucion_tenant_paciente_fecha" in indexes:
            op.drop_index("ix_evolucion_tenant_paciente_fecha", table_name="evolucion")
        with op.batch_alter_table("evolucion") as batch:
            batch.drop_constraint("ck_evolucion_ancla_fdi_completa", type_="check")
            batch.drop_constraint(
                "fk_evolucion_profesional_id_profesional", type_="foreignkey"
            )
            for column in (
                "firmado_at",
                "odontograma_ref",
                "pieza_fdi_numero",
                "pieza_fdi_slot",
                "fecha",
                "profesional_id",
            ):
                batch.drop_column(column)
