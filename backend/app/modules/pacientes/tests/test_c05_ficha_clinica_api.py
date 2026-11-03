from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import AuditEventModel
from app.core.config import Settings
from app.core.security import mint_token
from app.main import create_app
from app.modules.agenda.models import ProfesionalModel, TenantModel, UsuarioModel
from app.modules.pacientes import attachment_storage
from app.modules.pacientes.attachment_storage import S3AttachmentStorage
from app.modules.pacientes.models import EvolucionModel, PacienteModel


def _usuario(
    session: Session,
    tenant: TenantModel,
    *,
    rol: str,
    email: str,
) -> tuple[UsuarioModel, str]:
    usuario = UsuarioModel(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        email=email,
        nombre=email,
        roles=[rol],
        activo=True,
    )
    session.add(usuario)
    session.flush()
    token = mint_token(
        user_id=usuario.id,
        tenant_id=tenant.id,
        roles=usuario.roles,
        email=usuario.email,
        token_type="access",
    )
    return usuario, token


def _paciente(session: Session, tenant: TenantModel) -> PacienteModel:
    paciente = PacienteModel(
        tenant_id=tenant.id,
        nombre="Paciente",
        apellido="Sintético",
        saldo=0,
    )
    session.add(paciente)
    session.commit()
    return paciente


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class _FakeAttachmentStorage:
    def __init__(self) -> None:
        self.uploads: list[tuple[str, bytes, str]] = []

    def put(self, key: str, content: bytes, content_type: str) -> None:
        self.uploads.append((key, content, content_type))

    def delete(self, key: str) -> None:
        return None

    def presign_get(self, key: str, filename: str) -> str:
        return f"https://storage.invalid/{key}"


