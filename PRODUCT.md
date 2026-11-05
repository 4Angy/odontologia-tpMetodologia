# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Recepción agenda turnos y gestiona la jornada; odontología consulta sus propios turnos y la ficha del paciente; el dueño supervisa la caja y la operación. En consultorios pequeños una persona puede acumular varios roles. El paciente reserva y gestiona turnos desde un enlace público sin crear una cuenta.

## Product Purpose

SaaS multi-tenant para consultorios odontológicos pequeños de Argentina que reemplaza la coordinación dispersa por WhatsApp y papel con una cadena de trabajo para agendar, atender y cobrar. El éxito incluye reducir ausencias, ocupar la agenda y permitir que un consultorio empiece a operar el mismo día del alta.

## Positioning

La propuesta de v1 prioriza gestión operativa, cobros simples, señas con una regla de cancelación clara, lista de espera y transparencia de costos, en vez de competir por profundidad clínica. El odontograma completo y la facturación electrónica quedan fuera de v1.

## Operating Context

La recepción suele organizar la agenda diaria entre varias personas profesionales, confirmaciones, cancelaciones y horarios que deben recuperarse. El sistema se usa como aplicación web autenticada; los pacientes externos acceden a una reserva pública y pueden operar desde enlaces compartidos.

## Capabilities and Constraints

- La agenda interna ofrece vistas de día y semana, profesionales múltiples, duración por prestación, bloqueos, sobreturnos explícitos y prevención de colisiones.
- La reserva pública, los recordatorios y las confirmaciones reducen trabajo manual y ausencias.
- El producto incluye ficha de paciente y HCE mínima, presupuestos simples y caja manual; no incluye odontograma completo, obras sociales ni facturación electrónica en v1.
- Los roles son acumulables y un usuario puede desempeñar más de una función.
- Los datos de negocio están aislados por consultorio; datos reales sensibles de pacientes no se usan en desarrollo ni pruebas.

## Evidence on Hand

La visión, roles y funcionalidades están documentados en `knowledge-base/01_vision_y_objetivos.md`, `knowledge-base/03_actores_y_roles.md` y `knowledge-base/06_funcionalidades.md`. No se proporcionaron testimonios, métricas observadas, logotipo ni activos de marca aprobados.

## Product Principles

- Reducir ausencias y huecos operativos con una agenda confiable.
- Hacer que las reglas de negocio sean explícitas y auditables.
- Respetar el aislamiento entre consultorios y limitar la exposición de datos.
- Mantener transparencia sobre capacidades, costos y límites del producto.
- Permitir que equipos pequeños operen con roles acumulables.

## Accessibility & Inclusion

La agenda debe poder operarse con controles etiquetados, mensajes de error visibles y textos en español rioplatense. No se estableció una norma de accesibilidad específica.
