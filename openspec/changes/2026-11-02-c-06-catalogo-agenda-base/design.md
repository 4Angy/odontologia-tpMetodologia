# Design

## Context

Ver `proposal.md` y `specs/agenda/catalogo-base/spec.md`. El backend ya tiene modelos, schemas estrictos, repositorios y CRUD HTTP de profesionales, prestaciones, bloqueos y configuración; la revisión `006_catalogo_agenda_base.py` crea las tablas y columnas de configuración, y contiene `downgrade`. Hay tests básicos de alta/lista de catálogo y configuración.

Gaps observados:
- La página de configuración y las páginas de agenda son placeholders; no hay pantallas de catálogo en React.
- Los routers escriben directamente modelos y no se encontró auditoría actor/acción (AuditMixin solo mantiene timestamps).
- Alta/edición de bloqueos comprueba que fin sea posterior al inicio, pero no verifica que el profesional exista en el mismo tenant ni que datetimes sean aware antes de persistir.
- La revisión 006 crea modelos/tablas, pero no inserta catálogo de prestaciones; `seed_demo` actual crea tenant, usuarios, config básica y turnos, no profesionales/prestaciones/bloqueos.
- No existe cálculo compartido de disponibilidad que combine duración, bloqueos, antelación y turnos.
- No existe configuración de horarios semanales por profesional; los bloqueos existentes no los sustituyen y deben actuar como excepciones.
- `ConfigRepository` y los schemas usan `antelacion_cancel_hs`; KB confirma que ese es el nombre ejecutable, aunque CHANGES.md lo denomine conceptualmente `antelacion_hs`.
- La independencia funcional está declarada en CHANGES.md, pero Alembic 006 tiene `down_revision = 005_ficha_clinica_presupuestos`.

## Goals / Non-Goals

**Goals:**
- Validar y cerrar gaps del catálogo/configuración existente, incluyendo UI, tenancy relacional, intervalos y servicio de disponibilidad reutilizable.
- Mantener independencia funcional de C-04/C-05 y dependencia funcional de C-03.
- Preservar el esquema existente y establecer una secuencia segura de aplicación de migraciones.

**Non-Goals:**
- CRUD de turnos, agenda día/semana, reserva pública, notificaciones o lista de espera: C-07/C-08/C-09/C-10.
- Implementar CRUD de turnos, feriados, reserva pública o política de múltiples sillones.
- Rehacer o renumerar revisiones Alembic existentes en esta etapa de planificación.

## Decisions

1. **Extender el slice, no reescribirlo.** Se conservan modelos, routers, DTOs y migración 006 donde ya satisfacen el contrato. Antes de cambiar, se agregan pruebas de caracterización; el trabajo backend se limita a huecos confirmados: validación tenant de referencias, datetime aware, restricciones temporales, auditoría y disponibilidad. CRUD de catálogo existente se valida por método/rol y no se vuelve a crear.

2. **Derivar tenant exclusivamente de JWT y validar relaciones en el mismo tenant.** Toda lectura/mutación usa el contexto autenticado. `Bloqueo.profesional_id` debe resolverse tenant-scoped antes de guardar; un ID recibido del cliente no prueba pertenencia. Profesional `usuario_id` puede ser nulo por modelo y no se impone FK/login por inferencia. Las respuestas siguen DTOs estrictos sin modelos ORM.

3. **Mantener nombres/valores reales del contrato.** Usar `antelacion_cancel_hs` como columna ejecutable existente; no crear `antelacion_hs` duplicada. Valores monetarios `precio_ref` se manejan como centavos enteros. Duraciones/defaults deben validarse contra constraints actuales sin ampliar rangos de producto por supuesto.

4. **Horarios locales, instantes UTC.** Los horarios semanales de cada profesional se interpretan en la zona horaria del tenant; los bloqueos son excepciones. Todo instante persistido se normaliza a UTC y las fronteras HTTP exigen datetime aware. En todos los intervalos `fin > inicio`; no se almacenan timestamps naive. La zona de tenant no se fija a `America/Argentina/Buenos_Aires` si la configuración real declara otra.

5. **Separar catálogo de disponibilidad reutilizable.** El servicio de huecos acepta tenant, profesional, prestación y ventana temporal; genera inicios cada 30 minutos, requiere que la duración completa quepa en el horario semanal, descuenta bloqueos y aplica la antelación global de reserva. Cuando el dominio de turnos esté disponible, excluye turnos activos. Es una capability compartida consumida por C-07/C-08, no un duplicado de sus endpoints.

6. **Reglas globales de antelación cerradas.** La cancelación tiene un único valor global por tenant, default 24 horas, sin override por prestación. La reserva tiene un mínimo global por tenant de 2 horas, configurable por el dueño. Se calculan candidatos con inicios cada 30 minutos. El timeout de pago no forma parte de C-06. Los días/intervalos semanales se configuran por profesional en la zona del tenant; no se presuponen horas laborables concretas.

