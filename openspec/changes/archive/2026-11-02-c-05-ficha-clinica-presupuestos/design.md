# Design

## Context

Ver `proposal.md` y `specs/pacientes/ficha-clinica/spec.md`. Ya existen modelos, DTOs `extra='forbid'`, servicios y endpoints para crear/listar evoluciones, crear adjuntos como metadatos y crear/listar presupuestos; la revisión Alembic `005_ficha_clinica_presupuestos.py` crea las tablas con `downgrade`. El test actual cubre creación básica, suma de presupuesto, cambio de saldo y rechazo por tamaño fijo de 10 MB.

Gaps observados:
- No existe UI de ficha clínica ni endpoint de lista de adjuntos.
- Presupuestos no tienen update/delete pese a que el roadmap declara CRUD.
- El límite de 10 MB está hardcodeado; el endpoint de adjunto acepta metadatos/URL, no un archivo binario, y no resuelve descarga o almacenamiento.
- El modelo de evolución actual usa `odontologo_id`, `created_at` y `firma_timestamp`, pero debe evolucionar exactamente al contrato ADR-003: `profesional_id`, `fecha`, `pieza_fdi_slot`, `pieza_fdi_numero`, `odontograma_ref`, `firma_simple` y `firmado_at`.
- El servicio incrementa `paciente.saldo` por el total del presupuesto; debe reemplazarse por saldo derivado, integrado con las aplicaciones de cobros/créditos de C-11.
- `AuditMixin` solo aporta timestamps; no se encontró bitácora actor/acción consultable.
- Los endpoints actuales autorizan en general a los tres roles, mientras `03_actores_y_roles.md` restringe evoluciones y presupuesto por rol.
- La UI de Pacientes sigue siendo placeholder. Las migraciones 004–006 ya existen y 006 es el head actual del chain.

## Goals / Non-Goals

**Goals:**
- Completar la ficha integrada sobre el slice existente y corregir divergencias contractuales antes de que haya registros clínicos reales.
- Conservar dato clínico trazable, tenant-scoped, auditable y proyectable conforme al contrato ADR-003.
- Implementar el contrato aprobado de adjuntos privados y saldo derivado, armonizando la redacción de RN-CO-05 antes de aplicar.

**Non-Goals:**
- Odontograma/periodontograma FDI v2, firma digital Ley 25.506, cobros/caja o comprobantes fiscales.
- Fijar proveedor concreto de almacenamiento, detalles de interacción de la interfaz, política de retención o estados adicionales no aprobados.
- Reescribir la migración 005 como si nunca se hubiese aplicado.

## Decisions

1. **Servicios de dominio como autoridad y routers delgados.** Extender los servicios existentes para reglas, permisos, transacciones y contratos; los routers solo validan DTOs estrictos, obtienen identidad y traducen errores de dominio. Alternativa descartada: añadir reglas directamente a endpoints, que permite inconsistencias entre vista, API y tests.

2. **Preservar exactamente ADR-003 con migración forward.** El contrato es `profesional_id`, `fecha` almacenada en UTC, `pieza_fdi_slot` y `pieza_fdi_numero` ambos presentes o ausentes, `odontograma_ref` nullable, `firma_simple` y `firmado_at`. La revisión 005 queda inmutable; una migración forward copia/transforma datos sin pérdida y completa ese contrato, con downgrade estructural. No crear odontograma ni asignar pieza por inferencia. Probar proyección sin pérdida e idempotencia.

3. **Permisos siguen la matriz de actores, no las autorizaciones amplias actuales.** Odontólogo registra/gestiona sus evoluciones; dueño puede consultarlas; recepción no accede al contenido clínico. Presupuestos permiten lectura de recepción y operaciones autorizadas de odontólogo/dueño según KB. La unión de roles continúa aplicando. Cualquier aclaración de qué significa "propias" debe fijar cómo se vincula una evolución con profesional/usuario, no confiar en un ID aportado por frontend.

4. **Auditoría explícita, ligada a la transacción.** Reutilizar `audit_event` con tenant, actor autenticado, recurso, acción, instante UTC y nombres de campos modificados; confirmar atómicamente con la mutación y permitir consulta tenant-scoped solo al dueño. No registrar valores clínicos ni el texto íntegro de evoluciones en logs, errores o auditoría. Timestamps del ORM no sustituyen RN-GL-02.

5. **Adjuntos en almacenamiento privado compatible con S3.** La UI envía el archivo al backend, que valida JPEG/PNG/PDF de hasta 10 MiB por contenido real y guarda en un bucket privado configurable usando cifrado del lado del almacenamiento. Las descargas autorizadas tenant-scoped se entregan mediante URLs firmadas de corta duración. No fijar proveedor ni aceptar URLs libres del cliente como prueba de archivo verificado.

