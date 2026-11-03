# Design

## Context

Ver `proposal.md` y `specs/pacientes/gestion-pacientes/spec.md`. El backend existente ya ofrece CRUD de pacientes, búsqueda por nombre/apellido/DNI/teléfono, upsert/lista de opt-ins, importación por CSV y exportación de pacientes. La migración `004_pacientes_optin.py` crea pacientes y opt-ins con `downgrade`; los tests actuales cubren flujos básicos de API y aislamiento de lectura/lista. En cambio, la UI de `/pacientes` es un placeholder.

Gaps observados en el código:
- El reporte CSV devuelve contadores, no detalle por fila; captura excepciones genéricas y el contrato de importación requiere pruebas de duplicados intra-archivo, fallos y rollback/aislamiento por fila.
- El cambio de teléfono no invalida estado asociado al número anterior. No hay todavía modelos de tokens o mensajes pendientes; C-09 será dueño de los envíos.
- `exportar_csv` implementa pacientes, mientras turnos/cobros responden `501`; estos recursos pertenecen a cambios posteriores.
- No se encontró una bitácora de auditoría de actor/acción: `AuditMixin` conserva timestamps, no quién cambió qué.
- El endpoint de borrado y relaciones ORM pueden eliminar historia relacionada en cascada cuando C-05 está presente; la política de retención no está definida.
- React solo muestra el placeholder; sí existen rutas protegidas, cliente HTTP y pruebas Vitest.

## Goals / Non-Goals

**Goals:**
- Cerrar los comportamientos faltantes y validar los ya implementados, dando prioridad a privacidad, tenancy, opt-in, importación/exportación y UI.
- Mantener interfaces HTTP y modelos actuales cuando ya cumplen el contrato; no volver a crear CRUD ni la revisión 004.
- Dejar explícita la coordinación de exportación con los dominios que llegan después.

**Non-Goals:**
- Implementar evoluciones, adjuntos clínicos, presupuestos, turnos completos, cobros o notificaciones; son C-05/C-07/C-09/C-11.
- Elegir texto legal, retención clínica o una política de consentimientos que no esté acordada.
- Añadir Excel/PDF como interpretación implícita de la exportación CSV declarada en CHANGES.md.

## Decisions

1. **Cerrar el slice existente mediante inventario de gaps, no reemplazarlo.** Se conserva `PacienteService`, los DTOs, repositorios y migración 004 salvo cambios necesarios para cumplir requisitos. Una prueba de contrato/regresión precede a cada cambio. Rehacer el módulo completo duplicaría comportamiento probado y elevaría el riesgo de pérdida o fuga de datos.

2. **El JWT validado es la única fuente de tenant.** Cada query/mutación usa `tenant_id` del contexto autenticado; no se acepta tenant en DTOs ni se devuelve un recurso cross-tenant. Las respuestas siguen siendo DTOs Pydantic estrictos (`extra='forbid'`), y las búsquedas/exportaciones mantienen filtros tenant-scoped. No se exponen modelos ORM.

3. **La importación produce resultados por fila.** El contrato conservará el resumen actual y agregará suficientes datos de fila/resultado para localizar duplicados y errores. La estrategia de persistencia debe permitir que un registro inválido no deje la transacción inutilizable ni oculte filas omitidas; se validan primero encabezados, campos y teléfono, y se cubren duplicados tanto contra la base del tenant como dentro del archivo. Acuerdo de producto: UTF-8 con o sin BOM, máximo 5 MiB y 5.000 filas de datos; `nombre` y `apellido` son obligatorios, `dni`, `telefono` y `email` opcionales, sin columnas desconocidas.

4. **Cambiar el teléfono revoca el opt-in y requiere consentimiento nuevo.** La actualización del teléfono revoca el opt-in WhatsApp; el número nuevo no queda consentido por herencia. La evidencia registra canal, actor, instante UTC y versión del texto presentado, sin afirmar validez o cumplimiento legal. No hay tokens de paciente bajo control de C-04/C-08 en el runtime actual. Para C-09, la misma transacción guarda `paciente.telefono_cambiado` en `audit_event`, junto con el tenant, paciente y SHA-256 del teléfono anterior; el worker compara el hash con el destino de sus trabajos pendientes y los invalida antes del envío. C-04 no crea ni simula ese worker.

5. **La eliminación operativa es baja lógica; la supresión es separada.** La operación de eliminación marca al paciente como dado de baja y conserva sus datos. Si existe historia clínica o financiera, se bloquea cualquier borrado destructivo y no se ejecutan cascadas. La eventual supresión de esos datos requiere un proceso separado, con sus controles de retención y autorización; no se realiza silenciosamente desde el CRUD.

