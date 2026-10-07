# Preguntas Abiertas

## Inconsistencias detectadas

### IN-01 — "Facturación" significa dos cosas distintas
**Documento A dice**: discovery §3/§5 habla de "registrar cobros, saldos y deudas" y "caja manual, sin AFIP en v1".
**Documento B dice**: el usuario y el análisis usan "facturación"/"cobros" en sentido amplio (DrApp/Benty sí facturan AR; Dentatools declara no hacerlo).
**Impacto**: si un stakeholder espera comprobantes, v1 defrauda aunque cumpla la spec.
**Resolución propuesta**: mantener RN-CO-01 (caja manual, declarado en UI) y validar SU-03 en entrevistas; no ampliar v1 sin evidencia.

### IN-02 — Seña por MP: ¿"cobro online" fuera de v1 o dentro?
**Documento A dice**: discovery §8 deja "cobro online (Mercado Pago o similar)" explícitamente fuera de v1.
**Documento B dice**: el análisis competitivo (C.4-2, D.3) y este KB ponen "seña por Mercado Pago" como diferenciador v1.
**Impacto**: ambigüedad de alcance que puede expandir v1 a un checkout completo.
**Resolución propuesta**: seña acotada SÍ en v1 (preferencia + webhook + arrastre, sin checkout completo ni pagos online generales); registrar como decisión DD-05 y confirmar con el dueño del producto.

## Preguntas abiertas (priorizadas)

| Prioridad | Pregunta | Bloquea | Decisor |
|-----------|----------|---------|---------|
| Alta | PA-01 — WhatsApp v1: ¿API oficial Cloud API (costo por mensaje, plantillas, opt-in) o vía artesanal/gateway (barata, frágil, riesgo de baneo)? Incluye: tabla de costos, entregabilidad, fallback y panel de consumo. | Sprint 1 (diseño de `notificaciones/` + env vars + costos) | Dueño producto + técnico |
| Alta | PA-02 — Alcance exacto de "facturación" v1: ¿solo caja (cobros/saldos/deudas/cierre) o algún comprobante interno no fiscal (recibo PDF numerado)? | Sprint 1 (modelo `cobros/` + US-006/008) | Dueño producto |
| Alta | PA-03 — Dental Manager y MednIA: ¿se reintentan con navegador manual (URLs internas /precios, /funcionalidades) o se descartan del set competitivo? | Análisis D.1 (demos) | Dueño producto |
| Media | PA-04 — Regla 24h: ¿aplica igual a primera visita con seña que a control sin seña? ¿Ventanas distintas por prestación? | Sprint 2 (RN-AG-01/02, config) | Dueño producto |
| Media | PA-05 — Política de devolución de seña por defecto y medios de devolución (¿solo saldo a favor o devolución MP real en v1?) | Sprint 2 (RN-CO-03, US-007) | Dueño producto |
| Media | PA-06 — TTL de oferta de lista de espera y orden de prioridad (¿solo FIFO o score de ausentismo simple?) | Sprint 2 (US-005) | Equipo producto |
| Baja | PA-07 — Adecuación legal fina (Leyes 25.326/26.529/25.506): alcance de "firma simple" en evoluciones y textos de opt-in/DPA antes del lanzamiento | Lanzamiento | Abogado + producto |
| Baja | PA-08 — Antelación mínima de reserva pública y timeout de pago pendiente (defaults propuestos: 2h y 30 min) | Sprint 2 | Equipo técnico |
