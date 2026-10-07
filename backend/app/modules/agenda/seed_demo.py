"""Seed demo sintético (R14): tenant demo + 1 turno cancelable futuro
+ 1 turno dentro de la ventana de antelación. Idempotente (upsert por PK)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.modules.agenda.models import ConfigModel, TenantModel, TurnoModel

TENANT_DEMO = "tenant-demo"
TURNO_LIBRE_ID = "turno-demo-cancelable"
TURNO_VENTANA_ID = "turno-demo-en-ventana"


def seed_demo(session: Session, now_utc: datetime | None = None) -> dict:
    now_utc = now_utc or datetime.now(timezone.utc)

    tenant = session.get(TenantModel, TENANT_DEMO)
    if tenant is None:
        session.add(TenantModel(id=TENANT_DEMO, nombre="Consultorio Demo"))

    cfg = session.get(ConfigModel, TENANT_DEMO)
    if cfg is None:
        session.add(ConfigModel(tenant_id=TENANT_DEMO, antelacion_cancel_hs=24))

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

    _upsert_turno(TURNO_LIBRE_ID, now_utc + timedelta(hours=72))
    _upsert_turno(TURNO_VENTANA_ID, now_utc + timedelta(hours=2))
    session.commit()
    return {"tenant": TENANT_DEMO, "turnos": [TURNO_LIBRE_ID, TURNO_VENTANA_ID]}


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
