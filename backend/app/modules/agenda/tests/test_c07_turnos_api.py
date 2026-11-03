from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.audit import AuditEventModel
from app.core.security import mint_token
from app.main import create_app
from app.modules.agenda.models import (
    PrestacionModel,
    HorarioProfesionalModel,
    ProfesionalModel,
    TenantModel,
    TurnoModel,
    UsuarioModel,
)
from app.modules.pacientes.models import PacienteModel

TENANT_A = "tenant-c07-api-a"
TENANT_B = "tenant-c07-api-b"
AHORA = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)


@pytest.fixture()
def client(session_factory):
    session = session_factory()
    session.add_all(
        [
            TenantModel(id=TENANT_A, nombre="Demo A"),
            TenantModel(id=TENANT_B, nombre="Demo B"),
        ]
    )
    session.flush()
    session.add_all(
        [
            UsuarioModel(
                id="user-recepcion",
                tenant_id=TENANT_A,
                email="recepcion@example.test",
                roles=["recepcion"],
            ),
            UsuarioModel(
                id="user-odontologo",
                tenant_id=TENANT_A,
                email="odontologo@example.test",
                roles=["odontologo"],
            ),
            ProfesionalModel(
                id="prof-a",
                tenant_id=TENANT_A,
                nombre="Profesional A",
                usuario_id="user-odontologo",
            ),
            ProfesionalModel(
                id="prof-b",
                tenant_id=TENANT_A,
                nombre="Profesional B",
                usuario_id="otro-odontologo",
            ),
            ProfesionalModel(
                id="prof-tenant-b",
                tenant_id=TENANT_B,
                nombre="Profesional B",
            ),
            PrestacionModel(
                id="prest-a",
                tenant_id=TENANT_A,
                nombre="Consulta",
                duracion_min=30,
            ),
            PacienteModel(
                id="pac-a",
                tenant_id=TENANT_A,
                nombre="Paciente",
                apellido="Sintético A",
            ),
            PacienteModel(
                id="pac-b",
                tenant_id=TENANT_B,
                nombre="Paciente",
                apellido="Sintético B",
            ),
            TurnoModel(
                id="turno-propio",
                tenant_id=TENANT_A,
                paciente_id="pac-a",
                profesional_id="prof-a",
                profesional_usuario_id="user-odontologo",
                prestacion_id="prest-a",
                inicio=AHORA + timedelta(days=1),
                fin=AHORA + timedelta(days=1, minutes=30),
                estado="confirmado",
            ),
            TurnoModel(
                id="turno-otro-prof",
                tenant_id=TENANT_A,
                paciente_id="pac-a",
                profesional_id="prof-b",
                profesional_usuario_id="otro-odontologo",
                prestacion_id="prest-a",
                inicio=AHORA + timedelta(days=1),
                fin=AHORA + timedelta(days=1, minutes=30),
                estado="confirmado",
            ),
        ]
    )
    session.commit()
    session.close()
    return TestClient(create_app(session_factory=session_factory, now_fn=lambda: AHORA))


def _auth(user_id="user-recepcion", roles=("recepcion",), tenant=TENANT_A):
    token = mint_token(user_id=user_id, tenant_id=tenant, roles=list(roles))
    return {"Authorization": f"Bearer {token}"}


def _payload(**overrides):
    values = {
        "paciente_id": "pac-a",
        "profesional_id": "prof-a",
        "prestacion_id": "prest-a",
        "inicio": (AHORA + timedelta(days=2)).isoformat(),
        "fin": (AHORA + timedelta(days=2, minutes=30)).isoformat(),
    }
    values.update(overrides)
    return values


def test_api_crea_turno_y_reintento_idempotente_devuelve_mismo_recurso(client):
    headers = {**_auth(), "Idempotency-Key": "crear-turno-1"}
    primera = client.post("/turnos", json=_payload(), headers=headers)
    segunda = client.post("/turnos", json=_payload(), headers=headers)

    assert primera.status_code == 201, primera.text
    assert segunda.status_code == 201, segunda.text
    assert primera.json()["id"] == segunda.json()["id"]
    assert primera.json()["estado"] == "confirmado"
    assert primera.json()["origen"] == "mostrador"
    session = client.app.state.session_factory()
    auditorias = session.execute(
        select(AuditEventModel).where(
            AuditEventModel.tenant_id == TENANT_A,
            AuditEventModel.accion == "agenda.turno.creado",
        )
    ).scalars().all()
    session.close()
    assert len(auditorias) == 1


def test_api_rechaza_paciente_de_otro_tenant_sin_revelar_datos(client):
    response = client.post(
        "/turnos",
        json=_payload(paciente_id="pac-b"),
        headers={**_auth(), "Idempotency-Key": "crear-turno-2"},
    )
    assert response.status_code == 404
    assert response.json()["code"] == "RN-AU-01"
    assert "Sintético B" not in response.text


def test_api_agenda_dia_y_odontologo_solo_ve_sus_turnos(client):
    response = client.get(
        "/agenda/dia?fecha=2026-10-08",
        headers=_auth("user-odontologo", ("odontologo",)),
    )
    assert response.status_code == 200, response.text
    assert [turno["id"] for turno in response.json()] == ["turno-propio"]


def test_api_odontologo_no_puede_crear_turnos(client):
    response = client.post(
        "/turnos",
        json=_payload(),
        headers={
            **_auth("user-odontologo", ("odontologo",)),
            "Idempotency-Key": "crear-turno-3",
        },
    )
    assert response.status_code == 403
    assert response.json()["code"] == "RN-AU-04"


