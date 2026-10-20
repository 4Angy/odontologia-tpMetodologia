# foundation/runtime Specification

## Purpose
Define el contrato del runtime de la aplicación (configuración por variables de entorno, health checks, logging estructurado y sobre de error uniforme) que todo el proyecto —backend, worker y frontend— consume como base común desde el primer change.

## Requirements

### Requirement: Liveness del servicio independiente de las dependencias

El sistema SHALL exponer `GET /health` que responda `200` con un cuerpo que contenga el estado del servicio, su nombre y su versión. La respuesta SHALL NOT depender de la base de datos ni de Redis: una dependencia caída SHALL NOT provocar reinicios del contenedor.

#### Scenario: Servicio disponible sin depender de la base ni de Redis

- **GIVEN** la aplicación está arrancada
- **WHEN** se solicita `GET /health`
- **THEN** el sistema responde `200` con el estado del servicio, su nombre y su versión

#### Scenario: El health check no consulta las dependencias externas

- **GIVEN** la aplicación está arrancada y la base de datos y Redis están inaccesibles
- **WHEN** se solicita `GET /health`
- **THEN** el sistema responde `200` igual, sin propagar el fallo de las dependencias

### Requirement: Readiness con estado por componente

El sistema SHALL exponer `GET /health/ready` que verifique la conexión a la base de datos y a Redis. Responderá `200` solo cuando ambas dependencias estén operativas; si alguna falla, SHALL responder `503` identificando qué componente falló, sin exponer credenciales, URIs con contraseñas ni datos de negocio.

#### Scenario: Dependencias operativas

- **GIVEN** la base de datos y Redis responden correctamente
- **WHEN** se solicita `GET /health/ready`
- **THEN** el sistema responde `200` informando que el servicio está listo

#### Scenario: Base de datos inaccesible

- **GIVEN** la base de datos no responde y Redis sí
- **WHEN** se solicita `GET /health/ready`
- **THEN** el sistema responde `503` identificando el componente de base de datos como fallido, sin incluir credenciales ni la URI de conexión

#### Scenario: Redis inaccesible

- **GIVEN** Redis no responde y la base de datos sí
- **WHEN** se solicita `GET /health/ready`
- **THEN** el sistema responde `503` identificando el componente de cola y caché como fallido, sin incluir credenciales

### Requirement: Configuración por variables de entorno validada al arranque

