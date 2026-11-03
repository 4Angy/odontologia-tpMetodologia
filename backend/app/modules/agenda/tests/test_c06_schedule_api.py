from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.agenda.models import ProfesionalModel, TenantModel
from app.modules.agenda.tests.test_c06_integrity import _owner


def test_horario_semanal_se_persiste_en_zona_del_tenant(session_factory):
    session = session_factory()
    tenant, headers = _owner(session, "c06-schedule")
    professional = ProfesionalModel(tenant_id=tenant.id, nombre="Profesional demo")
    session.add(professional)
    session.commit()
    professional_id = professional.id
    session.close()
    client = TestClient(create_app(session_factory=session_factory))

    response = client.put(
        f"/profesionales/{professional_id}/horarios",
        json={
            "horarios": [
                {"dia_semana": 0, "inicio": "09:00", "fin": "12:00"},
                {"dia_semana": 0, "inicio": "13:00", "fin": "17:00"},
            ]
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["zona_horaria"] == "America/Argentina/Buenos_Aires"
    assert len(response.json()["horarios"]) == 2
    assert response.json()["horarios"][0]["dia_semana"] == 0


def test_horario_semanal_rechaza_solapamiento_sin_perder_el_existente(
    session_factory,
):
    session = session_factory()
    tenant, headers = _owner(session, "c06-schedule-overlap")
    professional = ProfesionalModel(tenant_id=tenant.id, nombre="Profesional demo")
    session.add(professional)
    session.commit()
    professional_id = professional.id
    session.close()
    client = TestClient(create_app(session_factory=session_factory))
    path = f"/profesionales/{professional_id}/horarios"
    accepted = client.put(
        path,
        json={"horarios": [{"dia_semana": 0, "inicio": "09:00", "fin": "12:00"}]},
        headers=headers,
    )
    rejected = client.put(
        path,
        json={
            "horarios": [
                {"dia_semana": 0, "inicio": "09:00", "fin": "12:00"},
                {"dia_semana": 0, "inicio": "11:30", "fin": "13:00"},
            ]
        },
        headers=headers,
    )

    assert accepted.status_code == 200
    assert rejected.status_code == 422
    assert rejected.json()["code"] == "RN-GL-02"
    current = client.get(path, headers=headers)
    assert len(current.json()["horarios"]) == 1
    assert current.json()["horarios"][0]["inicio"] == "09:00:00"


def test_horario_semanal_no_revela_profesional_de_otro_tenant(session_factory):
    session = session_factory()
    _, headers = _owner(session, "c06-schedule-owner")
    other_tenant, _ = _owner(session, "c06-schedule-other")
    professional = ProfesionalModel(tenant_id=other_tenant.id, nombre="Ajeno")
    session.add(professional)
    session.commit()
    foreign_id = professional.id
    session.close()
    client = TestClient(create_app(session_factory=session_factory))

    response = client.get(
        f"/profesionales/{foreign_id}/horarios",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["code"] == "RN-AU-01"