6. **Saldo derivado y presupuesto CRUD integrado con C-11.** El total se calcula desde ítems en centavos, sin `float`. Un borrador no afecta deuda; solo presupuestos aprobados o aceptados contribuyen, restando cobros y créditos aplicados por C-11. El saldo se deriva y ningún endpoint lo edita. C-05 implementa CRUD para los estados `borrador`, `aprobado` y `aceptado`, sin cobros ni estados adicionales. Esta es la interpretación ejecutable de RN-CO-05 para el alcance C-05; no se modifica la KB ni se cambia su texto en este change.

7. **UI en features de React ya existentes.** Reemplazar el placeholder con ficha paciente y componentes accesibles para timeline, adjuntos y presupuestos; el cliente HTTP reusa el API común. Los datos UI usan tipos explícitos TypeScript, validan errores de API y no almacenan datos de salud innecesarios en persistencia local.

8. **Migración y rollback son estructurales, no borrado de datos reales.** No modificar 005 aplicada; nueva revisión con `down_revision` del head real al momento de implementación, identificador único y `downgrade` probado. Aclarar cómo preservar columnas/datos durante renombres y cómo migrar filas existentes de fixture. En producción, downgrade que elimine campos clínicos no se ejecuta sin backup y plan de recuperación; reversibilidad del esquema no autoriza pérdida de historias.

9. **TDD y reglas duras R1–R14.**
   - R1–R2: toda query de negocio tenant-scoped; tenant deriva del JWT validado, no de la UI.
   - R3–R4: API con DTOs Pydantic v2, nunca ORM; `extra='forbid'`.
   - R5–R7: montos centavos enteros; cada Alembic revision reversible; todo datetime aware/UTC.
   - R8–R9: cualquier webhook futuro idempotente; errores de negocio con `code` RN.
   - R10: TS estricto, sin `any`, componentes PascalCase.
   - R11: TDD estricto: test rojo antes de código y mínimo dos casos por comportamiento.
   - R12: no commit/push sin solicitud explícita.
   - R13: datos de salud y cobros son gobernanza CRITICAL/HIGH; análisis antes de escribir código, sin atajos.
   - R14: todos los datos de test/seed/demo son sintéticos; nunca datos reales sensibles.

## Risks / Trade-offs

- [Divergencia ADR-003] Evoluciones actuales no contienen ancla FDI ni fecha/profesional con nombres de contrato → migración forward más pruebas de proyección; no archivar C-05 con contrato incumplido.
- [RN-CO-05 contradictoria] La redacción actual parece invertir el orden de cálculo → armonizar explícitamente la KB con la fórmula aprobada antes de aplicar; no implementar hasta cerrar esa tarea de documentación.
- [Exposición de HCE] Los endpoints actuales no restringen la lectura por rol como KB → pruebas positivas/negativas RBAC y respuesta no reveladora cross-tenant.
- [Adjuntos inseguros] Solo hay URL/metadata, no inspección del contenido → seleccionar almacenamiento/control de acceso antes de aceptar archivos clínicos.
- [Auditoría insuficiente] Timestamps no identifican autor ni cambios → incorporar registro atómico y acceso limitado al dueño.
- [Datos de salud] Error de tenancy o logging puede causar daño legal y privacidad → revisión de seguridad HIGH/CRITICAL, minimización y tests sintéticos.

## Migration Plan

1. Armonizar RN-CO-05 antes de aplicar; confirmar los detalles de interfaz de carga/descarga, proveedor concreto compatible con S3, vínculo profesional/usuario, auditoría y estados de presupuesto adicionales que resulten materiales.
2. Escribir primero pruebas rojas de servicios, permisos, tenancy, proyección FDI, auditoría, saldo y UI; usar exclusivamente fixtures sintéticos.
3. Agregar migración forward desde Alembic head real: ampliar/copiar datos sin destruir 005; verificar restricciones y compatibilidad en entorno descartable.
4. Ensayar upgrade/downgrade y exportación/retención con muestras sintéticas; documentar cualquier incompatibilidad. Nunca revertir producción destruyendo historias clínicas.

## Open Questions

Decisiones cerradas para C-05:

- La autoría clínica se vincula por `profesional.usuario_id`; solo el odontólogo cuyo usuario coincide puede crear y gestionar evoluciones. Un profesional sin usuario asociado no puede firmar en el sistema. El dueño consulta, no crea evoluciones; recepción no accede al contenido clínico.
- La UI carga al backend y descarga mediante URL firmada temporal. El almacenamiento será privado y compatible con S3, configurado por entorno, sin elegir proveedor en C-05.
- Presupuestos usan únicamente `borrador`, `aprobado` y `aceptado`; se permite CRUD y cada eliminación se audita. Solo los dos últimos estados contribuyen a deuda.
- Se reutiliza `audit_event` en la misma transacción; registra nombres de campos, no valores clínicos. El endpoint de lectura queda limitado al dueño.
- C-05 no implementa purga automática. La baja de paciente permanece lógica y se conservan historia clínica y auditoría; la política legal de retención requiere definición especializada antes de habilitar supresión de esos registros.
