# Tasks — cancelar-turno-liberar-horario

> TDD estricto (R11): cada grupo escribe el test en rojo ANTES del código; mínimo 2 casos por comportamiento. Datos sintéticos/demo únicamente (R14).

## 1. Servicio de dominio `AgendaCancelService` + `resolver_antelacion` (puro, sin HTTP/DB)

- [x] 1.1 Escribir tests del servicio en rojo: cancelación en término cambia a `cancelado` con `cancelled_by/cancelled_at/motivo`, y slot liberado observable (el turno deja de contar como activo en query por tenant/profesional/rango); verificar con `pytest backend/app/modules/agenda/tests/test_cancel_service.py -k "en_termino or libera_horario"` en rojo
- [x] 1.2 Implementar `cancel()` en término + liberación por estado y `resolver_antelacion(tenant, prestacion?)` (UNA global, ignora prestacion, extensible) y verificar que los tests de 1.1 pasan en verde
- [x] 1.3 Escribir tests en rojo de antelación: fuera de término no muta y devuelve `RN-AG-01` con `action: {type: reprogramar, hint}` placeholder; borde exacto `== antelacion` acepta; `antelacion=0` acepta hasta minuto cero; config ausente usa fallback 24h + log; verificar en rojo con `pytest -k "fuera_de_termino or borde_exacto or antelacion_cero or config_fallback"`
- [x] 1.4 Implementar validación UTC aware (`inicio - now_utc >= antelacion`, límite inclusivo, `0` hasta minuto cero, fallback 24h + log, error `RN-AG-01` con placeholder) y verificar que los tests de 1.3 pasan
- [x] 1.5 Escribir tests en rojo de idempotencia + orden + terminales: doble cancelación → `200` sin duplicar auditoría; segundo POST con motivo distinto conserva primera auditoría; `presente/ausente` → `409`; turno pasado (`inicio<now`) → `409`; `reprogramado` (turno viejo migrado) tratado como terminal; orden inmutable tenant→existe→permiso→ya-cancelado→terminales→antelación→motivo; verificar en rojo con `pytest -k "idempotente or motivo_distinto or terminal or pasado or orden"`
- [x] 1.6 Implementar idempotencia por estado (ya `cancelado` → `200` sin efectos, ignora motivo nuevo) + rechazo de terminales/pasado + orden inmutable y verificar que los tests de 1.5 pasan
- [x] 1.7 Escribir tests en rojo de motivo obligatorio como última validación (faltante → `422` sin mutar; vacío/whitespace → `422`; fuera-de-término precede a motivo: sin motivo + fuera de término → `409` RN-AG-01) y verificar en rojo
- [x] 1.8 Implementar validación `motivo` 1–500 caracteres al final del orden y verificar que los tests de 1.7 pasan
- [x] 1.9 Escribir tests en rojo de seña intacta: turno con seña `acreditada` se cancela y la seña sigue `acreditada` con `senia_pendiente_definicion=True`; turno sin seña → flag `False` (2 casos: con y sin seña); verificar en rojo
- [x] 1.10 Implementar no-touch de seña + `senia_pendiente_definicion BOOLEAN DEFAULT FALSE` solo si había seña (desviación temporal RN-CO-03, Owner C-12) y verificar que los tests de 1.9 pasan
- [x] 1.11 Escribir test de concurrencia en rojo: dos `cancel()` concurrentes sobre el mismo turno activo (hilos/transacciones) → uno transiciona y otro cae en idempotencia sin duplicar auditoría; verificar en rojo
- [x] 1.12 Implementar `SELECT FOR UPDATE` o update condicional por estado y verificar que el test de 1.11 pasa

## 2. Persistencia: `turno` mínimo, `config` mínima seed y migración reversible

