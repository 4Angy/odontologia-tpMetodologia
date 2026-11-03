# Proposal

## Why

El backend ya define evoluciones, adjuntos y presupuestos, con creación y lecturas parciales; sin embargo, no hay una ficha clínica usable en el frontend, el CRUD de presupuestos no está completo y la auditoría/derivación del saldo necesitan validación antes de manejar información clínica. Completar C-05 permite registrar la atención con alcance legal honesto, sin reconstruir el slice existente ni adelantar el odontograma v2.

## What Changes

- Completar y validar timeline clínico conforme exactamente a ADR-003 (`profesional_id`, `fecha` UTC, `pieza_fdi_slot` y `pieza_fdi_numero` presentes juntos o ausentes, `odontograma_ref` nullable, `firma_simple` y `firmado_at`), adjuntos privados y CRUD/estados de presupuestos sobre los modelos/endpoints existentes.
- Construir la ficha integrada de paciente en React, incluyendo evoluciones, adjuntos y presupuestos/saldo, con contratos tipados y sin `any`.
- Guardar adjuntos en almacenamiento privado cifrado compatible con S3, aceptar JPEG/PNG/PDF hasta 10 MiB con validación de tipo real y entregar URLs firmadas de corta duración sin fijar proveedor.
- Derivar el saldo: solo presupuestos aprobados/aceptados contribuyen deuda, menos cobros/créditos aplicados por C-11; ningún endpoint permite editar saldo. El presupuesto en borrador no afecta el saldo.
- Conservar la migración reversible `005_ficha_clinica_presupuestos`; completar el contrato ADR-003 mediante una migración forward, sin editar 005 ni recrear tablas.
- Mantener fuera el odontograma/periodontograma, la firma digital Ley 25.506, cobros y comprobantes fiscales. C-11 integra cobros/créditos aplicados al saldo; C-05 no implementa cobros.
- Antes de aplicar, armonizar la regla RN-CO-05 con esta fórmula aprobada; no cambiar la KB en este alcance.

## Capabilities

### New Capabilities

- `pacientes/ficha-clinica`: acceso tenant-scoped a evoluciones, adjuntos y presupuestos de la ficha clínica mínima.

### Modified Capabilities

Ninguna.

## Impact

- Backend existente: `backend/app/modules/pacientes/` y `backend/alembic/versions/005_ficha_clinica_presupuestos.py`.
- Frontend React: placeholder actual en `frontend/src/pages/index.tsx`; nueva ficha integrada bajo `frontend/src/features/pacientes/`.
- Pruebas de API, dominio, aislamiento, auditoría y UI; la selección de proveedor concreto de almacenamiento permanece abierta mientras cumpla el contrato privado compatible con S3.
- Dependencia: C-04 debe preceder a C-05 para la identidad y navegación del paciente. C-05 no depende de C-06.
- Gobernanza CRITICAL/HIGH por datos de salud: minimización, control de acceso, auditabilidad y fixtures/seeds solo sintéticos; adecuación legal final sigue requiriendo revisión especializada.
