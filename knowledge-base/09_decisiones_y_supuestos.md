# Decisiones y Supuestos

## Decisiones documentadas

### DD-01 — Salir en v1 sin odontograma
**Decisión**: v1 = agenda + recordatorios → caja/señas → ficha mínima + WhatsApp. Odontograma e HC completa van a v2+.
**Contexto**: los 15 competidores tienen odontograma como núcleo; salir sin él es ir contra el estándar (riesgo R1 confirmado por el usuario en discovery).
**Alternativas consideradas**: (a) odontograma básico en v1 y recortar caja/señas; (b) v1 solo agenda.
**Justificación**: el discovery confirma que el dolor pagable es ausentismo + cobro, no clínica; la apuesta es que gestión+cobros 10× mejores compensan. El análisis competitivo (C.4-3) propone el camino progresivo con migración garantizada.
**Trade-offs aceptados**: fricción comercial contra consultorios que exigen odontograma; posible adelanto a v1 si las demos lo muestran eliminatorio (gatillo definido en análisis D.3).

### DD-02 — Caja manual sin AFIP/ARCA en v1
**Decisión**: "facturación" v1 = cobros/saldos/deudas/cierre, sin comprobantes fiscales.
**Contexto**: integrar ARCA en v1 multiplica costo y riesgo; Dentatools valida que la transparencia negativa ("no hacemos AFIP") puede ser diferencial.
**Alternativas consideradas**: (a) FE ARCA en v1; (b) comprobante interno no fiscal en v1.
**Justificación**: presupuesto/plazo flexibles pero equipo chico; el supuesto de que caja manual no defrauda se valida en entrevistas (SU-03).
**Trade-offs aceptados**: dueños que necesitan factura electrónica quedan fuera hasta v2; la UI debe declararlo para no defraudar.

### DD-03 — Stack FastAPI + React + Postgres + Redis + Docker
**Decisión**: backend Python FastAPI (JWT, SQLAlchemy) + Postgres + Redis; frontend React+TS+Vite; Docker Compose.
**Contexto**: sin stack obligatorio; se elige productividad + costo operativo bajo + OpenAPI gratis + workers Redis para WhatsApp.
**Alternativas consideradas**: (a) Next.js full-stack; (b) Django monolito con templates.
**Justificación**: FastAPI da validación/async/webhooks baratos; React+Vite separa la reserva pública liviana; Compose = un deploy.
**Trade-offs aceptados**: dos codebases (front/back) vs. full-stack único; se mitiga con contratos OpenAPI generados.

### DD-04 — Multi-tenant row-level (un tenant por consultorio)
**Decisión**: aislamiento por `tenant_id` + JWT, sin DB por tenant en v1.
**Contexto**: muchos consultorios chicos; costo por tenant debe tender a cero.
**Alternativas consideradas**: (a) schema/DB por tenant; (b) instancia por consultorio.
**Justificación**: costo operativo bajo (prioridad de calidad); RLS Postgres como endurecimiento posterior.
**Trade-offs aceptados**: un bug de filtro expone datos cruzados — se mitiga con middleware obligatorio + tests de aislamiento por tenant.

### DD-05 — Seña por Mercado Pago + regla 24h configurable como diferenciadores v1
**Decisión**: seña MP (no cobro online completo) + cancelación configurable (24h defecto) + lista de espera automática + transparencia radical como apuestas que el mercado no cierra (vacíos C.3-2/7, C.4-1/2 del análisis).
**Contexto**: ningún dental-vertical publica política configurable de seña/antelación; Turnito/Gendu solo esbozan la seña genérica.
**Alternativas consideradas**: (a) sin seña en v1; (b) cobro online completo en v1.
**Justificación**: seña acotada = 80% del valor anti-ausentismo con 20% del costo de un checkout completo.
**Trade-offs aceptados**: depende de la cuenta MP de cada consultorio (onboarding con fricción; documentar guía paso a paso).

### DD-06 — Roles acumulables ("3-roles-1-persona")
**Decisión**: un usuario puede tener los 3 roles; permiso = unión; nada exige tres personas.
**Contexto**: consultorios de 1–2 personas (discovery §2).
**Alternativas consideradas**: (a) 3 usuarios obligatorios; (b) sin roles (todo abierto).
**Justificación**: fricción cero para el consultorio chico sin resignar permisos cuando crece.
**Trade-offs aceptados**: auditoría debe registrar rol activo en cada acción para no perder trazabilidad.

## Supuestos inferidos

### SU-01 — WhatsApp es el canal que decide la compra
**Supuesto**: el consultorio elige/huye por cómo funciona WhatsApp (costo, entregabilidad, automatismo real).
**Origen**: discovery §§1/8 + análisis C.3-2 (todos ambiguos en "automático").
**Riesgo si es falso**: sobre-invertir en WhatsApp vs. agenda/caja.
**Cómo validar**: 5 entrevistas con la pregunta "¿qué te haría pagar?" antes del Sprint 2; decisión PA-01 primero.

### SU-02 — 3-roles-1-persona no genera caos de permisos
**Supuesto**: la unión de permisos en un solo usuario es usable y auditable sin rol "encargado" intermedio.
**Origen**: nota estructural de discovery §2, confirmada por el usuario.
**Riesgo si es falso**: el dueño unipersonal ve demasiada UI o la auditoría se vuelve inútil.
**Cómo validar**: test de usabilidad con 2 consultorios unipersonales en prototipo; crear rol intermedio solo con evidencia.

### SU-03 — Caja manual sin AFIP no defrauda
**Supuesto**: el dueño acepta "caja, no factura" en v1 si se declara honestamente.
**Origen**: discovery §10 (supuesto sin probar).
**Riesgo si es falso**: churn temprano por expectativa fiscal.
**Cómo validar**: mensaje explícito en landing + onboarding; medir objeción en demos D.1 (DrApp/Benty muestran que FE AR existe en el mercado).

### SU-04 — Precio ARS publicado compensa la presión gratuita
**Supuesto**: transparencia (precio + costos WhatsApp + "qué no hace") justifica pagar frente a Gendu/Turnito/Doctocliq gratis.
**Origen**: análisis C.2 (Dentatools) + C.3-10 + riesgo de tiers gratuitos (discovery §10).
**Riesgo si es falso**: el producto pago no convierte aunque sea mejor.
**Cómo validar**: definir posicionamiento/precio antes del código (advertencia D.3); test A/B de landing con/sin "qué no hace".
