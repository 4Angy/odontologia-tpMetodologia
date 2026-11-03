# Design — C-07 `turnos-agenda-interna`

## Context

C-07 completa la agenda interna sobre los componentes que ya existen: `turno` y `config` (migración inicial `0001_cancelacion_turno`), autenticación/RBAC y el catálogo de profesionales, prestaciones y bloqueos de C-06 (revisión Alembic `006_catalogo_agenda_base`). La cancelación ya tiene un slice y un contrato de error `RN-AG-01`; C-07 lo integra, no lo reemplaza. Ver `CHANGES.md` para el alcance y las dependencias.

**Decisión de arquitectura elegida por el usuario — Opción A:** reglas de negocio y anti-solapamiento en servicios de dominio testeables; routers FastAPI delgados; repositorios SQLAlchemy siempre filtrados por `tenant_id`; cambios de esquema mediante Alembic reversible. El diseño mantiene los límites entre dominio, persistencia y HTTP: los routers validan DTOs y traducen errores, pero no deciden reglas de agenda.

## Goals / Non-Goals

**Goals:**
- CRUD interno de turnos y acciones explícitas `confirmar`, `cancelar`, `reprogramar`, `presente` y `ausente`, con transiciones validadas por dominio.
- Agenda interna de día y semana, multi-profesional, y las vistas/acciones de gestión diaria incluidas en el roadmap.
- Evitar colisiones por profesional conforme a RN-AG-03; devolver `409` con hasta tres horarios alternativos cuando corresponda.
- Permitir sobreturno solo como excepción explícita, con flag, motivo y permiso de agenda (RN-AG-04).
- Aplicar RBAC y aislamiento tenant-scoped en todas las operaciones; errores de negocio trazables con `code` RN-XX y mensajes en español-AR.
- Integrar la cancelación configurable de RN-AG-01/02 y respetar el contrato ya definido para el error fuera de término.
- Incorporar idempotencia en la creación de turnos y pruebas unitarias, de integración y de concurrencia.
- Extender el esquema existente con una migración Alembic reversible, sin recrear tablas de C-01/C-06.

**Non-Goals:**
- Reserva pública, acciones de pacientes por token y rate limiting: C-08.
- Cobro, devolución o movimiento efectivo de señas: C-12. C-07 conserva la seña y deja preparado el flujo de reprogramación para que C-12 aplique RN-AG-05.
- Envío de notificaciones y automatizaciones de lista de espera: C-09/C-10.
- Rehacer el catálogo de agenda de C-06 o introducir RLS de Postgres.

## Decisions

1. **Servicios de dominio como autoridad de las reglas; routers como adaptadores HTTP.** Los servicios reciben el contexto tenant/user y operaciones de repositorio, validan transiciones, permisos, antelación y solapamientos, y devuelven resultados/errores de dominio. FastAPI limita su responsabilidad a autorización de entrada, DTOs estrictos, invocación del servicio y mapeo de errores a HTTP. No se expone el ORM como respuesta.
   - Rationale: permite probar reglas sin FastAPI ni base de datos y evita duplicarlas entre CRUD, acciones y agenda.
   - Alternativa descartada: lógica de negocio en routers/endpoints; acopla reglas y HTTP y deja caminos alternativos para eludirlas.

2. **Repositorios SQLAlchemy tenant-scoped y transacciones en operaciones mutables.** Cada lectura y escritura de negocio incluye `tenant_id` derivado de la identidad autenticada; una entidad de otro tenant no se devuelve ni se muta. Las acciones de estado y la comprobación de colisión se ejecutan dentro de una operación transaccional.
   - Rationale: conserva RN-AU-01 y las convenciones del repositorio. Los índices tenant/profesional/tiempo ayudan a consultas, pero por sí solos no garantizan la exclusión de intervalos concurrentes.
   - **Decisión confirmada por el usuario:** bloquear la fila del profesional con `SELECT FOR UPDATE` dentro de la transacción antes de comprobar disponibilidad y persistir la operación. Las operaciones que involucren varios profesionales toman los locks en orden estable. El bloqueo serializa tanto reservas ordinarias como sobreturnos explícitos; el segundo solicitante vuelve a validar el horario después de adquirirlo.

