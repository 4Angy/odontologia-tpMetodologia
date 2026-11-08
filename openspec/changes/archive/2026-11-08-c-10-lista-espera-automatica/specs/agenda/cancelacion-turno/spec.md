# Spec Delta

## ADDED Requirements

### Requirement: Cancelación en término dispara oferta de lista de espera

El sistema SHALL, al completarse una cancelación en término de un turno, disparar la oferta automática de lista de espera para el primer hueco compatible, reutilizando las reglas de elegibilidad, TTL y envío de `agenda/lista-espera`. Si no existe entrada compatible, el hueco queda libre sin efectos adicionales. La oferta MUST ejecutarse dentro de la misma transacción de cancelación (Opción A).

#### Scenario: Cancelación con entrada compatible dispara oferta

- **WHEN** un turno se cancela en término y existe al menos una entrada `activa` compatible en la lista de espera del tenant
- **THEN** la primera entrada compatible pasa a `ofrecida` con `expires_at` y se encola el WhatsApp, dentro de la misma transacción de cancelación

#### Scenario: Cancelación sin entrada compatible no dispara oferta

- **WHEN** un turno se cancela en término y no existe entrada `activa` compatible
- **THEN** la cancelación se completa normalmente y el hueco queda libre sin cambios en la lista de espera