7. **Auditar mutaciones según RN-GL-02.** `created_at`/`updated_at` no bastan. Reusar una bitácora común aprobada o acordar el contrato mínimo (tenant, actor, recurso, acción, instante UTC y cambio permitido); escribirla de forma atómica con catálogo/config. No registrar datos clínicos en auditoría. La consulta de auditoría sigue restringida al dueño según matriz de actores.

8. **Seed solo para demo y repetible.** Extender el seed sintético con prestaciones del KB (limpieza, consulta, arreglo y conducto, con duraciones editables) si el seed de demostración es el destino acordado; hacerlo idempotente y sin duplicados al reejecutar. No sembrar datos operativos para tenants reales sin una decisión explícita.

9. **Independencia funcional y migración sin reescritura.** C-06 sigue independiente de C-04/C-05 y puede desarrollarse y probarse en paralelo. Se conserva `006_catalogo_agenda_base` sin editarla; si los horarios semanales requieren esquema, se añade una migración forward única y reversible sobre el head Alembic real. La relación de despliegue 005→006 existente se documenta como constraint técnico del chain, no como dependencia funcional.

10. **UI en React/TypeScript estricto.** Reemplazar placeholder de configuración por vistas de profesionales, prestaciones, bloqueos y opciones de agenda, con validación y RBAC coherentes con roles acumulables. Mantener tipos explícitos, componentes PascalCase, estados de carga/error y pruebas Vitest. No inferir APIs de agenda aún no disponibles.

11. **TDD y reglas R1–R14.**
   - R1–R2: consultas de negocio filtradas por tenant; el frontend no define tenant.
   - R3–R4: DTOs Pydantic v2, no ORM en API, `extra='forbid'`.
   - R5–R7: centavos enteros; Alembic reversible; timestamps aware/UTC.
   - R8–R9: webhooks futuros idempotentes; errores de negocio con `code` RN.
   - R10: TS estricto, sin `any` explícito, componentes PascalCase.
   - R11: test rojo antes del código, al menos dos casos por comportamiento.
   - R12: no commit/push sin pedido explícito.
   - R13: si una integración con paciente/cobro aparece, detener y reevaluar gobernanza HIGH/CRITICAL antes de escribir.
   - R14: fixtures y seeds solo sintéticos/demo, sin datos reales sensibles.

## Risks / Trade-offs

- [Referencia cross-tenant] El bloqueo actual puede guardar un profesional inexistente o ajeno → lookup tenant-scoped con tests de no fuga.
- [Datetimes naive] El driver podría fallar tarde o interpretarlos distinto → validar en la frontera HTTP y cubrir formatos con timezone ausente/UTC/desplazamiento.
- [Disponibilidad de horario] Los horarios semanales deben configurarse por profesional en zona del tenant y los bloqueos prevalecen como excepciones → probar duración completa y conversión UTC sin asumir jornadas estándar.
- [Migración de C-06 secuenciada] El chain existente exige 005 antes de 006 → mantener C-06 funcionalmente independiente y respetar el orden de despliegue actual; cambios para horarios van en migración forward, nunca editando 006.
- [Auditoría inexistente] La escritura directa a ORM no identifica actor/cambio → adoptar bitácora común transaccional antes de dar el change por terminado.
- [Datos de agenda] Horarios pueden revelar actividad clínica aunque este módulo no contenga HCE → acceso tenant-scoped, RBAC y no usar datos reales en pruebas.

## Migration Plan

1. Implementar los valores ya acordados (cancelación global 24 h, reserva global 2 h, horarios semanales por profesional, bloqueos excepcionales y candidatos cada 30 min); resolver solo los detalles de auditoría compartida y destino del seed demo que sigan abiertos.
2. Ejecutar tests rojos de tenancy relacional, validación UTC, RBAC, disponibilidad y auditoría antes de completar código; fixtures sintéticos.
3. Inspeccionar historial Alembic real en el entorno destino. No editar 006 ni recrear tablas; los horarios que requieran esquema se agregan en una nueva revisión forward, única y con `downgrade`.
4. Ensayar migración y rollback estructural en base descartable. El orden de despliegue sigue 005 → 006 según chain actual; el trabajo funcional de C-06 puede avanzar en paralelo.
5. Probar seed repetible y UI contra API tenant-scoped antes de habilitar para uso.

## Open Questions

- ¿El seed de catálogo se aplica solo al tenant demo o también al onboarding de nuevos tenants?
- ¿Qué política de color de agenda y validación de color debe aceptar el UI?
- ¿Qué mecanismo común de auditoría y consulta del dueño estará disponible para C-04/C-05/C-06?
- ¿Se mantiene la cadena lineal Alembic 005→006 para despliegues paralelos, o se necesita un grafo de ramas/merge antes de una futura reorganización?
