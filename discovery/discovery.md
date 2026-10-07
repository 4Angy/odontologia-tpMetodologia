# Discovery — Gestión para consultorios odontológicos

**Fecha**: 2026-10-05
**Fuentes investigadas**: 15 competidores (ver `discovery/sources/`)

## 1. Problema que resuelve

Los consultorios odontológicos chicos coordinan turnos por WhatsApp y llevan
la gestión en papel, lo que genera ausentismo (turnos perdidos = plata perdida),
dobles reservas y tiempo administrativo que le quita horas al sillón.

## 2. Usuarios / roles

- **Recepcionista**: agenda turnos y gestiona la agenda del día.
- **Odontólogo**: registra la atención y consulta la ficha del paciente.
- **Dueño**: cobra, controla la caja y mira los números del consultorio.

Nota: en un consultorio chico estos tres roles suelen ser la misma persona (o
dos). El sistema no asume que sean tres personas distintas.

## 3. Casos de uso

1. Como recepcionista, quiero agendar un turno y que el paciente reciba un
   recordatorio automático por WhatsApp para que no falte.
2. Como odontólogo, quiero ver la ficha del paciente y registrar lo atendido
   para no depender del papel.
3. Como dueño, quiero registrar cobros, saldos y deudas para saber cuánta plata
   entró y cuánta falta cobrar.

## 4. Competidores / soluciones existentes

| Competidor | Problema que resuelve | Pricing | Diferenciadores |
|---|---|---|---|
| Dentalink | Gestión integral de la clínica dental punta a punta | No publicado (cotización) | Líder LATAM, clínica + administración + IA en un solo lugar |
| Reservo | Control total del centro de salud (agenda, ausencias, administración) | No publicado | Certificación Fonasa/CENS (Chile), multi-rubro salud + estética |
| AgendaPro | Ordenar el negocio y acelerar crecimiento (+82% según su discurso) | No publicado | Agentes de IA propios, foco en crecimiento del negocio |
| DrApp | Carga administrativa que quita tiempo de atención | Desde $34.700/profesional/mes | Ecosistema propio (Crontu, Receto), IA con revisión humana obligatoria |
| Benty | Orden del consultorio diario, 100% odontología argentina | No publicado (1 mes bonificado) | Simplicidad + acompañamiento personalizado en puesta en marcha |
| DenPro | Turnos, HC y flujo diario con velocidad y claridad | Basic $19.900/mes, planes Team/Full | Privacidad como eje (AES-256, ISO 27001), precio en moneda local |
| Dentatools | Salir del papel y las planillas sueltas | $30.000/mes (3 odontólogos) + $8.000/adicional | Precio único simple en pesos; declara que NO hace obra social ni AFIP |
| Dental Manager | (sin dato — página vacía al investigar) | No publicado | No determinado |
| Clinic Cloud | Gestión de la clínica de principio a fin | No publicado (prueba gratis) | Ecosistema Doctoralia (visibilidad + reserva + reseñas) |
| Doctocliq | Clínica sin perder el control (agenda + clínica + finanzas) | Gratis / desde USD 19/mes | Plan gratuito permanente, todo-en-uno fácil de usar |
| DentalSoftWeb | Unificar lo fragmentado (historia, factura, reportes) | USD 362,50/año (plan 500) | Normativa colombiana en el ADN (RIPS/DIAN); dictado con IA |
| Dentiqa | Agenda + fichas + comunicación en una plataforma | Starter USD 89/mes tarifa plana | Chatbot IA de 3 capas como núcleo, pricing flat público |
| Turnito | Agenda de turnos sin papel ni WhatsApp | 100% gratis (según su página) | Gratuidad + simplicidad extrema |
| MednIA | (sin dato — página vacía al investigar) | No publicado | No determinado |
| Gendu (gendu.com.ar) | Agendas complicadas, ausentismo, gestión agotadora | Gratuito para siempre (plan base) | Turnos ilimitados gratis + marketing integrado (SEO, reseñas) |

**Notas**: el set foco son los argentinos con precio en pesos (DenPro,
Dentatools, DrApp, Benty) más la presión gratuita (Gendu, Turnito, Doctocliq
gratis). Casi nadie publica precio: Dentalink, Benty, AgendaPro y Clinic Cloud
piden cotización. Calidad del dato: 10 notas completas, 3 parciales (Reservo,
Dentiqa, Gendu — complementadas con búsqueda, marcadas como no verificadas) y
2 fallidas (Dental Manager, MednIA).

## 5. Funcionalidades necesarias

- Agenda de turnos con recordatorios automáticos anti-ausentismo.
- Registro de cobros, caja, saldos y deudas (caja manual, sin AFIP en v1).
- Ficha de pacientes con comunicación por WhatsApp.

## 6. Funcionalidades opcionales

- Odontograma + historia clínica completa (post-v1 — apuesta consciente: todos
  los competidores lo tienen como núcleo, esto se registra como riesgo R1).
- Reportes y números del consultorio para el dueño.
- Obras sociales / prepagas.

## 7. Reglas de negocio

- No se puede cancelar un turno con menos de 24 horas de anticipación.
- La antelación mínima debe ser configurable (el valor 24h es el acordado, no
  una constante quemada).

## 8. Integraciones

- WhatsApp en la v1 (recordatorios y confirmación de turnos). Queda por
  decidir en construcción: API oficial (costo por mensaje) vs vía artesanal.
- Explícitamente fuera de la v1: facturación electrónica AFIP, cobro online
  (MercadoPago o similar) y obras sociales. "Facturación" en v1 = caja manual.

## 9. Restricciones

- Ninguna restricción rígida: presupuesto y plazo flexibles.
- Sin stack ni deploy obligatorio.

## 10. Riesgos

- **R1 (principal, confirmado por el usuario)**: salir sin odontograma cuando
  los 15 competidores lo tienen como núcleo — la diferenciación por gestión +
  cobros tiene que ser lo suficientemente fuerte.
- **Supuesto sin probar**: que "facturación" como caja manual (sin AFIP) no
  defraude la expectativa del dueño.
- **Supuesto sin probar**: que 3 roles separados sirvan en consultorios donde
  una sola persona hace todo.
- **Riesgo**: presión de tiers gratuitos (Gendu, Turnito, Doctocliq gratis)
  contra un producto pago — el pricing y el posicionamiento importan desde el
  día 1.

## 11. Preguntas abiertas

- ¿WhatsApp por API oficial o vía artesanal para la v1?
- ¿Alcance exacto de "facturación" en v1 (solo caja, o algún comprobante)?
- ¿Se reintenta el dato de Dental Manager y MednIA, o se los descarta del set?
