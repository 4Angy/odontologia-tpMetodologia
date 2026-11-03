# Tasks

## 1. Decisiones y caracterización del catálogo existente

- [x] 1.1 Mantener C-06 funcionalmente independiente de C-04/C-05 y dependiente de C-03; documentar que el chain Alembic existente exige aplicar 005 antes de 006 al desplegar, sin convertirlo en dependencia funcional ni editar revisiones existentes.
- [x] 1.2 Aplicar las decisiones ya fijadas: cancelación global por tenant de 24 h sin override por prestación; reserva global de 2 h configurable por dueño; horarios semanales por profesional en timezone del tenant, bloqueos como excepciones e inicios cada 30 min con duración completa. Seed limitado a tenant-demo y auditoría reutilizando el contrato común de C-04.
- [x] 1.3 Añadir pruebas de caracterización del CRUD actual de profesionales/prestaciones/bloqueos/config y migración 006; ejecutar tests de agenda y validar línea base antes de tocar implementación.
- [x] 1.4 Escribir pruebas rojas por cada gap aprobado, con al menos dos casos por comportamiento (válido e inválido/denegado); usar tenants y catálogo sintéticos, demostrando inicialmente que los defectos se reproducen (R11/R14).

## 2. Integridad tenant, temporal y auditoría backend

- [x] 2.1 Validar cada relación de bloqueo con profesional del mismo tenant y mapear errores de negocio con código trazable; probar profesional propio, ajeno e inexistente con respuestas no reveladoras (R1/R2/R9).
- [x] 2.2 Validar datetimes aware, normalización UTC y rangos `fin > inicio` antes de persistencia en endpoints de bloqueo; probar naive, offsets, límite y no mutación ante error (R7).
- [x] 2.3 Validar CRUD y permisos existentes de profesionales/prestaciones/bloqueos/config, incluidas propiedades extra; probar DTOs `extra='forbid'`, no exposición ORM, roles permitidos y denegados (R3/R4).
- [x] 2.4 Incorporar auditoría transaccional del catálogo/config usando el contrato común aprobado; probar actor/tenant/instante/cambio, lectura solo autorizada del dueño y rollback de mutación ante fallo de auditoría (RN-GL-02/R7).
- [x] 2.5 Validar que valores económicos de `precio_ref` son centavos enteros y no `float`; cubrir nulo, cero y valores fuera de rango acordado en DTO, servicio y pruebas (R5).

## 3. Disponibilidad reutilizable y seed demo

- [x] 3.1 Crear pruebas unitarias rojas del cálculo de candidatos para horario semanal, duración total, bloqueos excepcionales, mínimo global configurable, inicios cada 30 min, normalización UTC y turnos activos cuando el dominio esté disponible.
- [x] 3.2 Completar el servicio reutilizable de disponibilidad sin duplicar endpoints de C-07/C-08; verificar que cada candidato cabe íntegramente en el horario y no atraviesa bloqueos, así como turnos y antelación, con suite de dominio/backend.
- [x] 3.3 Completar seed de catálogo demo con datos sintéticos acordados y operaciones idempotentes; ejecutarlo dos veces y verificar que no duplica profesionales/prestaciones ni modifica tenants reales.

## 4. Interfaz de catálogo y configuración

- [x] 4.1 Crear pruebas Vitest en rojo para catálogo/config, validaciones de formulario, roles, errores y estados vacíos/cargando; verificar tipado estricto y al menos dos escenarios por comportamiento (R10/R11).
- [x] 4.2 Implementar vistas de profesionales y prestaciones respetando RBAC; comprobar CRUD de rol autorizado, lectura sin escritura para rol de consulta y ausencia de recursos de otro tenant mediante tests/UI.
- [x] 4.3 Implementar gestión de bloqueos con fecha/hora timezone-aware y errores claros; comprobar que intervalos inválidos y profesionales ajenos no se aceptan.
- [x] 4.4 Reemplazar placeholder de configuración por controles de dueño para valores globales aprobados; verificar defaults de 24 h/2 h, persistencia tenant-scoped, ausencia de override por prestación y que un cambio no afecta retroactivamente decisiones previas.

## 5. Migración y verificación integrada

- [x] 5.1 Inspeccionar historial Alembic del entorno de destino; no editar la migración 006 ni reutilizar su revision ID. Respetar el chain actual 005→006 al desplegar, manteniendo independencia funcional de C-06 (R6).
- [x] 5.2 Si los horarios semanales u otro gap exigen esquema, crear una migración forward nueva, aditiva y reversible sobre el head real; verificar uniqueness del revision ID, downgrade/upgrade y que no recrea ni altera retroactivamente tablas existentes.
- [x] 5.3 Ejecutar suite backend agenda, pruebas de catálogo/config/disponibilidad y `npm test`, `npm run typecheck` y `npm run build` en frontend; revisar R1–R14, timezone UTC, strict DTOs, RBAC, migraciones y fixtures sintéticos.
- [x] 5.4 Verificar contrato de disponibilidad consumible por C-07/C-08 —horarios semanales del profesional en timezone del tenant, bloqueos, candidatos cada 30 min, duración completa, UTC y mínimos globales— sin implementar agenda completa ni reserva pública en C-06.