3. **Solapamiento como invariante de dominio con intervalos semiabiertos.** Para el mismo profesional, dos intervalos activos se solapan si sus rangos temporales semiabiertos se intersectan. Cancelados y turnos reemplazados no ocupan el horario. Una colisión ordinaria se rechaza con `409` y tres propuestas que también respeten los bloqueos y la duración configurada por prestación.
   - Las propuestas salen de la disponibilidad ya definida por C-06, ordenadas por distancia temporal absoluta al horario pedido; en empate se prioriza el horario anterior. El servicio devuelve datos, no decide su presentación.
   - **Decisión confirmada por el usuario:** usar este orden para las tres alternativas.

4. **Sobreturno explícito, nunca bypass silencioso.** El flujo ordinario rechaza el solapamiento. Solo la acción de sobreturno puede aceptarlo y requiere `sobreturno=true`, motivo no vacío, permiso de escritura de agenda y registro auditable de quién autorizó la excepción (RN-AG-04). El permiso se verifica en dominio además de la autorización HTTP.
   - RBAC respeta `03_actores_y_roles.md`: `recepcion` y `dueno` gestionan la agenda; `odontologo` consulta sus propios turnos/bloqueos. Se conserva la excepción ya implementada por el contrato de cancelación para que odontología cancele sus propios turnos; no habilita confirmar, reprogramar, marcar asistencia ni autorizar sobreturnos. La unión de roles aplica (RN-AU-04).

5. **Cancelación reutiliza la regla y el contrato existentes.** Se lee `config.antelacion_cancel_hs` por tenant (default 24 horas; cero permitido), se compara en UTC con datetimes timezone-aware y el límite es inclusivo. Si la antelación es menor, se mantiene `409`, `code: RN-AG-01` y la oferta de reprogramar; no se muta el turno. Solo `dueno` cambia la configuración, y los cambios no son retroactivos (RN-AG-02). Se conserva la cancelación lógica y su idempotencia por estado/auditoría, como define el slice previo.
   - Reprogramar realiza la transición del turno anterior y crea/asocia el nuevo turno dentro de C-07; el movimiento de la seña acreditada queda a cargo de C-12 (RN-AG-05), sin cobro duplicado en este change.

6. **Acciones de estado explícitas, no actualización libre del estado por CRUD.** Las acciones invocan la máquina de estados del dominio; el CRUD no permite saltarse sus validaciones mediante un `PATCH` genérico. Estados del modelo según roadmap: `pendiente_confirmacion`, `confirmado`, `presente`, `ausente`, `cancelado` y `reprogramado`.
   - Los turnos creados internamente nacen `confirmado`; la reserva pública de C-08 nace `pendiente_confirmacion`. `confirmar` permite únicamente `pendiente_confirmacion → confirmado`; cancelar y reprogramar aceptan solo estados activos conforme al contrato de cancelación; reprogramar marca el anterior `reprogramado` y crea el nuevo como `confirmado`.
   - `presente` se permite desde `confirmado`; `ausente` se permite desde `confirmado` al alcanzar su hora de fin. Ambos los ejecutan `recepcion` o `dueno`, de acuerdo con la matriz RBAC vigente. `presente`, `ausente`, `cancelado` y `reprogramado` son terminales. Las transiciones no permitidas devuelven un error trazable y no generan efectos parciales.
   - **Decisión confirmada por el usuario:** conservar la matriz RBAC actual, permitir marcar ausente desde el fin programado y aceptar las condiciones descritas.

