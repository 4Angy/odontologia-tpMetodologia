# Explore: Cancelar turnos y liberar el horario

- Fecha: 2026-10-06
- Modo: `openspec-explore` (thinking-partner, NO implementacion, NO codigo)
- Estado del proyecto: GREENFIELD. `openspec list` = cero changes activos. No hay backend/frontend. Todo lo afirmado aqui viene de artefactos de planificacion, no de codigo.
- Fuentes leidas: `knowledge-base/05_reglas_de_negocio.md`, `06_funcionalidades.md`, `07_flujos_principales.md`, `04_modelo_de_datos.md`, `03_actores_y_roles.md`, `10_preguntas_abiertas.md`, `CHANGES.md` (C-06/C-07/C-08/C-09/C-10/C-12), `AGENTS.md` (R1-R14).

---

## 1. Problem statement

"Cancelar turnos y liberar el horario" suena como una funcionalidad autocontenida, pero en este proyecto es un flujo transversal que toca cinco piezas:

1. Validar la politica de antelacion (24h configurable por tenant).
2. Cambiar el estado del turno y dejar el hueco visible/libre en agenda.
3. Resolver el destino de la sena (si existe).
4. Avisar al paciente (y registrar el aviso).
5. Ofrecer el hueco a la lista de espera (si hay cola).

La pregunta que origina este explore: es esto un change NUEVO, o ya esta cubierto por C-07 `turnos-agenda-interna` y C-10 `lista-espera-automatica`?

---

## 2. Hallazgos en los artefactos

### 2.1 Reglas de negocio (05)

- RN-AG-01: cancelar con menos antelacion que la configurada se bloquea con error trazable y ofrece reprogramar. Valor por defecto 24h, configurable, nunca constante quemada.
- RN-AG-02: solo `dueno` modifica la antelacion; rige para turnos futuros, no retroactivo.
- RN-AG-05: reprogramar arrastra la sena acreditada (no se cobra dos veces).
- RN-CO-03: destino de la sena al cancelar es parametrizable (`no_devuelve | devuelve_50 | devuelve_100`); default propuesto: en termino = saldo a favor, fuera de termino = se pierde. Es suposicion sin validar (PA-05).
- RN-GL-01: todo error de negocio devuelve `code` = RN que lo causo (ej. `RN-AG-01`), mensaje en espanol-AR mostrable.
- RN-GL-02: toda mutacion escribe auditoria (quien/cuando/que).
- RN-GL-03: ninguna integracion externa bloquea el flujo local (WhatsApp/MP caidos = operacion local completa + envio `encolada` con reintento).
- RN-PA-01: sin opt-in WhatsApp no hay envios, ni siquiera transaccionales.

### 2.2 Funcionalidades (06)

- US-001 (agendar sin colisiones): define colision, sobreturno explicito y huecos alternativos. No es cancelacion, pero fija el invariante que la cancelacion debe preservar (al liberar, el hueco vuelve a ser ofrecible sin romper RN-AG-03).
- US-004 (cancelacion con regla 24h configurable): CA-1 config por tenant solo dueno; CA-2 cancelar fuera de termino se bloquea con error `RN-AG-01` y ofrece reprogramar; CA-3 no retroactivo. Ojo: US-004 esta redactada desde el dueno/config, no desde recepcionista/paciente que cancelan todos los dias.
- US-005 (lista de espera automatica): CA-1 oferta al primero elegible con TTL (default 2h, suposicion PA-06); CA-2 vence/declina = pasa al siguiente, acepta = asigna y sale de la lista; CA-3 estados auditables.
- US-002 (reserva publica): el paciente tambien cancela/reprograma sin login via token. La cancelacion tiene dos puertas: mostrador (C-07) y publica (C-08).
- US-003 + US-007: recordatorios/confirmacion y senas. La cancelacion dispara o interrumpe esos flujos.

### 2.3 Flujos principales (07)

- Flujo 2 (cancelacion y lista de espera): pasos 1-5 ya describen el E2E completo: valida antelacion -> resuelve sena -> turno a `cancelado`, hueco libre -> motor busca primer `activa` compatible -> `ofrecida` + WhatsApp con TTL -> acepta/declina/vence. Casos de error: nadie en lista = hueco libre para carga manual; sin opt-in = se salta con motivo registrado.
- Flujo 1: el timeout de pago no acreditado en 30 min tambien "libera el hueco". Es una liberacion automatica distinta de la cancelacion manual; no mezclarlas en el mismo criterio de aceptacion.