def test_evolucion_cumple_adr003_y_registra_auditoria(session_factory):
    session = session_factory()
    tenant = TenantModel(id=str(uuid.uuid4()), slug="c05-evolucion", nombre="C05")
    session.add(tenant)
    session.flush()
    odontologo, token = _usuario(
        session, tenant, rol="odontologo", email="odontologo-c05@test.com"
    )
    profesional = ProfesionalModel(
        tenant_id=tenant.id,
        usuario_id=odontologo.id,
        nombre="Odontóloga sintética",
        activo=True,
    )
    session.add(profesional)
    paciente = _paciente(session, tenant)

    app = create_app(session_factory=session_factory)
    app.state.attachment_storage = _FakeAttachmentStorage()
    client = TestClient(app)
    fecha = "2026-11-03T16:00:00+00:00"
    response = client.post(
        f"/pacientes/{paciente.id}/evoluciones",
        headers=_headers(token),
        json={
            "profesional_id": profesional.id,
            "fecha": fecha,
            "motivo": "Control sintético",
            "detalle": "Detalle clínico sintético",
            "pieza_fdi_slot": "tooth",
            "pieza_fdi_numero": 11,
            "odontograma_ref": None,
            "firma_simple": True,
        },
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["profesional_id"] == profesional.id
    assert datetime.fromisoformat(data["fecha"]).astimezone(timezone.utc) == datetime(
        2026, 11, 3, 16, tzinfo=timezone.utc
    )
    assert data["pieza_fdi_slot"] == "tooth"
    assert data["pieza_fdi_numero"] == 11
    assert data["firmado_at"] is not None
    assert "no constituye firma digital" in data["alcance_firma"].lower()

    event = session.execute(
        select(AuditEventModel).where(
            AuditEventModel.recurso == "evolucion",
            AuditEventModel.recurso_id == data["id"],
        )
    ).scalar_one()
    assert event.actor_id == odontologo.id
    assert event.ocurrido_at.tzinfo is not None
    assert {"motivo", "detalle"} <= set(event.campos)
    assert "Detalle clínico sintético" not in str(event.campos)

    updated = client.put(
        f"/pacientes/{paciente.id}/evoluciones/{data['id']}",
        headers=_headers(token),
        json={
            "profesional_id": profesional.id,
            "fecha": fecha,
            "motivo": "Control actualizado",
            "detalle": "Detalle actualizado sintético",
            "pieza_fdi_slot": "tooth",
            "pieza_fdi_numero": 11,
            "odontograma_ref": None,
            "firma_simple": True,
        },
    )
    assert updated.status_code == 200, updated.text
    update_event = session.execute(
        select(AuditEventModel).where(
            AuditEventModel.recurso == "evolucion",
            AuditEventModel.recurso_id == data["id"],
            AuditEventModel.accion == "evolucion.actualizada",
        )
    ).scalar_one()
    assert update_event.actor_id == odontologo.id
    assert {"motivo", "detalle"} <= set(update_event.campos)
    assert "Detalle actualizado sintético" not in str(update_event.campos)
    session.close()


def test_falla_de_auditoria_revierte_creacion_de_evolucion(
    session_factory, monkeypatch
):
    import app.modules.pacientes.service as paciente_service

    session = session_factory()
    tenant = TenantModel(id=str(uuid.uuid4()), slug="c05-audit-atomic", nombre="C05")
    session.add(tenant)
    session.flush()
    odontologo, token = _usuario(
        session, tenant, rol="odontologo", email="odontologo-atomic@test.com"
    )
    profesional = ProfesionalModel(
        tenant_id=tenant.id,
        usuario_id=odontologo.id,
        nombre="Odontólogo sintético",
        activo=True,
    )
    session.add(profesional)
    paciente = _paciente(session, tenant)
    patient_id = paciente.id
    professional_id = profesional.id
    session.close()

    def auditoria_falla(*args, **kwargs):
        raise RuntimeError("fallo sintético")

    monkeypatch.setattr(paciente_service, "registrar_auditoria", auditoria_falla)
    client = TestClient(
        create_app(session_factory=session_factory),
        raise_server_exceptions=False,
    )
    response = client.post(
        f"/pacientes/{patient_id}/evoluciones",
        headers=_headers(token),
        json={
            "profesional_id": professional_id,
            "motivo": "Control sintético",
            "detalle": "No debe persistir",
        },
    )
    check = session_factory()
    try:
        assert response.status_code == 500
        assert check.execute(select(EvolucionModel)).scalars().all() == []
        assert check.execute(select(AuditEventModel)).scalars().all() == []
    finally:
        check.close()


def test_evolucion_rechaza_ancla_fdi_incompleta_sin_persistir(session_factory):
    session = session_factory()
    tenant = TenantModel(id=str(uuid.uuid4()), slug="c05-ancla", nombre="C05")
    session.add(tenant)
    session.flush()
    odontologo, token = _usuario(
        session, tenant, rol="odontologo", email="odontologo-ancla@test.com"
    )
    profesional = ProfesionalModel(
        tenant_id=tenant.id,
        usuario_id=odontologo.id,
        nombre="Odontólogo sintético",
        activo=True,
    )
    session.add(profesional)
    paciente = _paciente(session, tenant)
    app = create_app(session_factory=session_factory)
    app.state.attachment_storage = _FakeAttachmentStorage()
    client = TestClient(app)

    response = client.post(
        f"/pacientes/{paciente.id}/evoluciones",
        headers=_headers(token),
        json={
            "profesional_id": profesional.id,
            "motivo": "Control",
            "detalle": "Sintético",
            "pieza_fdi_slot": "tooth",
            "pieza_fdi_numero": None,
        },
    )

    assert response.status_code == 422
    assert session.execute(select(EvolucionModel)).scalars().all() == []
    session.close()


def test_evolucion_rbac_y_aislamiento_de_tenant(session_factory):
    session = session_factory()
    tenant = TenantModel(id=str(uuid.uuid4()), slug="c05-rbac", nombre="C05")
    otro_tenant = TenantModel(
        id=str(uuid.uuid4()), slug="c05-rbac-otro", nombre="C05 otro"
    )
    session.add_all([tenant, otro_tenant])
    session.flush()
    odontologo, token_odontologo = _usuario(
        session, tenant, rol="odontologo", email="odontologo-rbac@test.com"
    )
    _, token_recepcion = _usuario(
        session, tenant, rol="recepcion", email="recepcion-rbac@test.com"
    )
    _, token_dueno = _usuario(
        session, tenant, rol="dueno", email="dueno-rbac@test.com"
    )
    _, token_otro = _usuario(
        session, otro_tenant, rol="dueno", email="dueno-otro-rbac@test.com"
    )
    profesional = ProfesionalModel(
        tenant_id=tenant.id,
        usuario_id=odontologo.id,
        nombre="Odontólogo sintético",
        activo=True,
    )
    session.add(profesional)
    paciente = _paciente(session, tenant)
    client = TestClient(create_app(session_factory=session_factory))
    creada = client.post(
        f"/pacientes/{paciente.id}/evoluciones",
        headers=_headers(token_odontologo),
        json={
            "profesional_id": profesional.id,
            "motivo": "Control",
            "detalle": "Historia sintética",
        },
    )
    assert creada.status_code == 201, creada.text

    assert client.get(
        f"/pacientes/{paciente.id}/evoluciones", headers=_headers(token_dueno)
    ).status_code == 200
    assert client.get(
        f"/pacientes/{paciente.id}/evoluciones", headers=_headers(token_recepcion)
    ).status_code == 403
    ajena = client.get(
        f"/pacientes/{paciente.id}/evoluciones", headers=_headers(token_otro)
    )
    assert ajena.status_code in {403, 404}
    assert "Historia sintética" not in ajena.text
    session.close()


def test_presupuesto_borrador_y_crud_derivan_el_saldo(session_factory):
    session = session_factory()
    tenant = TenantModel(id=str(uuid.uuid4()), slug="c05-presupuesto", nombre="C05")
    session.add(tenant)
    session.flush()
    odontologo, token = _usuario(
        session, tenant, rol="odontologo", email="odontologo-presupuesto@test.com"
    )
    _, token_recepcion = _usuario(
        session, tenant, rol="recepcion", email="recepcion-presupuesto@test.com"
    )
    paciente = _paciente(session, tenant)
    client = TestClient(create_app(session_factory=session_factory))
    headers = _headers(token)
    path = f"/pacientes/{paciente.id}/presupuestos"

    creado = client.post(
        path,
        headers=headers,
        json={
            "items": [
                {"descripcion": "Consulta sintética", "monto_cents": 1250},
                {"descripcion": "Tratamiento sintético", "monto_cents": 8750},
            ],
            "estado": "borrador",
        },
    )
    assert creado.status_code == 201, creado.text
    presupuesto = creado.json()
    assert presupuesto["estado"] == "borrador"
    assert presupuesto["total_cents"] == 10_000
    exceso = client.post(
        path,
        headers=headers,
        json={
            "items": [
                {"descripcion": "Ítem sintético", "monto_cents": 2_147_483_647},
                {"descripcion": "Ítem sintético", "monto_cents": 1},
            ]
        },
    )
    assert exceso.status_code == 422
    assert client.get(
        path, headers=_headers(token_recepcion)
    ).status_code == 200
    assert client.post(
        path,
        headers=_headers(token_recepcion),
        json={"items": [{"descripcion": "No autorizado", "monto_cents": 100}]},
    ).status_code == 403
    assert client.get(
        f"/pacientes/{paciente.id}", headers=headers
    ).json()["saldo"] == 0

    presupuesto_path = f"{path}/{presupuesto['id']}"
    aprobado = client.patch(
        f"{presupuesto_path}/estado",
        headers=headers,
        json={"estado": "aprobado"},
    )
    assert aprobado.status_code == 200, aprobado.text
    assert client.get(
        f"/pacientes/{paciente.id}", headers=headers
    ).json()["saldo"] == 10_000
    aceptado = client.patch(
        f"{presupuesto_path}/estado",
        headers=headers,
        json={"estado": "aceptado"},
    )
    assert aceptado.status_code == 200, aceptado.text
    assert client.get(
        f"/pacientes/{paciente.id}", headers=headers
    ).json()["saldo"] == 10_000

    editado = client.put(
        presupuesto_path,
        headers=headers,
        json={
            "items": [{"descripcion": "Tratamiento actualizado", "monto_cents": 7000}],
            "notas": "Nota sintética",
        },
    )
    assert editado.status_code == 200, editado.text
    assert editado.json()["total_cents"] == 7000
    assert client.get(
        f"/pacientes/{paciente.id}", headers=headers
    ).json()["saldo"] == 7000

    eliminado = client.delete(presupuesto_path, headers=headers)
    assert eliminado.status_code == 204
    assert client.get(
        f"/pacientes/{paciente.id}", headers=headers
    ).json()["saldo"] == 0
    eventos = session.execute(
        select(AuditEventModel).where(
            AuditEventModel.recurso == "presupuesto",
            AuditEventModel.tenant_id == tenant.id,
        )
    ).scalars().all()
    assert {evento.accion for evento in eventos} >= {
        "presupuesto.creado",
        "presupuesto.estado_actualizado",
        "presupuesto.actualizado",
        "presupuesto.eliminado",
    }
    session.close()


def test_adjunto_rechaza_url_no_confiable_y_metadatos_sin_archivo(session_factory):
    session = session_factory()
    tenant = TenantModel(id=str(uuid.uuid4()), slug="c05-adjunto", nombre="C05")
    session.add(tenant)
    session.flush()
    _, token = _usuario(
        session, tenant, rol="odontologo", email="odontologo-adjunto@test.com"
    )
    paciente = _paciente(session, tenant)
    app = create_app(session_factory=session_factory)
    app.state.attachment_storage = _FakeAttachmentStorage()
    client = TestClient(app)

    response = client.post(
        f"/pacientes/{paciente.id}/adjuntos",
        headers=_headers(token),
        json={
            "nombre": "imagen.png",
            "tipo": "image/png",
            "tamano_bytes": 64,
            "url": "https://sitio-no-confiable.invalid/imagen.png",
        },
    )

    assert response.status_code == 422
    session.close()


@pytest.mark.parametrize(
    ("nombre", "tipo", "contenido"),
    [
        ("radiografia.jpg", "image/jpeg", b"\xff\xd8\xff" + b"sintetico"),
        ("imagen.png", "image/png", b"\x89PNG\r\n\x1a\n" + b"sintetico"),
        ("nota.pdf", "application/pdf", b"%PDF-1.7\nsintetico"),
    ],
)
def test_adjuntos_validos_se_guardan_y_descargan_con_url_temporal(
    session_factory, nombre, tipo, contenido
):
    session = session_factory()
    tenant = TenantModel(id=str(uuid.uuid4()), slug=f"c05-adjunto-{tipo[:3]}", nombre="C05")
    session.add(tenant)
    session.flush()
    odontologo, token = _usuario(
        session, tenant, rol="odontologo", email=f"odontologo-{tipo[:3]}@test.com"
    )
    paciente = _paciente(session, tenant)
    storage = _FakeAttachmentStorage()
    app = create_app(session_factory=session_factory)
    app.state.attachment_storage = storage
    client = TestClient(app)
    base = f"/pacientes/{paciente.id}/adjuntos"

    uploaded = client.post(
        base,
        content=contenido,
        headers={
            **_headers(token),
            "Content-Type": tipo,
            "X-Filename": nombre,
        },
    )
    assert uploaded.status_code == 201, uploaded.text
    assert "url" not in uploaded.json()
    assert storage.uploads == [
        (f"tenants/{tenant.id}/pacientes/{paciente.id}/{uploaded.json()['id']}", contenido, tipo)
    ]

    listed = client.get(base, headers=_headers(token))
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert "storage_key" not in listed.json()[0]

    download = client.get(
        f"{base}/{uploaded.json()['id']}/descarga", headers=_headers(token)
    )
    assert download.status_code == 200, download.text
    assert download.json()["url"].startswith("https://storage.invalid/")
    assert download.json()["expires_in_seconds"] == 300
    session.close()


def test_adjuntos_rechazan_tipo_falso_y_mas_de_10_mib(session_factory):
    session = session_factory()
    tenant = TenantModel(id=str(uuid.uuid4()), slug="c05-adjunto-invalid", nombre="C05")
    session.add(tenant)
    session.flush()
    _, token = _usuario(
        session, tenant, rol="odontologo", email="odontologo-invalid-adjunto@test.com"
    )
    paciente = _paciente(session, tenant)
    storage = _FakeAttachmentStorage()
    app = create_app(session_factory=session_factory)
    app.state.attachment_storage = storage
    client = TestClient(app)
    url = f"/pacientes/{paciente.id}/adjuntos"

    tipo_falso = client.post(
        url,
        content=b"<html>not an image</html>",
        headers={
            **_headers(token),
            "Content-Type": "image/png",
            "X-Filename": "falso.png",
        },
    )
    demasiado_grande = client.post(
        url,
        content=b"\xff\xd8\xff" + b"x" * (10 * 1024 * 1024),
        headers={
            **_headers(token),
            "Content-Type": "image/jpeg",
            "X-Filename": "grande.jpg",
        },
    )

    assert tipo_falso.status_code == 422
    assert demasiado_grande.status_code == 413
    assert storage.uploads == []
    session.close()


def test_s3_attachment_storage_requests_encryption_and_short_lived_urls(
    monkeypatch,
):
    s3_client = Mock()
    s3_client.generate_presigned_url.return_value = "https://storage.invalid/signed"
    monkeypatch.setattr(attachment_storage.boto3, "client", Mock(return_value=s3_client))
    storage = S3AttachmentStorage(
        Settings(
            _env_file=None,
            database_url="sqlite://",
            redis_url="redis://localhost",
            attachments_s3_bucket="private-test-bucket",
        )
    )

    storage.put("private/key", b"%PDF-1.7\nsynthetic", "application/pdf")
    url = storage.presign_get("private/key", "file.pdf")

    s3_client.put_object.assert_called_once_with(
        Bucket="private-test-bucket",
        Key="private/key",
        Body=b"%PDF-1.7\nsynthetic",
        ContentType="application/pdf",
        ServerSideEncryption="AES256",
    )
    assert url == "https://storage.invalid/signed"
    assert s3_client.generate_presigned_url.call_args.kwargs["ExpiresIn"] == 300


def test_adjunto_no_se_descarga_desde_otro_tenant(session_factory):
    session = session_factory()
    tenant = TenantModel(id=str(uuid.uuid4()), slug="c05-adjunto-own", nombre="C05")
    otro_tenant = TenantModel(
        id=str(uuid.uuid4()), slug="c05-adjunto-other", nombre="C05"
    )
    session.add_all([tenant, otro_tenant])
    session.flush()
    _, token = _usuario(
        session, tenant, rol="odontologo", email="odontologo-own-adjunto@test.com"
    )
    _, otro_token = _usuario(
        session, otro_tenant, rol="dueno", email="dueno-other-adjunto@test.com"
    )
    _, recepcion_token = _usuario(
        session, tenant, rol="recepcion", email="recepcion-own-adjunto@test.com"
    )
    paciente = _paciente(session, tenant)
    storage = _FakeAttachmentStorage()
    app = create_app(session_factory=session_factory)
    app.state.attachment_storage = storage
    client = TestClient(app)
    uploaded = client.post(
        f"/pacientes/{paciente.id}/adjuntos",
        content=b"%PDF-1.7\nsintetico",
        headers={
            **_headers(token),
            "Content-Type": "application/pdf",
            "X-Filename": "nota.pdf",
        },
    )
    assert uploaded.status_code == 201, uploaded.text

    response = client.get(
        f"/pacientes/{paciente.id}/adjuntos/{uploaded.json()['id']}/descarga",
        headers=_headers(otro_token),
    )
    assert response.status_code == 404
    assert client.get(
        f"/pacientes/{paciente.id}/adjuntos",
        headers=_headers(recepcion_token),
    ).status_code == 403
    assert storage.uploads[0][0] not in response.text
    session.close()
