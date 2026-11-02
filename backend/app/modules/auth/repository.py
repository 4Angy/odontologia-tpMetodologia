"""Repositorio del estado de tokens (`auth_token`) — task 2.1.

Toda query filtra por `tenant_id` (R1): el repositorio se construye con el
tenant autenticado, igual que `UnitOfWork` en `core/tenancy`.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.auth.models import AuthTokenModel, PropositoToken

_UTC = timezone.utc


@dataclass(frozen=True)
class EstadoToken:
    """Veredicto sobre un token presentado para rotación o uso."""

    existe: bool
    dentro_de_plazo: bool
    revocado: bool
    ya_usado: bool
    familia_id: str | None = None

    @property
    def es_reuse(self) -> bool:
        """Presentar un token que ya se usó o que estaba revocado es reuse."""
        return self.existe and (self.revocado or self.ya_usado)

    @property
    def vigente(self) -> bool:
        return self.existe and self.dentro_de_plazo and not self.es_reuse


class AuthTokenRepository:
    """Operaciones sobre `auth_token` acotadas al tenant autenticado."""

    def __init__(self, session: Session, tenant_id: str | None = None) -> None:
        self._session = session
        self._tenant_id = tenant_id

    # --- Escrituras ---------------------------------------------------------

    def crear(
        self,
        *,
        jti: str,
        usuario_id: str,
        familia_id: str,
        proposito: PropositoToken,
        expira: datetime,
        tenant_id: str | None = None,
        now: datetime | None = None,
    ) -> AuthTokenModel:
        """Registra un token nuevo (fila con `revoked=False`, `used_at=NULL`)."""
        tenant = self._tenant_id or tenant_id
        if tenant is None:
            raise ValueError("Se necesita tenant_id (ctor o parámetro) para crear un token.")
        fila = AuthTokenModel(
            id=jti,
            usuario_id=usuario_id,
            familia_id=familia_id,
            proposito=proposito.value,
            expira=expira,
            tenant_id=tenant,
            created_at=now or datetime.now(_UTC),
        )
        self._session.add(fila)
        self._session.flush()
        return fila

    def rotar(
        self, *, jti_viejo: str, jti_nuevo: str, expira: datetime, now: datetime
    ) -> AuthTokenModel | None:
        """Marca el jti viejo como usado y crea el nuevo en la misma familia."""
        viejo = self.obtener(jti_viejo)
        if viejo is None:
            return None
        viejo.used_at = now
        return self.crear(
            jti=jti_nuevo,
            usuario_id=viejo.usuario_id,
            familia_id=viejo.familia_id,
            proposito=PropositoToken.REFRESH,
            expira=expira,
            tenant_id=viejo.tenant_id,
            now=now,
        )

    def revocar_familia(self, familia_id: str, *, now: datetime | None = None) -> int:
        """Revoca en cascada: todas las filas activas de la familia."""
        filas = self._session.scalars(
            select(AuthTokenModel).where(
                AuthTokenModel.familia_id == familia_id,
                AuthTokenModel.revoked.is_(False),
            )
        ).all()
        for fila in filas:
            fila.revoked = True
            fila.revoked_at = now or datetime.now(_UTC)
        self._session.flush()
        return len(filas)

    def revocar_de_usuario(self, usuario_id: str, *, now: datetime | None = None) -> int:
        """Revoca todas las familias del usuario (post reset de password)."""
        filas = self._session.scalars(
            select(AuthTokenModel).where(
                AuthTokenModel.usuario_id == usuario_id,
                AuthTokenModel.revoked.is_(False),
            )
        ).all()
        for fila in filas:
            fila.revoked = True
            fila.revoked_at = now or datetime.now(_UTC)
        self._session.flush()
        return len(filas)

    def marcar_usado_reset(self, jti: str, *, now: datetime) -> None:
        """El reset es de uso único: se marca como usado y revocado."""
        fila = self.obtener(jti, proposito=PropositoToken.RESET)
        if fila is None:
            return
        fila.used_at = now
        fila.revoked = True
        fila.revoked_at = now
        self._session.flush()

    def purgar_expirados(self, *, now: datetime) -> int:
        """Borra filas vencidas (purge cheap dentro del flujo de refresh)."""
        resultado = self._session.execute(
            delete(AuthTokenModel).where(AuthTokenModel.expira < now)
        )
        return int(resultado.rowcount or 0)

    # --- Lecturas -----------------------------------------------------------

    def obtener(
        self, jti: str, *, proposito: PropositoToken | None = PropositoToken.REFRESH
    ) -> AuthTokenModel | None:
        stmt = select(AuthTokenModel).where(AuthTokenModel.id == jti)
        if self._tenant_id is not None:
            stmt = stmt.where(AuthTokenModel.tenant_id == self._tenant_id)
        if proposito is not None:
            stmt = stmt.where(AuthTokenModel.proposito == proposito.value)
        return self._session.scalars(stmt).first()

    def estado(self, fila: AuthTokenModel, *, now: datetime | None = None) -> EstadoToken:
        """Veredicto de un token presentado (reuse/vigente/expirado)."""
        ahora = now or datetime.now(_UTC)
        dentro = fila.expira > ahora
        return EstadoToken(
            existe=True,
            dentro_de_plazo=dentro,
            revocado=bool(fila.revoked),
            ya_usado=fila.used_at is not None,
            familia_id=fila.familia_id,
        )
