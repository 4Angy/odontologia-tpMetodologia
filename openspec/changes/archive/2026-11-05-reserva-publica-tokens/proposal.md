# Proposal

## Why

Los pacientes necesitan reservar fuera del horario del consultorio sin crear una cuenta, mientras que el consultorio debe proteger la disponibilidad real y evitar que enlaces públicos permitan acciones indefinidas o abusivas. C-07 ya aporta turnos, disponibilidad y `token_publico`, por lo que C-08 debe completar la superficie pública con tokens revocables/expirables, rate limiting y una experiencia de reserva coherente con la agenda interna.

## What Changes

- Agregar una página pública por tenant en `/r/:tenantSlug` que consulte catálogo y disponibilidad real.
- Permitir crear reservas públicas idempotentes, tenant-scoped y con datos mínimos del paciente, respetando duración, bloqueos, solapamientos y antelación configurada.
- Crear una entidad separada de token público vinculada al turno, almacenando únicamente el hash, propósito, expiración, revocación y auditoría mínima.
- Exponer acciones sin login para confirmar, cancelar y reprogramar un turno mediante token válido.
- Hacer que toda reserva pública nazca `pendiente_confirmacion`; dejar preparada la respuesta de checkout cuando la prestación requiera seña, sin procesar el pago en este change.
- Aplicar opt-in explícito y teléfono E.164 válido cuando se solicite WhatsApp.
- Aplicar rate limiting y protección anti-abuso en las rutas públicas; liberar reservas pendientes de pago después del timeout configurable.
- Incorporar pruebas de aislamiento, expiración/revocación, idempotencia, disponibilidad, colisiones y límites de abuso.

## Capabilities

### New Capabilities

- `agenda/reserva-publica`: Reserva pública por tenant, tokens de acciones sin login, disponibilidad, protección anti-abuso y ciclo de vida de reservas públicas.

### Modified Capabilities

<!-- C-07 ya expone los contratos de agenda y disponibilidad requeridos; este change los consume sin modificar sus requisitos. -->

## Impact

- Backend: nuevo módulo de reserva pública dentro de agenda, DTOs estrictos, servicios de dominio, repositorios tenant-scoped y rutas sin JWT.
- Persistencia: nueva migración Alembic reversible posterior a la revisión vigente; la numeración deberá coordinarse porque `010_c05_contrato_clinico` ya existe.
- Frontend: página pública fuera del shell autenticado, selección de prestación/profesional/horario y acciones mediante enlace.
- Seguridad: rate limiter existente, tokens opacos almacenados como hash, expiración, revocación por cambio de teléfono y no exposición de datos entre tenants.
- Dependencias: C-07 para agenda/disponibilidad/turnos y C-04 para pacientes y opt-in; C-12 consumirá el contrato de checkout y webhook de seña.
