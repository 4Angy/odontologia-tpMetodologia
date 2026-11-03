from __future__ import annotations

from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.modules.pacientes.models import OptInModel, PacienteModel


class PacienteRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, tenant_id: str, q: Optional[str] = None) -> list[PacienteModel]:
        stmt = select(PacienteModel).where(PacienteModel.tenant_id == tenant_id)
        if q:
            like = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    PacienteModel.apellido.ilike(like),
                    PacienteModel.nombre.ilike(like),
                    PacienteModel.dni.ilike(like),
                    PacienteModel.telefono.ilike(like),
                )
            )
        stmt = stmt.order_by(PacienteModel.apellido, PacienteModel.nombre)
        return list(self.session.execute(stmt).scalars().all())

    def get_by_id(self, tenant_id: str, paciente_id: str) -> Optional[PacienteModel]:
        stmt = select(PacienteModel).where(
            PacienteModel.tenant_id == tenant_id,
            PacienteModel.id == paciente_id,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def create(self, paciente: PacienteModel) -> PacienteModel:
        self.session.add(paciente)
        self.session.flush()
        return paciente

    def update(self, paciente: PacienteModel) -> PacienteModel:
        self.session.flush()
        return paciente

    def delete(self, paciente: PacienteModel) -> None:
        self.session.delete(paciente)
        self.session.flush()


class OptInRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_for_paciente(self, tenant_id: str, paciente_id: str) -> list[OptInModel]:
        stmt = select(OptInModel).where(
            OptInModel.tenant_id == tenant_id,
            OptInModel.paciente_id == paciente_id,
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_for_canal(self, tenant_id: str, paciente_id: str, canal: str) -> Optional[OptInModel]:
        stmt = select(OptInModel).where(
            OptInModel.tenant_id == tenant_id,
            OptInModel.paciente_id == paciente_id,
            OptInModel.canal == canal,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def save(self, optin: OptInModel) -> OptInModel:
        self.session.add(optin)
        self.session.flush()
        return optin
