# Design

## Context

C-09 ya provee el motor durable (`notificacion_envio`, plantilla `lista_espera`, worker con tick de 15s) y C-07/C-08 proveen cancelación, tokens públicos opacos y disponibilidad. La cancelación en término libera el hueco observable; C-10 reutiliza esa señal para disparar la oferta dentro de la misma transacción (Opción A acordada en explore). La cadena Alembic vigente termina en `012_notificaciones`, por lo que C-10 usa `013_lista_espera`.

## Goals / Non-Goals

**Goals:**

- Ofertar automáticamente el primer hueco compatible liberado por cancelación, con TTL configurable (default 2h).
- Mantener una cola auditable por tenant con estados `activa|ofrecida|convertida|vencida`.
- Permitir aceptar/declinar por token público y asignar el turno en la misma transacción.
- Saltar entradas sin opt-in con motivo registrado y avanzar al siguiente.
- Vencer ofertas expiradas y avanzar automáticamente vía worker.

**Non-Goals:**

- Score de ausentismo o prioridad compleja en v1: se usa FIFO por `created_at` (PA-06 mitigado con prioridad configurable).
- Cobro/devolución de seña: delegado a C-12; C-10 solo arrastra si corresponde según RN-AG-05.
- Notificaciones por email para lista de espera: el motor lo soporta, pero v1 dispara WhatsApp; email queda como fallback del motor.
- Reemplazar el rate limiter in-memory o migrar a async: pertenece a C-13.

## Decisions

### D1 — Oferta sincrónica en la transacción de cancelación

Al cancelar un turno en término (interno), dentro de la misma transacción se busca la primera entrada `activa` compatible, se marca `ofrecida`, se fija `expires_at` y se encola el WhatsApp. Esto reutiliza el lock por turno ya existente y evita una segunda fuente de verdad.

Alternativa descartada: outbox asíncrono (Opción B), que agrega latencia y una tabla extra sin beneficio frente al lock existente.

### D2 — Modelo `lista_espera` y prioridad

Nueva tabla `lista_espera` con `paciente_id`, `profesional_id` (nullable), `prestacion_id` (nullable), `prioridad` (int, default 0), `estado`, `created_at`, `ofrecido_at`, `expires_at`, `hueco_profesional_id`, `hueco_inicio`, `hueco_fin`, `hueco_prestacion_id` (para reconstruir el hueco ofrecido) y `motivo_omision`. El índice `(tenant_id, estado, prioridad)` y `(tenant_id, estado, expires_at)` para el worker.

La prioridad se resuelve por `prioridad` asc y luego `created_at` asc (FIFO). El TTL vive en `config.lista_espera_ttl_hs` (default 2) para no quemar constantes.

### D3 — Matching de compatibilidad

Una entrada es elegible para un hueco si:
- `entry.profesional_id IS NULL OR entry.profesional_id = hueco.profesional_id`
- `entry.prestacion_id IS NULL OR entry.prestacion_id = hueco.prestacion_id`

No se valida solape con otros turnos del paciente en v1 (fuera de alcance).

### D4 — Omisión por falta de opt-in

Si la primera elegible no tiene opt-in válido, se registra un envío `omitida` con `motivo_code="RN-PA-01"` (sin proveedor) y se evalúa la siguiente. La entrada permanece `activa` para futuros huecos.

### D5 — Vencimiento y avance vía worker

Nuevo job `lista_espera.expiry` en el worker: escanea entradas `ofrecida` con `expires_at <= now`, las marca `vencida` y ofrece el hueco al siguiente `activa` compatible. Un hueco tiene a lo sumo una oferta vigente a la vez.

### D6 — Tokens de aceptación/declinación

Se reutiliza `public_token` de C-08 con nuevos propósitos `waitlist_accept` y `waitlist_decline`, TTL del token alineado al TTL de la oferta. El mensaje incluye dos links: aceptar y declinar. Al aceptar se crea el turno y se revoca el token; al declinar se vence la oferta.

### D7 — Aceptación transaccional

La aceptación ejecuta dentro de una transacción:
1. Valida token (`waitlist_accept`, no revocado, no expirado).
2. Lock del profesional del hueco.
3. Verifica que el hueco siga libre (`list_solapados`).
4. Crea el turno `confirmado` (o `pendiente_confirmacion` si aplica seña).
5. Transiciona la entrada a `convertida`.
6. Revoca el token.

Si el hueco fue tomado, la entrada vuelve a `activa` y se responde error trazable.

### D8 — Seña

La creación del turno por aceptación deja `senia_id` nullable. El arrastre real de seña (RN-AG-05) se delega a C-12; C-10 solo reserva el punto de extensión (`origen="lista_espera"`).

### D9 — Oferta manual

Endpoint `POST /lista-espera/{id}/ofrecer` (recepción/dueno) que recibe `hueco` (profesional, inicio, fin, prestacion) y reutiliza la misma lógica de matching/TTL/envío que la automática.

### D10 — Migración `013_lista_espera`

Tabla `lista_espera` + índices, `config.lista_espera_ttl_hs` (default 2, check >= 0). `downgrade` elimina en orden inverso y debe probarse `upgrade head → downgrade 012 → upgrade head`.

## Risks / Trade-offs

- **[Concurrencia en cancelación]** → el lock por turno y la transacción evitan doble oferta; si dos cancelaciones liberan huecos distintos, cada una ofrece de forma independiente.
- **[Spam en bucle]** → un `ofrecida` por hueco a la vez + auditoría de transiciones + TTL.
- **[Hueco tomado entre oferta y aceptación]** → D7 verifica disponibilidad y revierte la entrada a `activa`.
- **[TTL y FIFO sin validar (PA-06)]** → TTL y prioridad configurables por tenant; FIFO por defecto, extensible a score sin cambio de contrato.
- **[Token en URL de WhatsApp]** → token opaco de un solo propósito, hash persistido, revocación por cambio de teléfono (C-04/C-08).

## Migration Plan

1. Crear `013_lista_espera` posterior a `012_notificaciones`: tabla, índices, `config.lista_espera_ttl_hs`, con `downgrade`.
2. Desplegar backend con endpoints y worker job; plantilla `lista_espera` ya existe (C-09).
3. Ejecutar pruebas de migración `upgrade head → downgrade 012 → upgrade head` contra PostgreSQL 16.
4. Rollback: apagar el job de vencimiento, dejar que las ofertas expiren sin procesarse y ejecutar downgrade solo si no hay filas dependientes.

## Open Questions

- Texto legal final del opt-in y mensajes (PA-07) sigue pendiente; el motor no cambia si el texto cambia.
- Si se requiere score de ausentismo para prioridad, se agrega sin romper el contrato (D2).
