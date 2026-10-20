# ADR-001 — Proveedor de WhatsApp en v1: `official` (Cloud API de Meta)

- **Estado:** aceptada
- **Fecha:** 2026-10-19
- **Decide:** C-01 `foundation-setup-decisiones`
- **Cierra:** PA-01 (`knowledge-base/10_preguntas_abiertas.md`)
- **Owner del comportamiento:** **C-09** (`notificaciones-whatsapp-worker`)
- **Reversibilidad:** cambiar el default de `WHATSAPP_PROVIDER`. La interfaz `WhatsAppClient` lo soporta desde el día 1.

## 1. Contexto

La KB ya había resuelto la *forma* de la decisión: `WHATSAPP_PROVIDER=official|gateway` está en la tabla de variables de entorno y `02_descripcion_general.md` decía "API oficial Cloud API **o** gateway artesanal — POR DECIDIR". El módulo `notificaciones/` consume siempre la misma interfaz, así que lo que faltaba era decidir **qué se implementa en v1 y cuál es el default**.

Dos hechos del mercado condicionan la decisión:

1. El análisis competitivo (`discovery/analisis-competitivo.md` §C.3-2) muestra que **nadie** en el mercado argentino publica costo por mensaje ni distingue API oficial de gateway artesanal. La apuesta §C.4-1 ("WhatsApp primero, honesto": API oficial + costos transparentes + plantillas preaprobadas + opt-in + fallback + panel de consumo) es exactamente este producto.
2. El filtro de calidad del proyecto es **costo operativo bajo** (DD-03). El gateway artesanal tiene costo de dinero ~0, pero su costo real es operacional: riesgo de baneo del número, entregabilidad no garantizada y ausencia de estado de entrega confiable — lo que volvería el panel de consumo de C-09 un estimado en lugar de un dato.

## 2. Decisión

**El proveedor de WhatsApp en v1 es `official` (Cloud API de Meta).**

- Se implementa **un único adaptador**, `OfficialWhatsAppClient`, detrás de la interfaz `WhatsAppClient`. El dominio no sabe qué proveedor hay detrás.
- `WHATSAPP_PROVIDER=official` es el **valor por defecto**. El valor `gateway` **sobrevive en el enum**, documentado como camino de v2, **sin implementar en v1**.
- Variables que lo configuran (KB §Variables de entorno):
  - `WHATSAPP_PROVIDER=official`
  - `WHATSAPP_API_TOKEN` — token de la WABA (sensible)
  - `WHATSAPP_PHONE_ID` — número remitente
- **No se implementa un segundo proveedor en v1.** El fallback ante caída del proveedor es el **email** (RN-PA-04), no otro proveedor de WhatsApp.

## 3. Costos por tipo de mensaje

Meta factura **por mensaje entregado** (no enviado) y según la **categoría** y el **país del destinatario**. Tarifas vigentes desde el **2026-10-01** (tarifario oficial de Meta, mercado Argentina):

| Categoría | USD por mensaje | BRL por mensaje | Qué es en este producto |
|---|---|---|---|
| Marketing | 0.0618 | 0.3181 | Campañas y reactivación. **Fuera de v1** (§C.4-1 lo posterga). |
| Utility | 0.0260 | 0.1338 | Recordatorios T-48h/T-24h, confirmación, aviso de lista de espera. **El grueso de v1.** |
| Authentication | 0.0260 | 0.1338 | Verificación de identidad. No se usa en v1. |
| Service | 0.0260 | 0.1338 | Respuesta libre dentro de la ventana de 24 h del paciente. |

Reglas vigentes que afectan el costo:

- Los **1.000 primeros mensajes `service` del mes son gratis**, por número de teléfono emisor.
- Desde el 2026-10-01 los mensajes `service` (respuesta libre dentro de la ventana de 24 h) **se cobran**; antes eran gratis.
- `utility` y `authentication` tienen **tramos por volumen** en Argentina: lista hasta 100.000 mensajes/mes (−5 % a partir de 100.001; −10 % a partir de 1.000.001; −25 % a partir de 4.500.000).
- Los mensajes enviados dentro de las 72 h posteriores a un clic en un anuncio de Facebook/Instagram no se cobran.

**Costo mensual estimado de un consultorio chico** (300 turnos/mes, 1 confirmación + 2 recordatorios = 900 mensajes `utility`):

| Escenario | Mensajes | Costo mensual estimado |
|---|---|---|
| 100 turnos/mes | 300 | ~USD 7,80 |
| 300 turnos/mes | 900 | ~USD 23,40 |
| 1.000 turnos/mes | 3.000 | ~USD 78,00 |