### 2.4 Modelo de datos (04)

- `turno.estado`: `pendiente_confirmacion | confirmado | presente | ausente | cancelado | reprogramado`.
- `lista_espera.estado`: `activa | ofrecida | convertida | vencida`.
- `turno` lleva `token_publico` (acciones sin login), `senia_id` nullable, `origen` (mostrador/reserva_publica/lista_espera).
- Constraints declarados: sin solape por profesional, `fin > inicio`, cancelacion validada contra config.
- Seed/config: `antelacion_cancel_hs = 24` por defecto; plantillas WhatsApp base incluyen cancelacion y lista de espera.

### 2.5 Actores y RBAC (03)

- Cancelan: recepcionista (CRUD agenda), dueno (CRUD todo), paciente externo (via token, sin login). Odontologo solo R sobre sus turnos + bloqueos propios: NO deberia cancelar agenda ajena.
- Configuran la regla: solo dueno.
- Sistema/Worker: dispara vencimientos y lista de espera.

### 2.6 CHANGES.md (lo planificado)

- C-06 `catalogo-agenda-base`: config `antelacion_hs` default 24 + calculo de huecos reutilizable. Prerrequisito, no implementa cancelar.
- C-07 `turnos-agenda-interna` (US-001 + US-004): ya contiene `POST /turnos/:id/cancelar`, validacion RN-AG-01/02, error `code: RN-AG-01` + oferta de reprogramar, `reprogramar` con arrastre (ejecutado en C-12), idempotency en creacion, frontend dia/semana + gestion del dia + mensaje mostrable. Tests: cancelacion <24h devuelve `RN-AG-01`. Lee Flujo 2.
- C-08 `reserva-publica-tokens` (US-002): `POST /public/turnos/:token/cancelar|reprogramar`, token con expiracion, rate-limit, job de liberacion a 30 min por pago pendiente.
- C-09 `notificaciones-whatsapp-worker` (US-003): plantillas (incluye cancelacion), estados `encolada|enviada|entregada|fallida`, reintento + fallback email, panel de consumo. Es quien AVISA la cancelacion.
- C-10 `lista-espera-automatica` (US-005): motor hueco-liberado -> primer `activa` -> `ofrecida` + TTL 2h -> acepta/declina/vence -> siguiente; salta sin opt-in; vista de cola + oferta manual. Es quien REUTILIZA el hueco.
- C-12 `senias-mercadopago` (US-007): destino de la sena al cancelar/reprogramar (RN-CO-03, RN-AG-05), webhook idempotente por `mp_payment_id`.

Conclusion de lectura: el E2E "cancelar + liberar + avisar + ofrecer" esta repartido en cinco changes con C-07 como base. Ningun change lo titula "cancelar turnos", pero todos lo asumen.

---

## 3. Visualizacion (ASCII solo)

### 3.1 Maquina de estados del turno (segun modelo 04)

```
                +-------------------+
                | pendiente_confirm |
                +---+---+---+---+---+
                    |   |   |   |
         confirma --+   |   |   +-- cancela (C-07/C-08) --> [cancelado]
         (C-07/     |   |   |                                |
          C-08/     |   |   |                                +--> ofrece a lista (C-10)
          C-12)     |   |   |                                +--> avisa (C-09)
                    v   v   v
                +-----------+
                | confirmado|
                +--+--+--+--+
                   |  |  |  |
   presente (C-07)-+  |  |  +-- cancela en termino --> [cancelado] --> motor lista (C-10)
   ausente (C-07)-----+  |  +-- cancela fuera termino --> ERROR RN-AG-01 + ofrece reprogramar
   reprogramar ---------+  +-- reprograma --> [reprogramado] + nuevo turno (arrastra sena, C-12)
   (C-07/C-08)            |
                          +-- no-show sin aviso --> [ausente] (NO es cancelacion, NO libera a lista)
```

Nota: `ausente` vs `cancelado` no son intercambiables. Solo `cancelado` (y el timeout de C-08) liberan hueco hacia C-10.

### 3.2 Flujo E2E de cancelacion manual