def test_api_agenda_semana_incluye_turnos_ordenados(client):
    response = client.get(
        "/agenda/semana?fecha=2026-10-08",
        headers=_auth(),
    )

    assert response.status_code == 200, response.text
    assert [turno["id"] for turno in response.json()] == [
        "turno-otro-prof",
        "turno-propio",
    ]

    filtrada = client.get(
        "/agenda/semana?fecha=2026-10-08&profesional_id=prof-a",
        headers=_auth(),
    )
    assert filtrada.status_code == 200, filtrada.text
    assert [turno["id"] for turno in filtrada.json()] == ["turno-propio"]


def test_api_reprograma_turno_y_conserva_el_anterior_como_terminal(client):
    response = client.post(
        "/turnos/turno-propio/reprogramar",
        json={
            "profesional_id": "prof-a",
            "prestacion_id": "prest-a",
            "inicio": (AHORA + timedelta(days=3)).isoformat(),
            "fin": (AHORA + timedelta(days=3, minutes=30)).isoformat(),
        },
        headers=_auth(),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["turno_anterior"]["estado"] == "reprogramado"
    assert body["turno_nuevo"]["estado"] == "confirmado"
    assert body["turno_nuevo"]["paciente_id"] == "pac-a"
    assert body["turno_nuevo"]["senia_id"] is None


def test_api_no_permite_marcar_ausente_antes_del_fin(client):
    response = client.post(
        "/turnos/turno-propio/ausente",
        headers=_auth(),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "RN-AG-08"


def test_api_turno_detalle_y_odontologo_no_ve_turno_ajeno(client):
    propio = client.get(
        "/turnos/turno-propio",
        headers=_auth("user-odontologo", ("odontologo",)),
    )
    ajeno = client.get(
        "/turnos/turno-otro-prof",
        headers=_auth("user-odontologo", ("odontologo",)),
    )

    assert propio.status_code == 200
    assert propio.json()["id"] == "turno-propio"
    assert ajeno.status_code == 404
    assert ajeno.json()["code"] == "RN-AU-01"


def test_api_colision_retorna_alternativas_disponibles(client):
    session = client.app.state.session_factory()
    session.add(
        HorarioProfesionalModel(
            tenant_id=TENANT_A,
            profesional_id="prof-a",
            dia_semana=3,
            hora_inicio=datetime.strptime("09:00", "%H:%M").time(),
            hora_fin=datetime.strptime("12:00", "%H:%M").time(),
        )
    )
    session.commit()
    session.close()

    response = client.post(
        "/turnos",
        json=_payload(
            inicio=(AHORA + timedelta(days=1)).isoformat(),
            fin=(AHORA + timedelta(days=1, minutes=30)).isoformat(),
        ),
        headers={**_auth(), "Idempotency-Key": "crear-turno-solapado"},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "RN-AG-03"
    assert len(response.json()["alternativas"]) <= 3
    assert response.json()["alternativas"]


def test_api_consulta_horarios_disponibles_con_zona_del_tenant(client):
    session = client.app.state.session_factory()
    session.add(
        HorarioProfesionalModel(
            tenant_id=TENANT_A,
            profesional_id="prof-a",
            dia_semana=4,
            hora_inicio=datetime.strptime("09:00", "%H:%M").time(),
            hora_fin=datetime.strptime("12:00", "%H:%M").time(),
        )
    )
    session.commit()
    session.close()

    response = client.get(
        "/agenda/disponibilidad",
        params={
            "profesional_id": "prof-a",
            "prestacion_id": "prest-a",
            "desde": "2026-10-09T03:00:00-03:00",
            "hasta": "2026-10-10T03:00:00-03:00",
        },
        headers=_auth(),
    )

    assert response.status_code == 200, response.text
    assert response.json()[0].startswith("2026-10-09T12:00:00")


def test_api_reprogramacion_conserva_senia_y_libera_slot_anterior(client):
    session = client.app.state.session_factory()
    sesion = session.get(TurnoModel, "turno-propio")
    assert sesion is not None
    sesion.senia_id = "senia-sintetica"
    session.add(
        HorarioProfesionalModel(
            tenant_id=TENANT_A,
            profesional_id="prof-a",
            dia_semana=3,
            hora_inicio=datetime.strptime("09:00", "%H:%M").time(),
            hora_fin=datetime.strptime("12:00", "%H:%M").time(),
        )
    )
    session.commit()
    session.close()

    response = client.post(
        "/turnos/turno-propio/reprogramar",
        json={
            "profesional_id": "prof-a",
            "prestacion_id": "prest-a",
            "inicio": (AHORA + timedelta(days=2)).isoformat(),
            "fin": (AHORA + timedelta(days=2, minutes=30)).isoformat(),
        },
        headers=_auth(),
    )
    disponibilidad = client.get(
        "/agenda/disponibilidad",
        params={
            "profesional_id": "prof-a",
            "prestacion_id": "prest-a",
            "desde": "2026-10-08T03:00:00-03:00",
            "hasta": "2026-10-09T03:00:00-03:00",
        },
        headers=_auth(),
    )

    assert response.status_code == 200, response.text
    assert response.json()["turno_anterior"]["senia_id"] == "senia-sintetica"
    assert response.json()["turno_nuevo"]["senia_id"] is None
    assert "2026-10-08T12:00:00" in disponibilidad.text
