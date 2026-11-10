"""Seed demo sintético (R14): tenant demo + usuarios + turnos.

Es idempotente y explíctamente crea un tenant con slug `demo` para que el
patrón de multi-tenancy quede informado desde el arranque del sistema.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.modules.agenda.models import (
    ConfigModel,
    PrestacionModel,
    ProfesionalModel,
    TenantModel,
    TurnoModel,
    UsuarioModel,
    UsuarioRoles,
)
from app.modules.notificaciones.seed import seed_plantillas

TENANT_DEMO = "tenant-demo"
TENANT_DEMO_SLUG = "demo"
TURNO_LIBRE_ID = "turno-demo-cancelable"
TURNO_VENTANA_ID = "turno-demo-en-ventana"


def seed_demo(session: Session, now_utc: datetime | None = None) -> dict:
    now_utc = now_utc or datetime.now(timezone.utc)

    tenant = session.get(TenantModel, TENANT_DEMO)
    if tenant is None:
        tenant = TenantModel(id=TENANT_DEMO, nombre="Consultorio Demo", slug=TENANT_DEMO_SLUG)
        session.add(tenant)
    elif not tenant.slug:
        tenant.slug = TENANT_DEMO_SLUG

    cfg = session.get(ConfigModel, TENANT_DEMO)
    if cfg is None:
        session.add(
            ConfigModel(
                tenant_id=TENANT_DEMO,
                antelacion_cancel_hs=24,
                antelacion_reserva_hs=2,
                senia_requerida=False,
            )
        )

    demo_users = [
        ("usuario-demo-recepcion", "recepcion@demo.com", [UsuarioRoles.RECEPCION.value]),
        ("usuario-demo-odontologo", "odontologo@demo.com", [UsuarioRoles.ODONTOLOGO.value]),
        ("usuario-demo-dueno", "dueno@demo.com", [UsuarioRoles.DUENO.value]),
        ("usuario-demo-todo", "multi@demo.com", [r.value for r in UsuarioRoles]),
    ]
    for user_id, email, roles in demo_users:
        usuario = session.query(UsuarioModel).filter_by(tenant_id=TENANT_DEMO, email=email).first()
        if usuario is None:
            session.add(
                UsuarioModel(
                    id=user_id,
                    tenant_id=TENANT_DEMO,
                    nombre=email.split("@", 1)[0],
                    email=email,
                    activo=True,
                    roles=roles,
                )
            )

    profesional_demo = session.get(ProfesionalModel, "prof-demo-1")
    if profesional_demo is None:
        session.add(
            ProfesionalModel(
                id="prof-demo-1",
                tenant_id=TENANT_DEMO,
                nombre="Profesional Demo",
                usuario_id=None,
                activo=True,
            )
        )
    elif profesional_demo.tenant_id != TENANT_DEMO:
        raise ValueError("El ID reservado para el profesional demo pertenece a otro tenant.")

    for prestacion_id, nombre, duracion_min in (
        ("prest-demo-limpieza", "limpieza", 30),
        ("prest-demo-consulta", "consulta", 20),
        ("prest-demo-arreglo", "arreglo", 45),
        ("prest-demo-conducto", "conducto", 60),
    ):
        existente = (
            session.query(PrestacionModel)
            .filter_by(tenant_id=TENANT_DEMO, nombre=nombre)
            .first()
        )
        if existente is not None:
            continue
        prestacion_por_id = session.get(PrestacionModel, prestacion_id)
        if prestacion_por_id is not None and prestacion_por_id.tenant_id != TENANT_DEMO:
            raise ValueError(
                f"El ID reservado para la prestación demo {nombre} pertenece a otro tenant."
            )
        if prestacion_por_id is None:
            session.add(
                PrestacionModel(
                    id=prestacion_id,
                    tenant_id=TENANT_DEMO,
                    nombre=nombre,
                    duracion_min=duracion_min,
                    precio_ref=None,
                    activa=True,
                )
            )

    def _upsert_turno(turno_id: str, inicio, estado="confirmado") -> TurnoModel:
        t = session.get(TurnoModel, turno_id)
        if t is None:
            t = TurnoModel(
                id=turno_id,
                tenant_id=TENANT_DEMO,
                paciente_id="pac-demo-1",
                profesional_id="prof-demo-1",
                profesional_usuario_id="user-odonto-demo",
                prestacion_id=None,
                inicio=inicio,
                fin=inicio + timedelta(minutes=30),
                estado=estado,
            )
            session.add(t)
        return t

    # Paciente demo (R14: datos sintéticos)
    from app.modules.pacientes.models import PacienteModel

    paciente_demo_id = "pac-demo-1"
    paciente = session.get(PacienteModel, paciente_demo_id)
    if paciente is None or paciente.tenant_id != TENANT_DEMO:
        if paciente is None:
            session.add(
                PacienteModel(
                    id=paciente_demo_id,
                    tenant_id=TENANT_DEMO,
                    nombre="Paciente",
                    apellido="Demo",
                    telefono="+5491112345678",
                    dni="12345678",
                    email="paciente@demo.com",
                )
            )

    # Cobro y cierre de caja de ejemplo
    from app.modules.cobros.models import CobroModel, CierreCajaModel
    from datetime import timedelta

    cobro_demo_id = "cobro-demo-1"
    cobro = session.get(CobroModel, cobro_demo_id)
    if cobro is None:
        session.add(
            CobroModel(
                id=cobro_demo_id,
                tenant_id=TENANT_DEMO,
                paciente_id=paciente_demo_id,
                monto_cents=50000,
                medio="efectivo",
                concepto="Consulta de ejemplo",
                usuario_id="usuario-demo-dueno",
                fecha=now_utc,
            )
        )

    cierre_demo_id = "cierre-demo-1"
    cierre = session.get(CierreCajaModel, cierre_demo_id)
    if cierre is None:
        session.add(
            CierreCajaModel(
                id=cierre_demo_id,
                tenant_id=TENANT_DEMO,
                usuario_id="usuario-demo-dueno",
                fecha=now_utc,
                total_efectivo_cents=50000,
                observaciones="Cierre de ejemplo del seed demo",
            )
        )

    session.commit()
    seed_plantillas(session, TENANT_DEMO)
    session.commit()
    return {"tenant": TENANT_DEMO, "tenant_slug": TENANT_DEMO_SLUG, "turnos": [TURNO_LIBRE_ID, TURNO_VENTANA_ID]}


if __name__ == "__main__":  # pragma: no cover
    import os

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.modules.agenda.models import Base

    url = os.getenv("DATABASE_URL", "sqlite:///demo.db")
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as s:
        print(seed_demo(s))