6. **Exportación CSV de pacientes en C-04; otros dominios en sus owners.** C-04 entrega pacientes tenant-scoped en CSV. La exportación de turnos y cobros pertenece a C-07/C-11 y se conectará mediante sus owners cuando esos recursos estén disponibles; C-04 no implementa ni anuncia esos exports ni crea abstracciones dependientes de tablas inexistentes. No se amplía el formato más allá del CSV de pacientes en este change.

7. **Auditoría de mutaciones es transaccional.** `created_at`/`updated_at` no satisfacen RN-GL-02 por sí solos. Como no existe infraestructura previa, C-04 incorpora `audit_event` compartida con autor, tenant, acción, recurso/identificador, instante UTC, nombres de campos modificados y metadatos técnicos mínimos. La mutación no se confirma si la auditoría asociada falla. No se guardan valores de contacto o clínicos en la auditoría; los errores inesperados registran solo el tipo de excepción.

8. **RBAC y experiencia de interfaz siguen `03_actores_y_roles.md`.** Acuerdo de producto: recepción y dueño administran datos de contacto y opt-ins; odontología tiene lectura de pacientes. La interfaz React tipada reemplaza el placeholder y cubre búsqueda, alta, detalle, opt-in e importación con reporte; se prueban estados de carga, error y vacío.

9. **Compatibilidad de migraciones.** La revisión 004 ya está presente y no se modifica retroactivamente. La revisión 007 agrega evidencia de consentimiento y la auditoría compartida sobre el head 006, con `downgrade`. El downgrade estructural no se usa como estrategia de recuperación de datos de producción.

10. **Reglas duras aplicables (R1–R14).**
   - R1–R2: aislamiento en toda query de negocio; tenant solo del JWT, nunca del frontend.
   - R3–R4: DTOs Pydantic v2, nada de ORM en API y `extra='forbid'`.
   - R5–R7: importes en centavos enteros; migraciones siempre reversibles; datetimes aware/UTC.
   - R8–R9: webhook futuro siempre idempotente; errores de negocio con `code` RN trazable.
   - R10: TypeScript estricto, sin `any` explícito y componentes PascalCase.
   - R11: TDD estricto: test en rojo antes del código y al menos dos casos por comportamiento.
   - R12: sin commit/push sin pedido explícito.
   - R13: datos personales/clínicos bajo gobernanza elevada; análisis y propuesta antes de implementar, sin atajos.
   - R14: fixtures, pruebas y seeds solo sintéticos/demo; nunca datos reales sensibles.

## Risks / Trade-offs

- [Consentimiento no probado] La evidencia técnica (canal, actor, instante UTC y versión del texto presentado) no acredita por sí sola el origen ni la suficiencia legal del consentimiento; no declarar conformidad legal.
- [Borrado en cascada] La implementación ORM actual puede eliminar relaciones clínicas → la baja lógica conserva datos y el borrado destructivo con historia se bloquea; la supresión queda fuera del CRUD y requiere proceso separado.
- [Portabilidad por dominios] C-04 solo exporta pacientes en CSV → C-07/C-11 son owners de turnos/cobros y deberán conectarse por su owner; no presentar C-04 como exportación total.
- [CSV hostil o inválido] Tamaño/campos y errores malformados pueden consumir recursos o producir importación parcial → acordar límites, validar encoding/headers y probar archivos adversos sin datos reales.
- [Riesgo salud/PII] Los datos de identificación y opt-in son sensibles → minimización, acceso RBAC, auditoría sin volcar datos clínicos y gobernanza HIGH; C-05 sube a CRITICAL/HIGH por contenido clínico.

## Migration Plan

1. Confirmar detalles aún abiertos de evidencia de consentimiento, importación y permisos de opt-in; la política de baja y el ownership/formato de exportación de C-04 ya están definidos.
2. Probar primero contratos y fallos en backend/frontend con datos sintéticos.
3. Reutilizar la migración 004 si no se requieren campos; si se requieren, crear migración aditiva reversible sobre el head Alembic actual y revisar el efecto sobre C-05/C-06.
4. Verificar upgrade/downgrade en base descartable. No ejecutar downgrade en datos de pacientes de producción sin estrategia aprobada de backup/recuperación.

## Open Questions

- ¿Qué evidencia del consentimiento explícito (por ejemplo, origen, instante y versión del texto) debe persistirse, además del estado de opt-in?
- ¿Qué tamaño/tipo de archivo y política de encoding/headers se acepta para importación CSV?
- ¿Qué roles pueden administrar opt-ins y qué reporte de errores por fila es suficiente sin exponer más datos personales?
