# Spec Delta

## Purpose

Define el contrato del núcleo multi-tenant del sistema (tenants, usuarios, configuración y el aislamiento por `tenant_id`) que sostiene todos los dominios de negocio: agenda, pacientes, cobros y notificaciones.

## ADDED Requirements

### Requirement: Aislamiento por tenant en la capa de datos

El sistema SHALL filtrar toda lectura y toda escritura de datos de negocio por el `tenant_id` del tenant autenticado, de forma que un tenant nunca pueda leer ni modificar datos de otro. El filtro SHALL ser aplicado por la capa de acceso a datos y no depender de que cada consulta lo recuerde.

#### Scenario: Un tenant no ve los datos de otro (funcionamiento esperado)

- **GIVEN** existen dos tenants `A` y `B`, y el tenant `B` tiene un usuario con el identificador `u-1`
- **WHEN** el acceso a datos del tenant `A` pide el identificador `u-1`
- **THEN** no devuelve ninguna fila, y el acceso a datos de negocio no puede obtenerse sin un tenant, de modo que el filtro por tenant forma parte de la construcción del acceso y no de cada consulta

#### Scenario: El mismo identificador existe en dos tenants (borde)

- **GIVEN** el tenant `A` y el tenant `B` tienen cada uno un usuario con el mismo correo `mismo@correo.com`
- **WHEN** se crea el usuario del tenant `B` con ese correo
- **THEN** la creación es correcta, porque la unicidad del correo es **por tenant** y no global, y la lectura de cualquiera de los dos usuarios desde el tenant equivocado no devuelve filas

### Requirement: Rechazo de operaciones sin tenant autenticado

El sistema SHALL rechazar con `403` toda operación de negocio cuyo token no identifique un tenant, y SHALL responder con el código de trazabilidad `RN-AU-01` y un mensaje en español-AR. El sistema SHALL NOT responder `404`, porque confirmaría la existencia de recursos de otro tenant.

#### Scenario: Token sin tenant en una operación de negocio (error de negocio)

- **GIVEN** un token firmado correctamente pero sin `tenant_id`
- **WHEN** se ejecuta una operación de negocio que requiere tenant
- **THEN** la respuesta es `403` con el código `RN-AU-01` y un mensaje en español-AR, y no se ejecuta ninguna consulta de datos

#### Scenario: El tenant del token no se toma del cliente (borde)

- **GIVEN** un token válido del tenant `A` y una solicitud que incluye un `tenant_id` distinto en el cuerpo o en un header
- **WHEN** se ejecuta la operación de negocio
- **THEN** la operación se resuelve con el `tenant_id` del token, y el valor enviado por el cliente se ignora por completo

### Requirement: Identidad global del tenant por slug

El sistema SHALL identificar a cada tenant por un `slug` en formato kebab-case, único a nivel global, y SHALL exponerlo como el identificador usado en los links públicos de reserva.

#### Scenario: Dos tenants con el mismo slug (error de negocio)

- **GIVEN** ya existe un tenant con `slug` `clinica-demo`
- **WHEN** se intenta crear otro tenant con el mismo `slug`
- **THEN** la creación es rechazada con un error `409` cuyo cuerpo es `{code, message}` —el código genérico documentado, porque la base de conocimiento no define una regla de negocio para el slug duplicado— y con un mensaje en español-AR que indique que el slug ya está en uso; el detalle técnico de la restricción queda en el log y no en la respuesta

#### Scenario: Slug con formato inválido (borde)

- **GIVEN** se intenta crear un tenant con un `slug` que contiene espacios, mayúsculas o caracteres fuera del alfabeto kebab-case
- **WHEN** se normaliza y se valida el `slug`
- **THEN** el sistema lo normaliza a minúsculas y guiones simples, o lo rechaza con un mensaje en español-AR que indique el formato esperado, sin crear el tenant

#### Scenario: Todo tenant tiene slug (borde)

- **GIVEN** se listan los tenants del sistema
- **WHEN** se inspecciona el `slug` de cada uno
- **THEN** ninguno está vacío ni es nulo, porque la unicidad global del `slug` no puede garantizarse sobre valores nulos

### Requirement: Roles acumulables con permiso por unión

El sistema SHALL admitir que un usuario acumule varios roles entre `recepcion`, `odontologo` y `dueno`, y SHALL computar el permiso efectivo como la **unión** de los roles del usuario. Ningún flujo SHALL exigir que un consultorio tenga tres personas distintas.

#### Scenario: Usuario con dos roles (funcionamiento esperado)

- **GIVEN** un usuario del tenant `A` con los roles `recepcion` y `odontologo`
- **WHEN** se evalúa si puede leer la agenda del consultorio y si puede registrar una atención propia
- **THEN** ambas operaciones están permitidas, y ninguna de las dos requiere un rol adicional ni un segundo usuario

#### Scenario: Usuario sin roles o inactivo (borde)

- **GIVEN** un usuario del tenant `A` sin ningún rol asignado, y otro usuario `B` con rol `dueno` pero `activo` en `false`
- **WHEN** se evalúa el permiso de cada uno
- **THEN** el primero no tiene ningún permiso efectivo, y el segundo tampoco, porque la inactividad revoca el acceso con independencia de sus roles

### Requirement: Auditoría mínima de toda mutación

El sistema SHALL registrar en toda fila de negocio la fecha de creación, la fecha de última modificación y la fecha de eliminación lógica. El borrado de un registro SHALL ser lógico, de modo que la fila siga existiendo para auditoría.

#### Scenario: Mutación con sello de auditoría (funcionamiento esperado)

- **GIVEN** un usuario del tenant `A` con un registro de negocio propio
- **WHEN** se crea el registro y luego se modifica su contenido
- **THEN** el registro conserva su fecha de creación original, su fecha de última modificación es posterior a la anterior, y su fecha de eliminación está vacía

#### Scenario: Borrado lógico (borde)

- **GIVEN** un registro de negocio del tenant `A` que es referenciado por otro registro
- **WHEN** se elimina
- **THEN** el registro sigue existiendo con su fecha de eliminación informada, deja de aparecer en los listados por defecto, y el registro que lo referenciaba no queda inconsistente

### Requirement: Seed de demostración idempotente

El sistema SHALL proveer un seed de demostración que cree un tenant con `slug` `demo` y tres usuarios: uno con cada rol y uno con los tres roles juntos, para poder probar el caso "todo en una persona". El seed SHALL ser idempotente: ejecutarlo varias veces SHALL dejar el mismo estado, sin duplicar filas ni sobrescribir datos existentes. El seed SHALL NOT ejecutarse de forma automática al arrancar la aplicación.

#### Scenario: Seed ejecutado dos veces (funcionamiento esperado)

- **GIVEN** una base de datos sin el seed aplicado
- **WHEN** se ejecuta el seed de demostración dos veces consecutivas
- **THEN** tras la primera ejecución existe un tenant `demo` y sus tres usuarios, y tras la segunda el número de tenants y de usuarios es el mismo, sin filas duplicadas

#### Scenario: Seed con datos ya presentes (borde)

- **GIVEN** el tenant `demo` ya existe con un usuario cuyo correo fue cambiado
- **WHEN** se ejecuta de nuevo el seed de demostración
- **THEN** el seed no vuelve a crear el tenant, no duplica los usuarios que ya existen y no sobrescribe el correo modificado
