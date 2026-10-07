# Funcionalidades

Organizadas por **épica** y luego por **historia de usuario** (formato US-NNN). v1 = épicas E1–E5. E6 es backlog v2+ (se documenta para no perder el norte, no para construir).

## Épica 1: Agenda anti-ausentismo

### US-001 — Agendar turno sin colisiones
**Como** recepcionista
**Quiero** crear un turno eligiendo paciente, profesional, prestación y horario
**Para** llenar el sillón sin dobles reservas

**Criterios de aceptación**:
- [ ] CA-1: el sistema propone solo huecos reales (duración por prestación + bloqueos + antelación mínima).
- [ ] CA-2: si hay colisión, rechaza con 3 huecos alternativos sugeridos.
- [ ] CA-3: permite sobreturno explícito con motivo (no silencioso).

**Reglas relacionadas**: RN-AG-03, RN-AG-04, RN-AG-06

### US-002 — Reserva pública 24/7 por link
**Como** paciente sin cuenta
**Quiero** reservar desde el link del consultorio y confirmar/cancelar/reprogramar desde WhatsApp
**Para** no depender del horario de atención

**Criterios de aceptación**:
- [ ] CA-1: link por tenant (`/r/:slug`) con disponibilidad real.
- [ ] CA-2: la reserva crea turno `pendiente_confirmacion` (o confirmado si hay seña acreditada).
- [ ] CA-3: cada turno emite token único para acciones sin login, con expiración.

**Reglas relacionadas**: RN-AG-06, RN-AG-07, RN-AU-03, RN-CO-02

### US-003 — Recordatorios automáticos + confirmación
**Como** recepcionista
**Quiero** que el sistema envíe recordatorios T-48h/T-24h y pida confirmación por WhatsApp
**Para** bajar el ausentismo sin trabajo manual

**Criterios de aceptación**:
- [ ] CA-1: envío automático en ventanas configurables, máximo 1 por ventana/turno.
- [ ] CA-2: el paciente confirma con un toque (token); el turno pasa a `confirmado`.
- [ ] CA-3: fallback a email si WhatsApp falla; panel de consumo/costo visible.

**Reglas relacionadas**: RN-PA-01, RN-PA-03, RN-PA-04, RN-GL-03

### US-004 — Cancelación con regla 24h configurable
**Como** dueño
**Quiero** configurar la antelación mínima de cancelación (defecto 24h)
**Para** proteger el sillón con una política clara y aplicable

**Criterios de aceptación**:
- [ ] CA-1: config en horas por tenant, solo rol dueño.
- [ ] CA-2: cancelar fuera de término se bloquea con error `RN-AG-01` y ofrece reprogramar.
- [ ] CA-3: el cambio rige solo para turnos futuros.

**Reglas relacionadas**: RN-AG-01, RN-AG-02

### US-005 — Lista de espera automática
**Como** recepcionista
**Quiero** que un hueco liberado se ofrezca solo al siguiente en lista por WhatsApp
**Para** recuperar facturación que hoy se pierde

**Criterios de aceptación**:
- [ ] CA-1: al liberarse un hueco compatible, oferta automática al primero elegible con TTL (defecto 2h). **Suposición:** TTL 2h; validar.
- [ ] CA-2: si vence/declina, pasa al siguiente; si acepta, el turno se asigna y sale de la lista.
- [ ] CA-3: estados de lista auditables (`activa|ofrecida|convertida|vencida`).

**Reglas relacionadas**: RN-AG-03, RN-PA-01

## Épica 2: Cobros y caja manual + señas

### US-006 — Cobrar y ver saldos/deudas
**Como** dueño
**Quiero** registrar cobros (efectivo/transferencia/MP/otro) y ver saldos y deudas por paciente
**Para** saber cuánta plata entró y cuánta falta cobrar

**Criterios de aceptación**:
- [ ] CA-1: alta de cobro en < 30 segundos con concepto y medio.
- [ ] CA-2: saldo derivado automático, nunca editable directo.
- [ ] CA-3: vista de deudas ordenada por antigüedad/monto.