> Estas cifras son un cálculo sobre el tarifario de lista: no incluyen mensajes de categoría `service` ni de `marketing`, ni el costo de un proveedor agregador (Twilio, etc.), que cobra su propia tarifa por mensaje además de la de Meta. **C-09 debe recalcular con el consumo real** y mostrarlo en el panel de consumo.

## 4. Entregabilidad y riesgo de baneo

| Aspecto | `official` (decidido) | `gateway` artesanal (descartado) |
|---|---|---|
| Identidad de la cuenta | WABA verificada, número de empresa | Cuenta personal o de empresa sin verificación |
| Riesgo de baneo | Bajo: Meta penaliza el contenido y los envíos abusivos, no la cuenta por usar la API | **Alto**: un gateway puede ser baneado por detección de automatización, y un baneo deja al consultorio sin canal de contacto con sus pacientes |
| Entregabilidad | Alta, con plantillas preaprobadas y estado de entrega por webhook | No garantizada: depende del método de automatización y de la cuenta |
| Estado de entrega | Webhook `statuses` (entregado, leído, fallido) | Sólo lo que exponga el gateway; sin webhook confiable |
| Plantillas | Preaprobadas por Meta: la empresa puede auditar qué se manda | Mensajes libres, sin auditoría ni control |
| Costo | Dinero, medible y publicable | ~$0 en dinero, pero riesgo operacional no medible |

**Consecuencia asumida:** el costo por mensaje es real y hay que mostrarlo. La respuesta de producto es el **panel de consumo de C-09** (US-012), que es a la vez el diferencial y la prueba de que la decisión fue deliberada.

## 5. Fallback y observabilidad

- **Fallback de canal:** email (RN-PA-04). Si el paciente no tiene opt-in de WhatsApp, no hay envíos (RN-PA-01) y se registra el motivo; si el envío falla, hay 3 reintentos exponenciales y después fallback a email si hay dirección.
- **Ningún proveedor externo bloquea el flujo local** (RN-GL-03): un turno se cancela igual aunque WhatsApp esté caído; el envío queda `encolada` con reintento.
- **Observabilidad:** cada envío guarda `provider_msg_id` (clave de idempotencia, R8), estado, costo estimado y período de consumo. El webhook de entrada (`POST /webhooks/whatsapp`) es idempotente por `provider_msg_id`.
- **Anti-spam:** máximo 1 mensaje por ventana y por turno (RN-PA-03). Las ventanas (T-48h/T-24h) y las plantillas son configurables por tenant, nunca constantes quemadas.

## 6. Runbook de onboarding por tenant

El alta de un consultorio en WhatsApp **no es un cambio de código**: es un proceso de Meta. El runbook vive en `docs/runbooks/whatsapp-onboarding.md` (lo escribe C-09) y su contenido mínimo es:

1. Crear la **WABA** (WhatsApp Business Account) y verificarla con el número del consultorio.
2. Registrar la app en Meta y obtener el **token permanente** → `WHATSAPP_API_TOKEN`.
3. Anotar el **ID del número emisor** → `WHATSAPP_PHONE_ID`.
4. Crear y **someter a aprobación** las plantillas (confirmación, recordatorio T-48h, recordatorio T-24h, cancelación, oferta de lista de espera). Los textos en español-AR viven en la tabla `plantilla` (C-09), versionados.
5. Configurar el webhook de estados y verificar la recepción con un mensaje de prueba.
6. Cargar el costo por mensaje vigente en el panel de consumo de C-09.

**Tiempo de onboarding esperado:** del alta de la WABA a la primera plantilla aprobada hay una espera de revisión de Meta que **no depende del equipo**. Es el costo de esta decisión y hay que decirlo en la onboarding del cliente (C-13).

## Alternativas descartadas

- **Gateway artesanal** (Evolution API / Baileys / whatsapp-web.js sobre número propio): costo monetario ~0, pero riesgo de baneo, sin plantillas, sin estado de entrega y en contradicción directa con §C.4-1 y §D.3 del análisis competitivo.
- **Ambos adaptadores en v1** (`official` como default + `gateway` como failover): duplica la superficie de C-09 (governance ALTO) para cubrir un modo de operación que no es un modo real. Si el proveedor oficial fuera una causa frecuente de caída, se evaluaría en v2.

## Consecuencias

- **C-09** implementa `OfficialWhatsAppClient`, el worker con reintentos, el fallback a email y el panel de consumo.
- **C-10** (lista de espera) reusa el mismo canal; su TTL de 2 h (PA-06) sigue siendo un supuesto sin validar.
- **C-13** publica el costo por mensaje en la UI (transparencia radical).
- **Reversión:** cambiar `WHATSAPP_PROVIDER` a `gateway` e implementar el adaptador faltante. La interfaz lo permite sin tocar el dominio.
