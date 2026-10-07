# Visión y Objetivos

## Propósito del sistema

**SaaS multi-tenant de gestión para consultorios odontológicos chicos argentinos que pierden plata por ausentismo y gestionan todo por WhatsApp y papel.**

El sistema ataca una sola cadena de valor en v1: agendar → recordar/confirmar por WhatsApp para que el paciente no falte → atender y registrar → cobrar y saber cuánta plata entró y cuánta falta cobrar. Todo lo que no sirva directamente a esa cadena queda fuera de v1. La diferenciación frente a los 15 competidores relevados no está en profundidad clínica (todos tienen odontograma; nosotros salimos sin él — riesgo R1 asumido), sino en gestión + cobros simples, seña con regla 24h, lista de espera automática y transparencia radical (precio ARS publicado, costos WhatsApp visibles, "qué NO hace" declarado).

## Objetivos por actor

| Actor | Objetivo principal | Objetivos secundarios |
|-------|-------------------|----------------------|
| Recepcionista (agenda) | Llenar el sillón sin dobles reservas ni huecos muertos | Confirmar/reprogramar en pocos clics; recuperar huecos con lista de espera |
| Odontólogo (registra) | Registrar lo atendido sin depender del papel | Consultar ficha + evoluciones + adjuntos antes de atender; emitir presupuestos simples |
| Dueño (cobra / mira números) | Saber cuánta plata entró y cuánta falta cobrar | Registrar cobros/caja/saldos/deudas; cobrar seña por Mercado Pago; ver números básicos del día |

> Nota estructural: en un consultorio chico estos tres roles suelen ser la misma persona (o dos). El sistema no asume tres personas distintas (ver `03_actores_y_roles.md` y supuesto SU-02 en `09_decisiones_y_supuestos.md`).

## Alcance v1

- Agenda multi-profesional (vista día/semana) con duración variable por prestación, bloqueos, sobreturnos explícitos y prevención de solapamientos.
- Reserva online 24/7 por link compartible (WhatsApp/redes/web) con confirmación, cancelación y reprogramación por el paciente.
- Recordatorios y confirmaciones automáticas por WhatsApp + fallback por email; panel de consumo/costos visible; opt-in del paciente.
- Regla de cancelación con antelación mínima configurable (24h por defecto, no quemada) + seña por Mercado Pago con arrastre ante reprogramación.
- Lista de espera automática: hueco liberado → oferta por WhatsApp al siguiente en lista.
- Ficha de paciente + HCE mínima (evolución, adjuntos RX/fotos, recetas/documentos) + presupuestos simples.
- Caja manual: cobros, saldos, deudas, cierre de caja del día. Sin AFIP/ARCA en v1.
- Roles y permisos (recepción / odontólogo / dueño, incluyendo "todo en una persona") + auditoría mínima + exportación en un clic (CSV/Excel/PDF).
- Onboarding en el día: alta guiada + importación CSV + prueba sin tarjeta.

## Fuera de alcance

Explícitamente fuera de v1 (backlog v2+, no "fase 2 de este sprint"):

- Odontograma + historia clínica completa (odontograma FDI versionado, periodontograma BOP/NIC/placa). Apuesta consciente — ver riesgo R1 en `09_decisiones_y_supuestos.md`.
- Reportes y analytics avanzados del dueño (más allá de números básicos del día/caja).
- Obras sociales / prepagas (convenios, aranceles, autorizaciones, liquidaciones).
- Facturación electrónica AFIP/ARCA ("facturación" en v1 = caja manual).
- Cobro online completo más allá de la seña por Mercado Pago; marketplace de turnos; chatbot IA; campañas de marketing; multi-sucursal; API pública.

## Métricas de éxito

| Métrica | Meta v1 | Cómo se mide |
|---------|---------|--------------|
| Tasa de ausentismo | −30% vs. línea base del consultorio a 90 días | Ausentes / turnos agendados por tenant |
| Tiempo agenda diaria | < 5 min para armar el día | Instrumentación frontend (opcional v1) / encuesta onboarding |
| Cobro de señas | > 50% de turnos con seña cobrada donde el consultorio la exige | Señas cobradas / turnos con seña requerida |
| Adopción papel→sistema | 100% de turnos del día cargados en sistema a 30 días | Turnos en sistema vs. auto-reporte |
| Time-to-value | Consultorio operando el mismo día del alta | Alta → primer turno agendado < 24h |
| Transparencia | Precio ARS + costo WhatsApp publicados y visibles in-app | Checklist de lanzamiento (binario) |
