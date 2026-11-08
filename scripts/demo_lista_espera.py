import os
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("APP_ENV", "dev")
os.environ.setdefault("JWT_SECRET", "dev-secret-largo-1234567890")

from app.modules.agenda.models import (
    ConfigModel,
    ProfesionalModel,
    TenantModel,
    TurnoModel,
    UsuarioModel,
    UsuarioRoles,
)
from app.modules.lista_espera.models import ListaEsperaModel
from app.modules.lista_espera.service import Hueco, ListaEsperaService
from app.modules.pacientes.models import OptInModel, PacienteModel

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://odontologia:odontologia@127.0.0.1:5432/odontologia")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

TENANT = "tenant-demo"
NOW = datetime.now(timezone.utc)

# paciente
pac = session.query(PacienteModel).filter_by(tenant_id=TENANT, id="pac-demo-le").first()
if pac is None:
    pac = PacienteModel(
        id="pac-demo-le",
        tenant_id=TENANT,
        nombre="Ana",
        apellido="Demo",
        telefono="+5491112345678",
    )
    session.add(pac)
    session.flush()
# opt-in
opt = session.query(OptInModel).filter_by(tenant_id=TENANT, paciente_id="pac-demo-le", canal="whatsapp").first()
if opt is None:
    opt = OptInModel(
        id="opt-demo-le",
        tenant_id=TENANT,
        paciente_id="pac-demo-le",
        canal="whatsapp",
        estado=True,
        updated_at=NOW,
    )
    session.add(opt)
    session.flush()

# entrada lista espera
entry = session.query(ListaEsperaModel).filter_by(tenant_id=TENANT, paciente_id="pac-demo-le", estado="activa").first()
if entry is None:
    entry = ListaEsperaModel(
        id=str(uuid.uuid4()),
        tenant_id=TENANT,
        paciente_id="pac-demo-le",
        profesional_id="prof-demo-1",
        prestacion_id="prest-demo-limpieza",
        prioridad=0,
        estado="activa",
    )
    session.add(entry)
    session.flush()

# cancelar turno demo y disparar oferta
turno = session.get(TurnoModel, "turno-demo-cancelable")
if turno is not None and turno.estado in ("confirmado", "pendiente_confirmacion"):
    hueco = Hueco(
        profesional_id=turno.profesional_id,
        inicio=turno.inicio,
        fin=turno.fin,
        prestacion_id=turno.prestacion_id,
    )
    turno.estado = "cancelado"
    turno.cancelled_at = NOW
    turno.cancelled_by = "demo"
    turno.motivo = "Prueba lista de espera"
    session.flush()
    svc = ListaEsperaService(session, NOW)
    offered = svc.ofrecer_por_hueco(TENANT, hueco, NOW)
    print("Turno cancelado y oferta disparada:", offered.id if offered else None)
else:
    print("Turno ya cancelado o no existe; disparando oferta con hueco fijo...")
    hueco = Hueco(
        profesional_id="prof-demo-1",
        inicio=NOW + timedelta(hours=24),
        fin=NOW + timedelta(hours=24, minutes=30),
        prestacion_id="prest-demo-limpieza",
    )
    svc = ListaEsperaService(session, NOW)
    offered = svc.ofrecer_por_hueco(TENANT, hueco, NOW)
    print("Oferta:", offered.id if offered else None)

session.commit()
session.close()
print("Listo. Revisa GET /lista-espera?estado=ofrecida y /notificaciones/envios")
