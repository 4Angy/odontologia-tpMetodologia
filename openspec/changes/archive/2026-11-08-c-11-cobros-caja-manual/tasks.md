# Tasks

## 1. Migración y modelos

- [x] 1.1 Crear migración `014_cobros_caja` (down_revision `012_notificaciones`) con tablas `cobro` y `cierre_caja`, índices y constraints; verificar `alembic upgrade head` y `alembic downgrade -1` en SQLite/Postgres.
- [x] 1.2 Implementar `app/modules/cobros/models.py` (`CobroModel`, `CierreCajaModel`) con `TenantMixin`/`AuditMixin` y verificar import sin errores.
- [x] 1.3 Agregar tests de migración (`test_migration_014_cobros.py`) verificando columnas, índices y downgrade.

## 2. Backend core (schemas, repository, service)

- [x] 2.1 Crear `schemas.py` con `CobroCreate/Update/Response`, `CierreCajaCreate/Response`, `AjusteCreate`, `DeudaResponse` con `extra='forbid'`; verificar validación con tests unitarios de schema.
- [x] 2.2 Implementar `repository.py` con filtros por `tenant_id` y ordenamientos; verificar tests de aislamiento por tenant.
- [x] 2.3 Implementar `service.py`: alta de cobro, `saldo_derivado` restando cobros, listado de deudas, cierre del día, ajuste auditado; verificar tests de servicio (saldo derivado, inmutabilidad, ajuste deja auditoría).
- [x] 2.4 Actualizar `PacienteService.saldo_derivado()` para restar cobros y dejar hook `_pagos_del_paciente`; verificar tests existentes de pacientes siguen pasando.

## 3. API y RBAC

- [x] 3.1 Implementar `router.py` con `CRUD /cobros`, `GET /deudas`, `POST /caja/cierre-dia`, `POST /caja/ajuste`, `GET /caja/cierre-dia`; registrar en `app/main.py`; verificar OpenAPI y health.
- [x] 3.2 Aplicar RBAC (cobro: recepcion/dueno; cierre/ajuste: dueno) y verificar tests de permisos.
- [x] 3.3 Tests de API (`test_cobros_api.py`): alta <30s, saldo derivado, deudas ordenadas, cierre inmutable, ajuste auditoría, aislamiento por tenant.

## 4. Frontend

- [x] 4.1 Crear feature `caja` (api.ts + CajaPage) con cobro rápido, deudas y cierre del día; reemplazar placeholder en `pages/index.tsx`; verificar build (`npm run build`).
- [x] 4.2 Declarar alcance honesto (caja manual sin comprobantes) y verificar render en tests de componente.
- [x] 4.3 Tests de frontend (`__tests__/caja*.test.tsx`) para flujos básicos.

## 5. Integración y verificación final

- [x] 5.1 Ejecutar suite completa backend (`pytest`) y frontend (`npm test`) y verificar sin regresiones.
- [x] 5.2 Validar change con `openspec validate c-11-cobros-caja-manual` y verificar artefactos completos.