**Reglas relacionadas**: RN-CO-01, RN-CO-05

### US-007 — Seña por Mercado Pago con arrastre
**Como** dueño
**Quiero** exigir seña por MP al reservar, que se arrastra si reprograman
**Para** que la reserva sea compromiso real, no intención

**Criterios de aceptación**:
- [ ] CA-1: seña configurable por tenant/prestación (monto, requerida u opcional).
- [ ] CA-2: reserva pública genera preferencia MP; webhook acredita y confirma el turno.
- [ ] CA-3: reprogramar arrastra la seña; política de devolución parametrizable.

**Reglas relacionadas**: RN-CO-02, RN-CO-03, RN-AG-05

### US-008 — Cierre de caja diario
**Como** dueño
**Quiero** cerrar la caja del día por medio de pago
**Para** conciliar sin planilla paralela

**Criterios de aceptación**:
- [ ] CA-1: cierre con totales por medio + observaciones.
- [ ] CA-2: cierre inmutable; solo nota de ajuste auditada.

**Reglas relacionadas**: RN-CO-04, RN-GL-02

## Épica 3: Ficha de pacientes + WhatsApp

### US-009 — Ficha con HCE mínima y presupuestos
**Como** odontólogo
**Quiero** ver la ficha (datos, evoluciones, adjuntos RX/fotos) y registrar la atención + presupuesto simple
**Para** no depender del papel

**Criterios de aceptación**:
- [ ] CA-1: ficha única con timeline de evoluciones y adjuntos.
- [ ] CA-2: evolución firmada simple con alcance legal declarado (no firma digital Ley 25.506).
- [ ] CA-3: presupuesto simple con items que alimenta el saldo.

**Reglas relacionadas**: RN-GL-02

### US-010 — Importar pacientes y exportar todo
**Como** recepcionista/dueño
**Quiero** importar pacientes por CSV y exportar mis datos en un clic
**Para** entrar en el día e irme cuando quiera (anti lock-in)

**Criterios de aceptación**:
- [ ] CA-1: importación CSV con reporte de filas ok/duplicadas/fallidas.
- [ ] CA-2: exportación CSV/Excel/PDF por recurso.

**Reglas relacionadas**: RN-GL-04

## Épica 4: Roles y configuración (3-roles-1-persona)

### US-011 — Operar con roles acumulables
**Como** dueño de consultorio unipersonal
**Quiero** tener los 3 roles en mi único usuario
**Para** agendar, registrar y cobrar sin cambiar de cuenta

**Criterios de aceptación**:
- [ ] CA-1: asignación múltiple de roles por usuario; permiso = unión.
- [ ] CA-2: invitar usuarios con roles acotados (ej. solo recepción).

**Reglas relacionadas**: RN-AU-01, RN-AU-04

## Épica 5: Transparencia radical (diferenciador)

### US-012 — Ver costos y límites declarados
**Como** dueño
**Quiero** ver el consumo/costo de WhatsApp y saber qué NO hace el sistema
**Para** confiar en el precio que pago

**Criterios de aceptación**:
- [ ] CA-1: panel de consumo WhatsApp (mensajes, costo estimado) por período.
- [ ] CA-2: sección "qué no hace (aún)" visible con roadmap honesto.
- [ ] CA-3: precio ARS del plan visible in-app.

**Reglas relacionadas**: RN-PA-03, RN-CO-01

## Épica 6 (backlog v2+, NO v1): Clínica completa y fiscalidad

- Odontograma FDI versionado + periodontograma BOP/NIC/placa (responde R1; migración v1→v2 garantizada).
- Reportes/analytics del dueño por profesional/sillón.
- Obras sociales/prepagas (convenios, aranceles, autorizaciones, liquidaciones) + FE ARCA.
- Chatbot IA opt-in, campañas, multi-sucursal, API pública.
