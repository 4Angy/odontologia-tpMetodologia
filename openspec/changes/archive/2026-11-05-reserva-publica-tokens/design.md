# Design

## Context

C-07 ya provee turnos, disponibilidad, estados, colisiones y reglas de
cancelación. C-04 provee pacientes y opt-in; el rate limiter actual es
in-memory y reemplazable. `turno.token_publico` existe por compatibilidad con
C-07, pero C-08 adopta una entidad separada para que los tokens públicos
puedan revocarse, expirar y auditarse sin convertir el turno en almacén de
credenciales. La cadena Alembic vigente ya contiene `010_c05_contrato_clinico`. Este change
usa `011_reserva_publica_tokens`, validada con un ciclo PostgreSQL
`upgrade head` → `downgrade 010_c05_contrato_clinico` → `upgrade head`.

## Goals / Non-Goals

**Goals:**

- Ofrecer reserva y acciones públicas tenant-scoped sin JWT.
- Reutilizar la disponibilidad y la máquina de estados de agenda sin duplicar reglas.
- Almacenar tokens como representaciones no reversibles y permitir revocación individual.
- Hacer idempotentes las reservas y seguros los reintentos concurrentes.
- Entregar un contrato estable para que C-12 conecte checkout y webhooks de señas.

**Non-Goals:**

- Procesar pagos, validar webhooks de Mercado Pago o aplicar devoluciones; pertenece a C-12.
- Enviar WhatsApp, ejecutar recordatorios o implementar el worker; pertenece a C-09.
- Construir lista de espera; pertenece a C-10.
- Crear una cuenta autenticada para el paciente.
- Reemplazar los contratos internos de C-06/C-07.

## Decisions

1. **Entidad separada para tokens públicos.** Cada token se genera con
   aleatoriedad criptográfica, se entrega una sola vez como valor opaco y se
   persiste mediante hash con propósito, `expires_at`, `revoked_at` y
   `revocation_reason`. Se elige sobre ampliar `turno` porque permite
   revocación y rotación sin mezclar credenciales con el agregado de agenda.

2. **Token por propósito y operación.** Confirmar, cancelar y reprogramar
   usan propósitos diferenciados. El servicio valida tenant, turno, propósito,
   expiración y revocación antes de delegar la transición a C-07. Se evita un
   token universal para limitar el impacto de una filtración.

3. **Reserva pública como adaptador del dominio de agenda.** Las rutas
   públicas validan DTOs estrictos y delegan disponibilidad, colisiones,
   transiciones y cancelación al servicio existente. No se replica una segunda
   regla de solapamiento. Las operaciones que crean o reprograman bloquean el
   profesional y vuelven a comprobar disponibilidad dentro de la transacción.

4. **Identidad pública mínima.** Se busca un paciente existente por
   identificadores permitidos del tenant; si no existe, se crea con los datos
   mínimos necesarios. El endpoint nunca permite elegir `tenant_id` ni acceder
   a pacientes ajenos. El cambio de teléfono debe revocar tokens pendientes
   asociados al número anterior, siguiendo C-04.

5. **Idempotencia con resultado estable.** La clave de idempotencia se
   almacena con tenant y huella del payload normalizado. Una repetición
   equivalente devuelve la reserva original; una huella distinta devuelve
   conflicto. La creación del paciente y del turno comparte la transacción.

6. **Protección anti-abuso por capas.** Se reutiliza la interfaz de rate
   limiting existente y se definen límites separados para disponibilidad,
   creación y acciones de token. El primer despliegue usa el backend
   in-memory ya presente; la interfaz permite migrar a Redis sin cambiar el
   contrato HTTP. No se incorpora un proveedor CAPTCHA nuevo en este change:
   el rate limit, los tokens opacos y el timeout de pendientes son el baseline,
   y un desafío adicional queda como endurecimiento posterior si las métricas
   lo justifican.

7. **Timeout de pago configurable.** La reserva con seña pendiente usa un
   timeout de 30 minutos como default documentado, configurable por tenant.
   Un job posterior libera el slot y revoca tokens; C-12 es responsable de
   emitir el evento de acreditación idempotente que puede confirmar la reserva.

8. **Migración aditiva y reversible.** Se agrega la tabla de tokens, los
   índices tenant/turno/hash/expiración y la persistencia mínima de
   idempotencia o se reutiliza el mecanismo existente cuando sea compatible.
   La migración no recrea `turno`, no elimina `token_publico` de C-07 y debe
   incluir downgrade probado. El identificador final se resolverá contra la
   cadena vigente antes de codificar la migración.

## Risks / Trade-offs

- **[Abuso de reservas que bloquean horarios]** -> rate limits separados,
  expiración de pendientes, idempotencia, auditoría y métricas de rechazos.
- **[Filtración de token en URL o logs]** -> token opaco de un solo propósito,
  hash persistido, redacción en logs y revocación.
- **[Divergencia entre agenda pública e interna]** -> un único servicio de
  disponibilidad/estado y revalidación transaccional antes de mutar.
- **[Rate limiting in-memory no escala entre réplicas]** -> mantener la
  interfaz `RateLimiter` y planificar implementación Redis antes de escalar.
- **[Identificación incorrecta de pacientes]** -> matching tenant-scoped,
  datos mínimos, no exponer coincidencias y permitir intervención posterior
  de recepción.
- **[Dependencia de C-12]** -> contrato explícito de checkout pendiente y
  evento de acreditación idempotente; C-08 no marca pago como acreditado.

## Migration Plan

1. Crear `011_reserva_publica_tokens` posterior a la revisión vigente para
   tokens públicos, índices, expiración y configuración del timeout, con
   `downgrade`.
2. Desplegar el backend que crea tokens separados y mantiene lectura
   compatible del campo heredado de C-07 durante la transición.
3. Habilitar la página pública y las rutas de reserva con rate limits.
4. Ejecutar pruebas de migración, aislamiento, concurrencia, expiración y
   contratos de checkout.
5. Tras verificar que no quedan consumidores del token heredado, dejarlo
   únicamente como compatibilidad de C-07; su eliminación queda fuera de C-08.

Rollback: deshabilitar las rutas públicas, dejar vencer/revocar tokens
emitidos y ejecutar el downgrade solo si no existen datos dependientes; los
turnos internos y sus reservas ya creadas deben conservarse.

## Open Questions

- El texto legal final del consentimiento WhatsApp y la adecuación legal deben
  validarse antes del lanzamiento (PA-07), sin cambiar el contrato técnico.
- La política final de CAPTCHA puede agregarse como endurecimiento si los
  límites iniciales no alcanzan.