El sistema SHALL leer su configuración exclusivamente de variables de entorno y SHALL validarla al arrancar. Las variables canónicas son: `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `JWT_ACCESS_MIN`, `JWT_REFRESH_DAYS`, `TENANT_DEFAULT_TZ`, `WHATSAPP_PROVIDER`, `WHATSAPP_API_TOKEN`, `WHATSAPP_PHONE_ID`, `MP_ACCESS_TOKEN`, `MP_WEBHOOK_SECRET`, `SMTP_URL`, `PUBLIC_BASE_URL` y `SEED_DEMO`. El entorno de ejecución se declara con la variable operativa `APP_ENV` (`dev` | `test` | `prod`). Si alguna variable requerida falta o tiene un valor inválido, la aplicación SHALL abortar el arranque con un mensaje que nombre la variable y el formato esperado, en lugar de operar en modo degradado con valores por defecto silenciosos.

#### Scenario: Configuración completa y válida

- **GIVEN** todas las variables canónicas están presentes con valores válidos
- **WHEN** la aplicación arranca
- **THEN** el arranque completa sin errores y el servicio queda disponible

#### Scenario: Variable con valor inválido

- **GIVEN** una variable canónica está presente pero su valor no cumple el formato esperado, por ejemplo `JWT_ACCESS_MIN` con un valor no numérico
- **WHEN** la aplicación arranca
- **THEN** el arranque se aborta con un mensaje que nombra esa variable y el formato esperado, y el servicio no queda disponible

#### Scenario: Variable requerida ausente

- **GIVEN** falta una variable canónica requerida
- **WHEN** la aplicación arranca
- **THEN** el arranque se aborta con un mensaje que nombra la variable ausente

#### Scenario: El entorno de ejecución está declarado

- **GIVEN** `APP_ENV` vale `prod` y el resto de las variables canónicas es válido
- **WHEN** la aplicación arranca
- **THEN** la aplicación aplica las reglas del entorno `prod` (secreto de firma obligatorio y de longitud mínima) en lugar de las de `dev`

### Requirement: Secreto de firma obligatorio fuera de desarrollo y prueba

`JWT_SECRET` SHALL ser obligatoria en todo entorno que no sea de desarrollo o de prueba; si falta, la aplicación SHALL abortar el arranque. En desarrollo y en prueba el sistema MAY operar con un valor generado en el proceso, y en ese caso SHALL emitir un aviso explícito al arrancar. El repositorio SHALL NOT contener secretos reales: los archivos de ejemplo de variables de entorno SHALL contener únicamente marcadores de posición.

#### Scenario: Arranque en un entorno productivo sin secreto

- **GIVEN** el entorno no es de desarrollo ni de prueba y `JWT_SECRET` no está definida
- **WHEN** la aplicación arranca
- **THEN** el arranque se aborta con un mensaje que indica que falta `JWT_SECRET`

#### Scenario: Arranque en desarrollo sin secreto

- **GIVEN** el entorno es de desarrollo y `JWT_SECRET` no está definida
- **WHEN** la aplicación arranca
- **THEN** la aplicación arranca, emite un aviso explícito de que usa un secreto temporal y el secreto no queda escrito en el repositorio

#### Scenario: Los archivos de ejemplo no contienen secretos

- **GIVEN** los archivos de ejemplo de variables de entorno del proyecto
- **WHEN** se inspecciona su contenido
- **THEN** ninguno contiene un valor de secreto real, solo marcadores de posición y su descripción

### Requirement: Sobre de error uniforme con código trazable

El sistema SHALL responder a todo error con un cuerpo `{code, message, action?}`. El campo `code` SHALL identificar la regla de negocio que causa el error cuando exista una regla aplicable, o un código genérico documentado cuando no exista ninguna. El campo `message` SHALL estar en español-AR y ser mostrable al usuario final sin traducción ni formato adicional. El campo `action` SHALL estar presente solo cuando exista una acción sugerible y SHALL ser opcional en todos los casos. Ningún endpoint SHALL devolver una forma de error distinta de esta.

#### Scenario: Error causado por una regla de negocio

- **GIVEN** una operación viola una regla de negocio con identificador propio
- **WHEN** el sistema responde con el error
- **THEN** el cuerpo contiene `code` con ese identificador de regla, `message` en español-AR y el código HTTP que corresponde a esa situación

#### Scenario: Error sin regla de negocio aplicable

- **GIVEN** una operación falla sin que exista una regla de negocio que la cause
- **WHEN** el sistema responde con el error
- **THEN** el cuerpo contiene el `code` genérico documentado y un `message` en español-AR

#### Scenario: Ausencia de acción sugerible

- **GIVEN** un error que no ofrece ninguna acción al usuario
- **WHEN** el sistema responde con el error
- **THEN** el cuerpo contiene únicamente `code` y `message`, sin campo de acción

#### Scenario: Exposición de detalle interno

- **GIVEN** una operación falla con una causa interna
- **WHEN** el sistema responde con el error
- **THEN** el cuerpo no incluye trazas, nombres de clases, sentencias SQL ni rutas del sistema de archivos

### Requirement: Logging estructurado sin exposición de secretos

El sistema SHALL emitir logs estructurados que contengan marca de tiempo en UTC, nivel, mensaje y contexto de la operación. Los valores marcados como sensibles —tokens, claves, secretos y URIs de conexión con contraseña— SHALL NOT aparecer en los logs, ni siquiera en los de arranque.

#### Scenario: Registro de arranque con formato estructurado

- **GIVEN** la aplicación arranca con configuración válida
- **WHEN** se emite el log de arranque
- **THEN** el registro contiene marca de tiempo en UTC, nivel y mensaje, y el contexto aparece como campos separados

#### Scenario: Los valores sensibles no se registran

- **GIVEN** la configuración contiene un token, una clave y una URI de conexión con contraseña
- **WHEN** se emite el log de arranque
- **THEN** ninguno de esos valores aparece en el registro, y su presencia se puede afirmar con una aserción explícita

#### Scenario: Un error se registra con su código trazable

- **GIVEN** una operación falla con un error de negocio
- **WHEN** se registra el error
- **THEN** el registro incluye el código de la regla que lo causó, de modo que el log y la respuesta al usuario sean consistentes