- [x] 2.1 Escribir tests de repositorio en rojo: toda query filtra por `tenant_id` (R1: un tenant no ve/cancela turnos de otro) + `cancelled_at` se persiste UTC con timezone (R7); columna precisa `antelacion_cancel_hs` (no `antelacion_hs`); `senia_pendiente_definicion DEFAULT FALSE`; verificar en rojo (2+ casos: aislamiento cross-tenant, UTC aware)
- [x] 2.2 Agregar `turno` mínimo seed (id, tenant_id NOT NULL+FK, paciente/profesional/prestacion, inicio/fin timestamptz, estado, cancelled_by/cancelled_at/motivo, senia_pendiente_definicion) y modelo mínimo `Config(tenant_id, antelacion_cancel_hs default 24, CHECK >= 0)` con nota de extensión sin re-migración para C-06/C-07 y verificar que los tests de 2.1 pasan
- [x] 2.3 Escribir migración Alembic con `upgrade` + `downgrade` (R6; crea `turno` mínimo y `config` mínima solo si no existen) y verificar `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` sin errores en DB de test
- [x] 2.4 Agregar seed demo sintético (tenant demo + 1 turno cancelable futuro + 1 dentro de ventana, R14) y verificar que el seed es idempotente (doble ejecución sin duplicados)

## 3. API HTTP: `POST /turnos/:id/cancelar` + `GET/PUT /config` (tenant, RBAC unión, DTOs, errores)

- [x] 3.1 Escribir tests de API en rojo: `POST /turnos/:id/cancelar` en término → `200` + `cancelado`; fuera de término → `409 {code: RN-AG-01, action: {type: reprogramar, hint}}` placeholder en español-AR (R9, RN-GL-01); turno pasado → `409`; verificar en rojo con `pytest backend/app/modules/agenda/tests/test_cancel_api.py`
- [x] 3.2 Implementar endpoint + DTOs Pydantic v2 con `extra='forbid'` (R3/R4: nunca exponer modelos) + tenant siempre del JWT validado (R2) + mapeo de `action` placeholder y verificar que los tests de 3.1 pasan
- [x] 3.3 Escribir tests de API en rojo: RBAC unión (sin permiso → `403`; `odontologo` solo sus turnos; `recepcion+odontologo` cancela cualquiera vía recepcion; `profesional.usuario_id` null → `403` con code — 4 casos) + aislamiento (inexistente o cross-tenant con JWT válido → `404` indistinguible; sin/inválido JWT → `403`; R1/RN-AU-01); verificar en rojo
- [x] 3.4 Implementar `require_role` por unión de roles + filtro `tenant_id` en la query (R1) + fallback null + códigos `403/404` precisos y verificar que los tests de 3.3 pasan
- [x] 3.5 Escribir tests de API en rojo para `GET/PUT /config`: `dueno` actualiza `antelacion_cancel_hs` (rige futuro, no retroactivo; `0` válido); no-`dueno` → `403`; valor negativo → `422` (2+ casos); verificar en rojo
- [x] 3.6 Implementar `GET/PUT /config` con permiso solo-`dueno` y validación `>= 0` y verificar que los tests de 3.5 pasan

## 4. Frontend: cancelar con motivo + placeholder reprogramar deshabilitado

- [x] 4.1 Escribir tests de componente en rojo (TS estricto, sin `any`, R10): modal exige motivo (botón deshabilitado sin motivo) + error `RN-AG-01` muestra mensaje español-AR con acción "Reprogramar" deshabilitada/informativa por placeholder (2 casos); verificar en rojo con `vitest run src/features/agenda/__tests__/cancelar-turno.test.tsx`
- [x] 4.2 Implementar botón Cancelar + modal de motivo + llamada al endpoint (componente PascalCase, `action.hint` renderizado informativo) y verificar que los tests de 4.1 pasan sin errores de tipo (`tsc --noEmit`)

## 5. Verificación integrada del slice (observable, no disponibilidad; deuda C-09 declarada)

- [x] 5.1 Ejecutar suite completa del slice (`pytest backend/app/modules/agenda + vitest run src/features/agenda`) y verificar todo en verde con cobertura de los 9 requisitos del spec (incluye orden, concurrencia, pasado, `antelacion=0`, fallback, unión multi-rol, flag de seña)
- [x] 5.2 Verificar manualmente el flujo E2E con datos sintéticos (cancelar en término → query de activos ya no lo devuelve; cancelar fuera de término ofrece reprogramar placeholder; envíos/notificaciones no tocados = deuda C-09) y validar el change con `openspec validate --change cancelar-turno-liberar-horario`