7. **Idempotencia de creación y migración aditiva.** La creación acepta una clave de idempotencia para que un reintento/doble clic no cree otro turno; su almacenamiento y alcance serán por tenant. La migración extiende `turno` con los campos que falten para C-07 (`token_publico` único, `origen`, `senia_id` nullable y datos de sobreturno/auditoría necesarios), agrega índices para consultas tenant/profesional/tiempo y tiene `downgrade`.
   - No se recrean `turno`, `config` ni los objetos de C-06. `token_publico` pertenece al modelo extendido de turno de C-07; C-08 añadirá únicamente lo que requiera para expiración/reserva pública.
   - La clave se conserva asociada al turno sin vencimiento, única dentro del tenant. La misma clave con el mismo contenido devuelve el resultado original; contenido distinto produce `409` con `code: RN-AG-03` y no crea otro turno.
   - **Decisión confirmada por el usuario:** retención sin vencimiento mientras exista el turno.
   - La cadena actual termina en `008_horarios_profesional`; C-07 usa la revisión `009`, y las migraciones posteriores siguen con identificadores únicos en secuencia.

8. **Pruebas por capas.** Servicios de dominio se prueban sin HTTP/DB para reglas y transiciones; repositorios/API verifican persistencia, tenant isolation, RBAC y contratos; pruebas de integración ejercitan la protección ante reservas concurrentes y la migración reversible.

9. **La disponibilidad interna es una sugerencia, no una restricción de alta manual.** La UI muestra candidatos al crear y reprogramar cuando hay profesional y prestación seleccionados, pero permite ingresar otro horario manualmente. El backend sigue validando intervalo, duración, referencias tenant-scoped y colisiones; el sobreturno explícito solo permite la colisión y no omite esas validaciones.
   - Rationale: conservar la flexibilidad operativa de recepción para excepciones de agenda, sin ocultar los horarios calculados por C-06.
   - **Decisión confirmada por el usuario:** disponibilidad sugerida, sin forzar selección de un candidato.

## Risks / Trade-offs

- [Carrera de reservas] Dos transacciones podrían validar el mismo horario antes de insertar → resolver el mecanismo transaccional/DB pendiente y probar reservas concurrentes, también frente a un sobreturno permitido.
- [Contención por profesional] El lock serializa escrituras del mismo profesional, incluso en horarios distintos → priorizar integridad frente a paralelismo; medir si la contención se vuelve relevante.
- [Fecha/zona horaria] Comparaciones de antelación o agenda pueden variar en los bordes → persistencia y reglas en UTC aware (R7), presentación en `America/Argentina/Buenos_Aires`, con pruebas de límite.

## Migration Plan

1. La cadena Alembic comprobada termina en `008_horarios_profesional`; registrar C-07 como `009_turnos_agenda_interna` y actualizar la secuencia futura en CHANGES.
2. Aplicar una migración aditiva y reversible sobre `turno`, creando solo columnas e índices ausentes; no eliminar ni reescribir datos de turnos existentes.
3. Desplegar backend con las acciones y servicios antes de habilitar la UI de agenda. Verificar el `downgrade` en entorno de prueba y que el rollback no borre datos previos.

## Verification Scope

- CRUD, agenda día/semana multi-profesional y filtros por tenant.
- Solape ordinario rechazado; tres alternativas válidas; intervalos contiguos no colisionan; bloqueos y duración de prestación respetados.
- Sobreturno sin flag/motivo o sin permiso rechazado; excepción autorizada queda auditada.
- Matriz RBAC, acceso del odontólogo a sus turnos, unión de roles y aislamiento entre tenants.
- Cancelación en el límite configurado y antes del límite (`RN-AG-01`), turno ya cancelado idempotente y reprogramación sin mutación parcial.
- Acciones confirmar/reprogramar/presente/ausente y transiciones inválidas.
- Idempotencia de creación, carrera de dos reservas y migración/downgrade.

## Open Questions

- No quedan decisiones de producto abiertas para implementar C-07; los defaults de concurrencia, alternativas, estados e idempotencia fueron confirmados por el usuario.
