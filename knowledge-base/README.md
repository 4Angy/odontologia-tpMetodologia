# Consultorio Odontológico SaaS — Base de Conocimiento

Base de conocimiento generada en Modo B (discovery por Q&A ya completado por el orquestador — sin preguntas nuevas) a partir de `discovery/discovery.md` (11 puntos gate-confirmados) y `discovery/analisis-competitivo.md` (15 sistemas, matriz ponderada, vacíos C.3 y apuestas C.4).

## Índice de Archivos

| Archivo | Contenido |
|---------|-----------|
| [01_vision_y_objetivos.md](01_vision_y_objetivos.md) | Propósito, objetivos por actor (3-roles-1-persona), alcance v1, fuera de v1, métricas |
| [02_descripcion_general.md](02_descripcion_general.md) | Stack FastAPI+React+Postgres+Redis+Docker, arquitectura multi-tenant, integraciones, API REST |
| [03_actores_y_roles.md](03_actores_y_roles.md) | 5 actores, RBAC recepción/odontólogo/dueño acumulables, rutas públicas |
| [04_modelo_de_datos.md](04_modelo_de_datos.md) | 5 dominios, ERD, 12 entidades, seed demo |
| [05_reglas_de_negocio.md](05_reglas_de_negocio.md) | 20 reglas RN-AG/RN-PA/RN-CO/RN-AU/RN-GL (24h configurable RN-AG-01/02) |
| [06_funcionalidades.md](06_funcionalidades.md) | 12 US en 5 épicas v1 + Épica 6 backlog v2+ (odontograma, OS, ARCA) |
| [07_flujos_principales.md](07_flujos_principales.md) | Reserva con seña, cancelación+lista de espera, atención mínima, auth multi-rol, worker recordatorios |
| [08_arquitectura_propuesta.md](08_arquitectura_propuesta.md) | Patrones (filtro: costo operativo bajo), layout monolito modular, seguridad, 13 env vars |
| [09_decisiones_y_supuestos.md](09_decisiones_y_supuestos.md) | 6 decisiones DD + 4 supuestos SU (R1, caja-manual, 3-roles-1-persona, tiers gratuitos) |
| [10_preguntas_abiertas.md](10_preguntas_abiertas.md) | 2 inconsistencias + 8 preguntas (PA-01 WhatsApp, PA-02 facturación, PA-03 Dental Manager/MednIA) |

## Quick Start para Desarrolladores

1. Entender el dominio → [01](01_vision_y_objetivos.md), [03](03_actores_y_roles.md)
2. Entender los datos → [04](04_modelo_de_datos.md)
3. Entender las reglas → [05](05_reglas_de_negocio.md)
4. Entender la arquitectura → [02](02_descripcion_general.md), [08](08_arquitectura_propuesta.md)
5. Implementar → [07](07_flujos_principales.md), [06](06_funcionalidades.md)
6. Antes de codificar → [10](10_preguntas_abiertas.md)

## Resumen Ejecutivo

SaaS multi-tenant (un tenant por consultorio) para consultorios odontológicos chicos que pierden plata por ausentismo: agenda con recordatorios WhatsApp, caja manual con seña por Mercado Pago y regla de cancelación 24h configurable, más lista de espera automática y transparencia radical como diferenciadores frente a 15 competidores que todos tienen odontograma (riesgo R1 asumido: v1 sale sin él). Stack: FastAPI + React + Postgres + Redis + Docker; 3 decisiones abiertas bloquean Sprint 1 (WhatsApp oficial vs artesanal, alcance de facturación, Dental Manager/MednIA).
