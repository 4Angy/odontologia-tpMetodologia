"""Router de gestión de usuarios del tenant (C-03): /users/invite, /users.

Solo accesible por `dueno` (US-011 CA-2). La invitación crea un usuario con
password_hash vacío (pendiente de reset) y roles asignados.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import deps
from app.core.logging import log_event
from app.core.security import AuthUser, require_roles
from app.modules.agenda.models import UsuarioModel, UsuarioRoles
from app.modules.tenancy.schemas import InviteRequest, UserResponse

logger = logging.getLogger("odontologia.tenancy")

router = APIRouter()


@router.post("/users/invite", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def invite_user(
    payload: InviteRequest,
    user: AuthUser = Depends(require_roles("dueno")),
    session: Session = Depends(deps.get_session),
) -> UserResponse:
    """Invita un usuario al tenant. Solo accesible por `dueno`."""
    # Validar roles válidos
    roles_validos = {UsuarioRoles.RECEPCION.value, UsuarioRoles.ODONTOLOGO.value, UsuarioRoles.DUENO.value}
    for rol in payload.roles:
        if rol not in roles_validos:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "RN-AU-04",
                    "message": f"Rol inválido: {rol}. Los roles válidos son: recepcion, odontologo, dueno.",
                },
            )

    # Verificar duplicado en el mismo tenant (R1)
    existente = (
        session.query(UsuarioModel)
        .filter_by(tenant_id=user.tenant_id, email=payload.email)
        .first()
    )
    if existente:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "RN-AU-04",
                "message": "El email ya está registrado en este consultorio.",
            },
        )

    # Crear usuario
    nuevo_usuario = UsuarioModel(
        tenant_id=user.tenant_id,
        email=payload.email,
        nombre=payload.nombre,
        password_hash=None,  # pendiente de reset
        roles=payload.roles,
        activo=True,
    )
    session.add(nuevo_usuario)
    session.commit()
    session.refresh(nuevo_usuario)

    log_event(
        logger,
        logging.INFO,
        "usuarios.invitacion",
        usuario_id=nuevo_usuario.id,
        tenant_id=user.tenant_id,
        email=nuevo_usuario.email,
        roles=nuevo_usuario.roles,
        invitado_por=user.id,
    )

    return UserResponse(
        id=nuevo_usuario.id,
        email=nuevo_usuario.email,
        nombre=nuevo_usuario.nombre,
        roles=nuevo_usuario.roles,
        activo=nuevo_usuario.activo,
    )


@router.get("/users", response_model=list[UserResponse])
def list_users(
    user: AuthUser = Depends(require_roles("dueno")),
    session: Session = Depends(deps.get_session),
) -> list[UserResponse]:
    """Lista los usuarios del tenant. Solo accesible por `dueno`."""
    usuarios = (
        session.query(UsuarioModel)
        .filter_by(tenant_id=user.tenant_id)
        .order_by(UsuarioModel.created_at)
        .all()
    )
    return [
        UserResponse(
            id=u.id,
            email=u.email,
            nombre=u.nombre,
            roles=u.roles,
            activo=u.activo,
        )
        for u in usuarios
    ]


__all__ = ["router"]