```
  Actor                    API (C-07)              Reglas            Efectos
  -----                    ----------              ------            -------

  recepcion/paciente
  cancela turno
       |
       +--> POST .../cancelar ----> valida tenant (R1/R2, JWT o token publico en C-08)
                                       |
                                       +--> antelacion vs config tenant (RN-AG-01/02, C-06/C-07)
                                       |       |
                                       |       +-- fuera de termino --> ERROR code RN-AG-01 (R9)
                                       |       |                        + ofrece reprogramar
                                       |       |
                                       |       +-- en termino --> sigue
                                       |
                                       +--> estado actual permite cancelar?
                                       |       pendiente/confirmado = SI
                                       |       presente/ausente/cancelado/reprogramado = NO (decidir codigo error)
                                       |
                                       +--> turno --> [cancelado] + auditoria (RN-GL-02)
                                                |
                                                +--> sena? --> delega a politica C-12 (RN-CO-03)
                                                |              (C-07 NO implementa dinero, deja hook)
                                                |
                                                +--> evento HuecoLiberado --> motor lista C-10
                                                |       |
                                                |       +-- hay cola? --> primer activa elegible
                                                |       |                 --> ofrecida + WhatsApp TTL (C-09/C-10)
                                                |       +-- no hay --> hueco visible en agenda (carga manual)
                                                |
                                                +--> encola aviso cancelacion (C-09, RN-GL-03 no bloqueante)
                                                        sin opt-in --> salta + registra motivo (RN-PA-01)
```

### 3.3 Mapa de cobertura: quien hace que

```
  Topico pedido                Ya cubierto en                Faltaria explicitar
  -------------                ----------------                --------------------
  validar 24h configurable     C-06 (config) + C-07 (valida)   nada nuevo; parametrizar (PA-04)
  cancelar mostrador           C-07                            motivo? idempotencia? evento?
  cancelar publica (token)     C-08                            nada nuevo
  error trazable RN-AG-01      C-07 (R9)                       codigo para "ya cancelado" / "no cancelable"
  hueco libre visible          C-07 (agenda dia/semana)        definir evento HuecoLiberado hacia C-10
  avisar cancelacion           C-09 (plantilla + worker)       quien encola (contrato C-07 -> C-09)
  ofrecer a lista              C-10                            criterio elegibilidad + TTL (PA-06)
  destino sena                 C-12 (RN-CO-03/RN-AG-05)        hook en C-07, dinero solo en C-12 (R5/R8)
  auditoria                    RN-GL-02, C-13 (vista)          C-07 debe escribirla aunque la vista llegue en C-13
```

---

## 4. Analisis de overlap: veredicto

**Veredicto: NO crear un change nuevo. Plegar "cancelar turnos y liberar el horario" dentro de C-07 como base, con contratos explicitos hacia C-08/C-09/C-10/C-12.**

Por que no es un change nuevo:

- El nucleo (validar, cambiar estado, liberar, error `RN-AG-01`, reprogramar como salida) ya es scope escrito de C-07 con sus tests.
- La parte "automatica" (ofrecer el hueco liberado) ya es TODO el scope de C-10; duplicarla crearia dos motores compitiendo por el mismo hueco.
- La parte "avisar" ya es C-09 y la parte "sena" ya es C-12. Un change "cancelar" que incluya notificaciones y dinero violaria la atomicidad (~4-6h por change) y mezclaria gobernanzas ALTA/CRITICA.
- El proyecto es greenfield con camino critico C-01 > C-02 > C-03 > C-04 > C-07 > C-08 > C-09 > C-10 > C-13. Insertar un change "cancelar" entre C-07 y C-10 alargaria el critico sin agregar capacidad nueva.

Que SI hay que reforzar en C-07 (enmienda de alcance, no change nuevo):

