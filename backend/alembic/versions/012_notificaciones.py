"""C-09 notificaciones: plantilla, notificacion_envio y acuse del paciente."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "012_notificaciones"
down_revision = "011_reserva_publica_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "config",
        sa.Column("recordatorio_1_hs", sa.Integer(), nullable=False, server_default="48"),
    )
    op.add_column(
        "config",
        sa.Column("recordatorio_2_hs", sa.Integer(), nullable=False, server_default="24"),
    )
    op.add_column(
        "config",
        sa.Column("whatsapp_costo_centavos", sa.Integer(), nullable=False, server_default="0"),
    )
    with op.batch_alter_table("config") as batch:
        batch.create_check_constraint(
            "ck_config_recordatorio_1_ge_0", "recordatorio_1_hs >= 0"
        )
        batch.create_check_constraint(
            "ck_config_recordatorio_2_ge_0", "recordatorio_2_hs >= 0"
        )
        batch.create_check_constraint(
            "ck_config_whatsapp_costo_ge_0", "whatsapp_costo_centavos >= 0"
        )

    op.add_column(
        "turno",
        sa.Column("confirmado_paciente_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    op.create_table(
        "plantilla",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("codigo", sa.String(60), nullable=False),
        sa.Column("canal", sa.String(20), nullable=False),
        sa.Column("idioma", sa.String(10), nullable=False, server_default="es-AR"),
        sa.Column("asunto", sa.String(200), nullable=True),
        sa.Column("cuerpo", sa.Text(), nullable=False),
        sa.Column("activa", sa.Boolean(), nullable=False, server_default="false"),
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
        sa.UniqueConstraint(
            "tenant_id", "codigo", "canal", "idioma",
            name="ux_plantilla_tenant_codigo_canal_idioma",
        ),
    )
    op.create_index("ix_plantilla_tenant_id", "plantilla", ["tenant_id"])
    op.create_index("ix_plantilla_tenant_codigo", "plantilla", ["tenant_id", "codigo"])

    op.create_table(
        "notificacion_envio",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("paciente_id", sa.String(64), sa.ForeignKey("paciente.id"), nullable=False),
        sa.Column("turno_id", sa.String(64), nullable=True),
        sa.Column("canal", sa.String(20), nullable=False),
        sa.Column("plantilla_codigo", sa.String(60), nullable=False),
        sa.Column("ventana", sa.String(10), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="encolada"),
        sa.Column("motivo_code", sa.String(40), nullable=True),
        sa.Column("intentos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("provider_msg_id", sa.String(128), nullable=True),
        sa.Column("costo_estimado_centavos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ultimo_error_code", sa.String(40), nullable=True),
        sa.Column("enviado_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("entregado_at", sa.TIMESTAMP(timezone=True), nullable=True),
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
        sa.UniqueConstraint(
            "tenant_id",
            "turno_id",
            "ventana",
            "canal",
            name="ux_notif_tenant_turno_ventana_canal",
        ),
        sa.CheckConstraint("canal IN ('whatsapp', 'email')", name="ck_notif_canal"),
        sa.CheckConstraint(
            "estado IN ('encolada', 'enviada', 'entregada', 'fallida', 'omitida', 'cancelada')",
            name="ck_notif_estado",
        ),
        sa.CheckConstraint("costo_estimado_centavos >= 0", name="ck_notif_costo_no_negativo"),
        sa.CheckConstraint("intentos >= 0", name="ck_notif_intentos_no_negativos"),
        sa.CheckConstraint(
            "ventana IS NULL OR ventana IN ('t-48h', 't-24h')",
            name="ck_notif_ventana",
        ),
    )
    op.create_index("ix_notif_tenant_estado_next", "notificacion_envio", ["tenant_id", "estado", "next_attempt_at"])
    op.create_index("ix_notif_tenant_created", "notificacion_envio", ["tenant_id", "created_at"])
    op.create_index("ix_notif_tenant_paciente", "notificacion_envio", ["tenant_id", "paciente_id"])
    op.create_index("ix_notif_tenant_turno", "notificacion_envio", ["tenant_id", "turno_id"])
    # Índice parcial de idempotencia del webhook.
    op.create_index(
        "ux_notif_tenant_provider_msg",
        "notificacion_envio",
        ["tenant_id", "provider_msg_id"],
        unique=True,
        postgresql_where=sa.text("provider_msg_id IS NOT NULL"),
        sqlite_where=sa.text("provider_msg_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ux_notif_tenant_provider_msg", table_name="notificacion_envio")
    op.drop_index("ix_notif_tenant_turno", table_name="notificacion_envio")
    op.drop_index("ix_notif_tenant_paciente", table_name="notificacion_envio")
    op.drop_index("ix_notif_tenant_created", table_name="notificacion_envio")
    op.drop_index("ix_notif_tenant_estado_next", table_name="notificacion_envio")
    op.drop_table("notificacion_envio")
    op.drop_index("ix_plantilla_tenant_codigo", table_name="plantilla")
    op.drop_index("ix_plantilla_tenant_id", table_name="plantilla")
    op.drop_table("plantilla")
    op.drop_column("turno", "confirmado_paciente_at")
    with op.batch_alter_table("config") as batch:
        batch.drop_constraint("ck_config_whatsapp_costo_ge_0", type_="check")
        batch.drop_constraint("ck_config_recordatorio_2_ge_0", type_="check")
        batch.drop_constraint("ck_config_recordatorio_1_ge_0", type_="check")
        batch.drop_column("whatsapp_costo_centavos")
        batch.drop_column("recordatorio_2_hs")
        batch.drop_column("recordatorio_1_hs")
