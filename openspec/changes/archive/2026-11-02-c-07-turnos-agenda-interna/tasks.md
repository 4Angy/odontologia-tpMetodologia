# Tasks

## 1. Persistencia y esquema

- [x] 1.1 Agregar pruebas primero para los campos e índices nuevos de `turno`; verificar que el esquema existente y sus datos se preserven.
- [x] 1.2 Implementar la migración Alembic `009_turnos_agenda_interna` con claves tenant-scoped, datos de sobreturno e índices faltantes; verificar upgrade y downgrade en una base de prueba.
- [x] 1.3 Ajustar el modelo ORM del turno sin exponerlo por la API; verificar campos, índices únicos y rechazo de datetimes naive con pruebas unitarias.

## 2. Repositorios y reglas de dominio

- [x] 2.1 Escribir pruebas para aislamiento tenant-scoped y referencias ajenas; implementar consultas tenant-scoped de agenda/idempotencia y verificar rechazo sin fuga en los tests de repositorio.
- [x] 2.2 Escribir pruebas de concurrencia para dos reservas del mismo profesional; serializar mutaciones con `SELECT FOR UPDATE` sobre el profesional y verificar que como máximo una reserva ordinaria se confirme.
- [x] 2.3 Escribir pruebas para creación idempotente, reintento equivalente y clave reutilizada con payload distinto; implementar persistencia por tenant sin vencimiento y verificar que no se duplique ni altere un turno.
- [x] 2.4 Escribir pruebas para solapes semiabiertos, duración, bloqueos y tres alternativas ordenadas por cercanía; implementar validación de dominio usando disponibilidad C-06 y verificar cada caso.
- [x] 2.5 Escribir pruebas de transiciones confirmar/cancelar/reprogramar/presente/ausente, roles y límites horarios; implementar el servicio de dominio y verificar estados terminales, auditoría y ausencia de efectos parciales.
- [x] 2.6 Escribir pruebas para sobreturno explícito, motivo obligatorio y actor autorizante; implementar la excepción auditable y verificar que solicitudes incompletas o sin permiso no creen turnos.

## 3. API y contratos

- [x] 3.1 Escribir pruebas API para CRUD de turnos, agenda día/semana y filtros por profesional; implementar endpoints tenant-scoped con DTOs estrictos y verificar respuestas ordenadas por inicio.
- [x] 3.2 Escribir pruebas API para acciones explícitas, error `RN-AG-01`, errores de dominio y autorización; conectar los endpoints al servicio sin actualizar estados libremente y verificar códigos HTTP y RN.
- [x] 3.3 Escribir pruebas de integración para cancelación seguida de reprogramación y para sobreturno; verificar que la seña no se mueva en C-07 y que el horario liberado vuelva a estar disponible.

## 4. Agenda frontend

- [x] 4.1 Escribir pruebas del cliente API y sus tipos para turnos, agenda y acciones; implementar el cliente y verificar serialización de fechas con offset y manejo de errores.
- [x] 4.2 Escribir pruebas de componentes para vistas día/semana, filtros y creación de turnos; implementar la agenda multi-profesional y verificar accesibilidad a operaciones según RBAC.
- [x] 4.3 Escribir pruebas de interfaz para conflicto, alternativas, sobreturno, cancelación/reprogramación y asistencia; implementar los flujos y verificar mensajes visibles en español-AR sin estado optimista ante errores.

## 5. Integración y documentación

- [x] 5.1 Actualizar la especificación principal de `agenda/turnos-internos` y la de `agenda/cancelacion-turno` con los deltas archivables; verificar que coincidan con el comportamiento implementado.
- [x] 5.2 Ejecutar validación de OpenSpec, pruebas backend y frontend, build TypeScript y `git diff --check`; resolver fallos introducidos por C-07 y registrar resultados.
  - Resultado: OpenSpec válido; 29 pruebas de C-07 pasaron en PostgreSQL 18; 85 pruebas de agenda pasaron en SQLite (la concurrencia también se validó aparte en PostgreSQL); 44 pruebas frontend, build TypeScript/Vite y `git diff --check` pasaron. La suite amplia de agenda en PostgreSQL tuvo 9 fallos en fixtures de C-06/cancelación que no crean su tenant.

## Workflow follow-up

- Archivar C-07 y verificar el change archivado luego de completar y validar todas las tareas.