1. Evento/contrato `HuecoLiberado`: C-07 al cancelar emite (o deja registrado de forma consultable) turno-id + profesional + inicio/fin + prestacion, para que C-10 lo consuma. Sin esto, C-10 no tiene gancho.
2. Idempotencia de cancelar: doble clic / doble mensaje WhatsApp / reintento no deben generar doble oferta a lista ni doble movimiento de sena. C-07 hoy exige idempotency solo en creacion; pedirla tambien en cancelar (segundo POST sobre turno ya `cancelado` = 200 idempotente con el mismo resultado, no error, no re-disparo).
3. `reprogramado` vs `cancelado`: reprogramar marca el original `reprogramado` (no `cancelado`) y crea/vincula el nuevo; cancelar es terminal. Esto preserva trazabilidad y evita que una reprogramacion dispare dos veces la lista de espera.
4. Motivo + auditoria minima en cancelar (quien/cuando/motivo/canal: mostrador vs publico), aunque la vista consultable llegue en C-13. Sin motivo, la auditoria de cancelaciones no sirve al dueno.
5. Permisos explicitos: recepcion y dueno cancelan; odontologo solo los propios (o ninguno si asi se decide); paciente solo via token vigente (C-08). Registrarlo en la matriz RBAC de C-07.
6. Dinero fuera de C-07: C-07 valida y cambia estado, pero el destino de la sena lo ejecuta C-12. C-07 deja el hook (turno.cancelado + senia_id pendiente de resolucion), no implementa devoluciones.
7. Distinguir `ausente` (no libera a lista, alimenta score futuro) de `cancelado` (si libera). Y distinguir cancelacion manual de liberacion por timeout de pago pendiente (C-08, 30 min): son dos productores del mismo evento con distinto motivo.

Si alguna de estas siete piezas se implementa a medias, el sintoma sera: hueco liberado que nadie ofrece (C-10 ciego), o hueco ofrecido dos veces (doble disparo), o sena movida dos veces (dinero). Por eso la recomendacion es endurecer C-07, no partir el tema.

---

## 5. Riesgos y unknowns (grounded en R1-R14 + KB)

- R1/R2 (tenant): toda query de cancelacion y del motor de lista debe filtrar por `tenant_id` del JWT; el token publico de C-08 debe resolver tenant sin confiar en el frontend. Un olvido = un consultorio cancela/ofrece turnos de otro. Critico.
- R9 (error trazable): fuera de `RN-AG-01` faltan codigos para "ya cancelado", "turno presente/ausente no cancelable", "token vencido" (esto ultimo en C-08). Definirlos en C-07 o se improvisan en codigo.
- R5 (dinero en centavos enteros) + R8 (idempotencia webhooks): el destino de la sena al cancelar (C-12) debe ser idempotente por `mp_payment_id`/evento unico. Cancelar dos veces no debe mover plata dos veces.
- R7 (timestamptz UTC): la comparacion "antelacion" debe hacerse en UTC contra `inicio` timestamptz, mostrando al usuario hora `America/Argentina/Buenos_Aires`. Mezclar zonas = regla 24h aplicada mal en el borde.
- R11 (TDD, 2 casos por comportamiento): casos minimos de cancelar: en termino libera; fuera de termino bloquea con `RN-AG-01`; doble cancel idempotente; reprogramar no duplica oferta; sin opt-in se salta con motivo.
- Condicion de carrera: dos recepcionistas cancelan/reprograman el mismo turno, o un paciente cancela por WhatsApp mientras recepcion reprograma. Mitigacion prevista en C-07 (validacion app + indice + idempotency): extenderla a cancelar, no solo a crear.
- RN-GL-03: si WhatsApp cae al avisar la cancelacion o al ofrecer a lista, la cancelacion local igual se completa; el envio queda `encolada` con reintento. No bloquear la agenda por el proveedor (depende de ADR-001/PA-01 en C-01).
- Spam de lista (PA-06): un solo `ofrecida` por hueco a la vez + auditoria de transiciones; si no, el motor ofrece en bucle.
- PA-04 (24h igual para primera visita con sena que para control?): hoy la config es un unico entero por tenant. Si se quieren ventanas por prestacion, C-06/C-07 deben modelarlo; si no, documentar "unico valor v1" como decision.
- PA-05 (devolucion: solo saldo a favor o devolucion MP real?): determina cuanto hace C-12 al cancelar. Default propuesto: saldo a favor / se pierde. Validar antes del Sprint 2.
- PA-08 (timeout 30 min pago pendiente): es el otro productor de "hueco libre". Confirmar default y que sea configurable.
- Datos sinteticos (R14): probar cancelaciones con pacientes/turnos demo, nunca reales.

---

## 6. Preguntas abiertas para el usuario (una a la vez en conversacion; aqui en lista para el archivo)

