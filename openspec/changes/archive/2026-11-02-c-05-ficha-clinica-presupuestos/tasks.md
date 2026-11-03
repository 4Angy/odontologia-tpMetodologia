# Tasks

## 1. Gate de dependencia, decisiones y pruebas rojas

- [x] 1.1 Iniciar C-05 solo después de completar C-04; verificar que la ficha base, sus permisos tenant-scoped y su política de borrado estén disponibles sin recrear pacientes.
- [x] 1.2 Armonizar RN-CO-05 con la fórmula de saldo aprobada antes de aplicar; resolver los detalles aún abiertos de vínculo profesional-usuario, interacción de la UI con adjuntos, auditoría común, estados adicionales de presupuesto y retención. No reabrir el contrato ADR-003, el formato/tamaño/tipo de adjuntos ni la fórmula de saldo ya acordados.
- [x] 1.3 Crear pruebas rojas de contrato para ADR-003, timeline UTC, RBAC, aislamiento cross-tenant, auditoría, lectura de adjuntos y CRUD presupuestos; comprobar como mínimo dos casos por comportamiento y utilizar únicamente datos clínicos sintéticos (R11/R14).

## 2. Evoluciones y compatibilidad FDI

- [x] 2.1 Completar el modelo/API exactamente con ADR-003: `profesional_id`, `fecha` almacenada en UTC, `pieza_fdi_slot` y `pieza_fdi_numero` ambos presentes o ausentes, `odontograma_ref` nullable, `firma_simple` y `firmado_at`; verificar DTO estricto, autoría autenticada y timestamps aware/UTC (R1–R4/R7).
- [x] 2.2 Implementar listado cronológico y permisos de evoluciones según matriz de actores; probar acceso positivo de odontólogo/dueño, denegación de recepción y ocultamiento cross-tenant.
- [x] 2.3 Añadir el mecanismo de auditoría aprobado para creación/edición clínica; probar actor, instante UTC, diff permitido, atomicidad y que el contenido clínico no se vuelca a logs (RN-GL-02/R13).
- [x] 2.4 Crear una migración forward sobre el head real que preserve filas existentes y complete exactamente ADR-003; no editar 005. Probar upgrade/downgrade estructural, ancla completa o ausente, proyección sin pérdida e idempotencia (R6).

## 3. Adjuntos clínicos

- [x] 3.1 Escribir pruebas rojas de carga, límite de 10 MiB, JPEG/PNG/PDF y validación de tipo real, asociación tenant/paciente, lectura y denegación; verificar dos casos por comportamiento sin archivos ni datos reales (R11/R14).
- [x] 3.2 Implementar almacenamiento cifrado y privado compatible con S3, aceptar solo JPEG/PNG/PDF hasta 10 MiB tras validar contenido real, y emitir URLs firmadas de corta duración sin fijar proveedor; probar tamaños/tipos permitidos y rechazados, autorización y rechazo de URLs libres no confiables.
- [x] 3.3 Implementar la vista de adjuntos en ficha con estados de carga/error y autorización; comprobar tests Vitest y que no se filtran enlaces/metadata de otro tenant.

## 4. Presupuestos y saldo

- [x] 4.1 Antes de aplicar, armonizar explícitamente la redacción de RN-CO-05 con la fórmula aprobada: borradores no computan; aprobados/aceptados contribuyen menos cobros/créditos aplicados por C-11. No editar la KB en este alcance ni exponer saldo editable.
- [x] 4.2 Añadir pruebas rojas de creación, listado, edición, eliminación, estados, totales y saldo derivado; cubrir borrador, aprobado/aceptado, centavos enteros, importes límite, permisos y aislamiento (R1/R5/R11).
- [x] 4.3 Completar CRUD de presupuestos/ítems y gestión de estados sin aceptar saldo desde la API; comprobar atomicidad y que C-11 es quien integra cobros/créditos aplicados al saldo derivado.
- [x] 4.4 Añadir vista de presupuestos y saldo a la ficha conforme a roles; verificar totales en centavos, estados y errores mediante Vitest/typecheck.

## 5. Integración de ficha y verificación

- [x] 5.1 Reemplazar el placeholder por ficha integrada con timeline, adjuntos y presupuestos; verificar navegación desde detalle del paciente, autorización por rol y estados vacíos/cargando/error.
- [x] 5.2 Ejecutar tests backend del módulo pacientes y tests/build/typecheck frontend; verificar tenant isolation, RBAC, UTC aware, DTOs strict, contrato ADR-003, auditoría atómica, adjuntos validados/cifrados y monto entero/saldo derivado (R1–R14).
- [x] 5.3 Revisar documentación contractual, notas legales de firma simple (no firma digital Ley 25.506), retención y uso de datos sintéticos; verificar que el alcance de odontograma v2 permanece fuera de C-05.
