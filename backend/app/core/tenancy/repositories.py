from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.agenda.models import TenantModel, UsuarioModel

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Repositorio base con aislamiento por tenant. El filtro es interno."""

    def __init__(self, session: Session, model: type[T], *, tenant_id: str | None):
        self.session = session
        self.model = model
        if tenant_id is None and getattr(model, "__tablename__", "") not in {"tenant"}:
            raise ValueError("tenant_id es obligatorio para repositorios de negocio.")
        self.tenant_id = tenant_id

    def _query(self):
        query = self.session.query(self.model)
        if self.tenant_id is not None and hasattr(self.model, "tenant_id"):
            query = query.filter(self.model.tenant_id == self.tenant_id)
        return query

    def get_by_id(self, row_id: str):
        return self._query().filter_by(id=row_id).first()

    def list(self, *, limit: int = 50, cursor: str | None = None):
        limit = max(1, min(int(limit), 200))
        query = self._query()
        if cursor is not None:
            _, created_at, row_id = self._decode_cursor(cursor)
            query = query.filter(
                (self.model.created_at > created_at)
                | ((self.model.created_at == created_at) & (self.model.id > row_id))
            )
        if hasattr(self.model, "deleted_at"):
            query = query.filter(self.model.deleted_at.is_(None))
        return query.order_by(self.model.created_at.asc(), self.model.id.asc()).limit(limit).all()

    def add(self, obj: T) -> T:
        self.session.add(obj)
        return obj

    def flush(self):
        return self.session.flush()

    @staticmethod
    def _encode_cursor(created_at: datetime, row_id: str) -> str:
        payload = {"created_at": created_at.isoformat(), "id": row_id}
        return base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()

    @staticmethod
    def _decode_cursor(cursor: str) -> tuple[str, datetime, str]:
        raw = base64.urlsafe_b64decode(cursor.encode())
        payload = json.loads(raw.decode())
        return (
            payload.get("created_at") or payload.get("createdAt"),
            datetime.fromisoformat(payload["created_at"]),
            payload["id"],
        )


class TenantRepository(BaseRepository[TenantModel]):
    """Excepción explícita del patrón: tenant es global para la creación y resolución de slug."""

    def __init__(self, session: Session):
        super().__init__(session, TenantModel, tenant_id=None)


@dataclass
class UnitOfWork:
    """La única forma de construir repositorios de negocio; el tenant se fija al construir."""

    tenant_id: str
    session: Session

    def __post_init__(self):
        if not self.tenant_id:
            raise ValueError("tenant_id requerido para crear un UnitOfWork.")

    @property
    def tenants(self) -> TenantRepository:
        return TenantRepository(self.session)

    def repository(self, model: type[T]) -> BaseRepository[T]:
        return BaseRepository(self.session, model, tenant_id=self.tenant_id)

    def get_repository(self, model: type[T]) -> BaseRepository[T]:
        return self.repository(model)

    def __getattr__(self, name: str):
        aliases = {
            "usuarios": UsuarioModel,
            "usuario": UsuarioModel,
            "tenant": TenantModel,
            "tenants": TenantModel,
        }
        if name in aliases:
            return self.repository(aliases[name])
        raise AttributeError(name)


__all__ = ["BaseRepository", "TenantRepository", "UnitOfWork"]