1. Motivo de cancelacion: obligatorio u opcional? (Mi recomendacion: obligatorio en mostrador con lista corta + libre; opcional en publico. Desbloquea auditoria util y metricas de ausentismo.)
2. Quien puede cancelar que?: confirma que odontologo NO cancela agenda ajena y que recepcion cancela cualquiera? (Desbloquea matriz RBAC de C-07.)
3. Reprogramar dentro de C-07 o diferida?: C-07 la promete con arrastre ejecutado en C-12. Confirmas ese split (C-07 cambia estados, C-12 mueve sena), o quieres reprogramar completa recien en C-12?
4. Idempotencia de cancelar: aceptas "segundo POST = 200 mismo estado, sin re-disparar lista ni sena"? (Desbloquea doble-clic/WhatsApp.)
5. Evento HuecoLiberado: aceptas agregarlo como criterio de aceptacion de C-07 (aunque el consumidor llegue en C-10)? Es la pieza que hace o rompe la lista automatica.
6. PA-04: 24h unico por tenant en v1, o ventanas por prestacion desde el dia 1? (Afecta modelo `Config` en C-06.)
7. PA-05: al cancelar en termino con sena, saldo a favor basta en v1? (Afecta C-12, no C-07.)
8. `ausente` quien lo marca y cuando?: al cierre del dia por recepcion, o job automatico? (Si nadie lo marca, la distincion ausente/cancelado se pierde.)
9. Cancelacion masiva (profesional enfermo, feriado) en v1 o backlog? (Si entra en v1, C-07 crece mucho; recomiendo dejarla fuera y registrarla como backlog.)

Detenerse aqui esta bien: con las respuestas 1-5 alcanza para proponer C-07 endurecido. Las 6-9 pueden diferirse a C-06/C-12/C-10 sin bloquear.

---

## 7. Next step recomendado (sin crear change ahora)

**Plegar en C-07. NO hacer `openspec new change`.**

Cuando estes listo, el comando es:

```
/opsx:propose C-07-turnos-agenda-interna
```

con esta enmienda de alcance agregada a la propuesta (copiar/pegar):

- C-07 incluye cancelacion mostrador completa (validar RN-AG-01/02, estados, idempotencia de cancelar, motivo + auditoria, permisos por rol, error `RN-AG-01` + oferta de reprogramar, hueco visible).
- C-07 expone el contrato `HuecoLiberado` (turno-id, profesional, rango, prestacion, motivo) que consumira C-10; no implementa el motor de oferta.
- C-07 NO implementa dinero (hook a C-12) ni envios (hook a C-09); ambos son consumidores, no parte del criterio de aceptacion de C-07 salvo "deja el gancho + test del gancho".
- C-08/C-09/C-10/C-12 referencian ese contrato sin duplicarlo.

Alternativa descartada: change nuevo `cancelar-turnos` entre C-07 y C-10. Se descarta porque duplica C-07 (base) y vacia C-10 (motor), alarga el camino critico y mezcla gobernanzas. Solo reconsiderarla si el equipo decide adelantar "cancelar + lista" como un vertical antes que la agenda completa, lo cual contradice el GATE 4 (C-07 exige C-04 + C-06) y no se recomienda.

---

## 8. Trazabilidad (para el propose de C-07)

- Reglas: RN-AG-01, RN-AG-02, RN-AG-05 (hook), RN-CO-03 (hook C-12), RN-GL-01, RN-GL-02, RN-GL-03, RN-PA-01, RN-AU-01.
- Historias: US-001 (invariante solape), US-004 (CA-1/2/3), US-005 (consumidor C-10), US-002 (puerta publica C-08), US-003/US-007 (consumidores C-09/C-12).
- Flujos: Flujo 2 pasos 1-5 + errores; Flujo 1 (timeout 30 min como segundo productor, PA-08).
- Modelo: `turno` (estados, token_publico, senia_id, origen) + `lista_espera` (estados) + `config.antelacion_cancel_hs`.
- Hard rules aplicables: R1, R2, R3 (DTOs, no exponer Turno ORM), R4 (`extra='forbid'`), R5 (centavos, solo C-12), R6 (migracion reversible), R7 (UTC), R8 (idempotencia), R9 (code RN-XX), R11 (TDD 2 casos), R13 (gobernanza ALTA), R14 (datos sinteticos).
- Preguntas que bloquean C-07: 1-5 de seccion 6. Preguntas diferibles: PA-04/PA-05/PA-06/PA-08.
