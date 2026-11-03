# Tasks

## 1. Decisiones y caracterización del slice existente

- [ ] 1.1 Acordar únicamente los detalles aún abiertos de evidencia de consentimiento, roles que administran opt-ins y límites/encoding/headers de importación; preservar los acuerdos ya fijados de cambio de teléfono, baja lógica/supresión separada y ownership/formato de exportación.
- [ ] 1.2 Añadir pruebas de caracterización del CRUD, búsqueda, DTO estricto, E.164, opt-ins, aislamiento, importación y exportación ya implementados; ejecutar pytest de pacientes y verificar que la base existente pasa antes de cambiar código (R11).
- [ ] 1.3 Diseñar pruebas rojas por cada gap aprobado, con al menos dos casos por comportamiento (éxito y límite/error); verificar fallos iniciales esperados y usar solo pacientes sintéticos (R11/R14).

## 2. Backend pacientes, opt-ins e importación/exportación

- [ ] 2.1 Cerrar CRUD/RBAC/búsqueda solo según matriz aprobada; probar lectura/escritura por cada rol, ID cross-tenant idéntico a inexistente y rechazo de `tenant_id`/campos extras antes de aceptar la implementación (R1–R4).
- [ ] 2.2 Completar validación E.164 y cambio de teléfono: revocar opt-in WhatsApp, requerir consentimiento explícito nuevo e invalidar tokens bajo control de C-04. Coordinar con C-09 el contrato para invalidar trabajos dirigidos al número anterior, sin implementar ni simular su worker.
- [ ] 2.3 Completar importación CSV con reporte por fila, deduplicación tenant-scoped y fallos aislados; verificar encabezado/encoding acordados, duplicados intra-archivo, filas inválidas y que no queden transacciones parciales ocultas.
- [ ] 2.4 Completar y validar exportación CSV de pacientes; probar descarga con solo registros del tenant y campos definidos. Mantener turnos/cobros fuera de C-04 y documentar su ownership en C-07/C-11 para conectarlos cuando esos dominios estén disponibles.
- [ ] 2.5 Implementar auditoría de mutaciones paciente/opt-in con actor, tenant, acción, instante UTC y cambio permitido; probar atomicidad, lectura autorizada por dueño y ausencia de valores clínicos en logs (RN-GL-02/R7).
- [ ] 2.6 Implementar baja lógica sin eliminación física de datos; bloquear borrado destructivo cuando exista historia clínica/financiera y no ejecutar cascadas. Probar paciente sin historia y con dependencias; mantener cualquier supresión en proceso separado.

## 3. Interfaz de pacientes

- [ ] 3.1 Crear pruebas Vitest en rojo para lista/búsqueda, carga/edición, detalle y estados vacío/cargando/error; verificar tipos estrictos y renderizado de respuestas/errores del API antes de construir las vistas (R10/R11).
- [ ] 3.2 Reemplazar placeholder por lista y alta/detalle/edición con API tipada, búsqueda por apellido/teléfono/DNI y permisos aprobados; comprobar con tests UI y `npm run typecheck` sin `any`.
- [ ] 3.3 Añadir gestión visible de opt-in, revocación al cambiar teléfono, exigencia de consentimiento nuevo y feedback de validación; probar activación/revocación e integración de invalidación con C-09.
- [ ] 3.4 Añadir importación con reporte por fila y exportación permitida; verificar accesibilidad básica, descarga y que errores/contadores no expongan datos de otro tenant.

## 4. Esquema y verificación integrada

- [ ] 4.1 Determinar si se requieren cambios de esquema para auditoría/evidencia de consentimiento; si se requieren, crear migración Alembic forward con `downgrade` sobre el head real y verificar upgrade/downgrade en base descartable sin editar 004 ya existente (R6).
- [ ] 4.2 Ejecutar suite backend de pacientes y pruebas frontend (`pytest` del módulo; `npm test` y `npm run build` en frontend); verificar tenancy, RBAC, contratos strict, UTC, reportes CSV, TDD y uso exclusivo de fixtures sintéticos (R1–R14).
- [ ] 4.3 Revisar documentación/contratos de exportación CSV de pacientes, consentimiento y baja/supresión; verificar que los exports de turnos/cobros sean atribuidos a C-07/C-11 y no se anuncien como disponibles desde C-04.
