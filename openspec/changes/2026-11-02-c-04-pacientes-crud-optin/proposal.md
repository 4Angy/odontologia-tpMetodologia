# Proposal

## Why

El backend ya contiene un slice sustancial de pacientes, opt-ins, importación y exportación CSV, pero el alcance C-04 sigue pendiente y la experiencia React continúa siendo un placeholder. Hay que cerrar y validar el contrato existente sin duplicar lo ya construido, para que recepción pueda operar pacientes de forma segura antes de C-05, C-07, C-09 y C-11.

## What Changes

- Completar y validar el CRUD tenant-scoped de pacientes y la gestión de opt-ins (RN-PA-01/02): cambiar el teléfono revoca el opt-in WhatsApp y requiere consentimiento nuevo, e invalida referencias asociadas al número anterior mediante la integración con C-09.
- Cerrar los gaps del importador CSV y del reporte fila por fila; exportar pacientes en CSV. La exportación de turnos/cobros pertenece a C-07/C-11 y se conectará por su owner cuando esos dominios estén disponibles.
- Reemplazar el placeholder de `/pacientes` por lista, búsqueda, alta, detalle y gestión visible de opt-ins/importación, con pruebas frontend.
- Aplicar baja lógica a pacientes; bloquear el borrado destructivo cuando exista historia clínica o financiera. La supresión de esos datos se tramita mediante un proceso separado.
- Conservar los endpoints, modelos y la migración `004_pacientes_optin` existentes; no recrearlos. Añadir migración reversible solo si el análisis de gaps demuestra que el esquema actual no alcanza.
- El alcance de exportación de C-04 es CSV de pacientes; no implementar exportación de turnos/cobros ni otros formatos en este change.

## Capabilities

### New Capabilities

- `pacientes/gestion-pacientes`: ficha identificatoria, opt-ins, importación y exportación de pacientes con aislamiento por tenant.

### Modified Capabilities

Ninguna.

## Impact

- Backend existente: `backend/app/modules/pacientes/` y `backend/alembic/versions/004_pacientes_optin.py`.
- Frontend React: `frontend/src/pages/index.tsx`, nuevas vistas/estado/API bajo `frontend/src/features/pacientes/`; actualmente solo existe el placeholder.
- Pruebas backend y frontend, contratos API y posible integración futura con los recursos de C-07/C-11.
- Dependencia funcional: C-03. C-04 precede a C-05; no depende de C-05 ni de C-06.
- Datos personales y potencialmente vinculados a salud: gobernanza elevada, minimización y datos sintéticos exclusivamente en desarrollo/pruebas.
