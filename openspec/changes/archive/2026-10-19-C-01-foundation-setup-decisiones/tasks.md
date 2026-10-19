# Tasks — C-01 `foundation-setup-decisiones`

> TDD estricto (R11): cada grupo escribe el test en rojo ANTES del código; mínimo 2 casos por comportamiento. Datos sintéticos/demo únicamente (R14).
> Contrato de comportamiento: `specs/foundation/runtime/spec.md`. Decisiones: `design.md`.
> Los grupos 8 (frontend) y 10 (ADR) son independientes entre sí y del resto: se pueden ejecutar en paralelo con los grupos 2-7.

## 1. Andamiaje y dependencias

- [x] 1.1 Agregar a `backend/requirements.txt` el driver de Postgres (`psycopg[binary]`), `pydantic-settings` y `redis`, y verificar que la instalación resuelve y que `python -c "import psycopg, pydantic_settings, redis"` no falla
- [x] 1.2 Agregar `react-router-dom` a `frontend/package.json` junto con los scripts `dev`, `build` y `preview`, y verificar que `npm install` completa sin conflictos y que `npm run typecheck` sigue pasando
- [x] 1.3 Crear el árbol de directorios canónico de `08_arquitectura_propuesta.md` §Estructura (`backend/app/modules/{pacientes,cobros,notificaciones,tenancy}/` con `__init__.py`, `backend/app/worker/`, `backend/tests/`, `frontend/src/{shared,pages}/`), y verificar que el árbol resultante coincide con el de la KB
- [x] 1.4 Crear `.env.example` en la raíz, en `backend/` y en `frontend/` con las 14 variables canónicas y solo marcadores de posición, y verificar por inspección que ningún archivo contiene un valor de secreto real
- [x] 1.5 Declarar en `backend/requirements.txt` y `frontend/package.json` los comandos de verificación (`pytest`, `vitest run`, `tsc --noEmit`) y verificar que se ejecutan sin error de resolución de comandos

## 2. Configuración por variables de entorno con validación y fail-fast

- [x] 2.1 Escribir tests en rojo: con las 14 variables válidas la configuración carga y los tipos se parsean (enteros a int, booleanos a bool, zona horaria a tz), y verificar en rojo con `pytest backend/tests -k "settings" -x`
- [x] 2.2 Implementar `backend/app/core/config.py` con una clase `Settings` frozen sobre `pydantic-settings`, con los 14 campos canónicos, secretos como `SecretStr` y una instancia única de settings, y verificar que los tests de 2.1 pasan
- [x] 2.3 Escribir tests en rojo: variable canónica con valor inválido (`JWT_ACCESS_MIN` no numérico) y variable requerida ausente, y verificar en rojo que el error identifica la variable y el formato esperado
- [x] 2.4 Implementar la validación al arranque que aborta con mensaje accionable ante variable inválida o ausente, y verificar que los tests de 2.3 pasan
- [x] 2.5 Escribir tests en rojo: sin `JWT_SECRET` en un entorno que no es dev/test la aplicación aborta; en dev arranca con aviso explícito y secreto temporal efímero, y verificar en rojo
- [x] 2.6 Implementar la regla de `JWT_SECRET` (obligatoria fuera de dev/test, efímera y avisada en dev/test) y eliminar el secreto fijo hardcodeado de `backend/app/core/security.py`, y verificar que los tests de 2.5 pasan
- [x] 2.7 Documentar en `backend/README.md` la tabla de las 14 variables con descripción y ejemplo, más el procedimiento para generar `JWT_SECRET`, y verificar que el comando indicado en el README se ejecuta tal como está escrito

## 3. Logging estructurado sin exposición de secretos

- [x] 3.1 Escribir tests en rojo: el log de arranque emite marca de tiempo UTC, nivel, mensaje y contexto en campos separados, y verificar en rojo con `pytest backend/tests -k "logging"`
- [x] 3.2 Implementar `backend/app/core/logging.py` con la configuración de logging estructurado y conectarlo al arranque de la aplicación, y verificar que los tests de 3.1 pasan
- [x] 3.3 Escribir tests en rojo: con token, clave y URI de conexión con contraseña en la configuración, ninguno de esos valores aparece en el log de arranque, y verificar en rojo
- [x] 3.4 Implementar el filtrado de valores sensibles en el logging, y verificar que los tests de 3.3 pasan
- [x] 3.5 Escribir tests en rojo: el log de un error de negocio incluye el `code` de la regla que lo causó y coincide con el `code` devuelto al usuario, y verificar en rojo
- [x] 3.6 Implementar el registro de errores con su código trazable y verificar que los tests de 3.5 pasan

## 4. Sobre de error uniforme con código trazable

- [x] 4.1 Escribir tests en rojo: una excepción de negocio con `code` RN-XX, `message` en español-AR y `action` opcional produce una respuesta con cuerpo `{code, message, action?}`, y verificar en rojo con `pytest backend/tests -k "errores"`
- [x] 4.2 Implementar `backend/app/core/errors.py` con la excepción de error de negocio y su serialización, y verificar que los tests de 4.1 pasan
- [x] 4.3 Escribir tests en rojo: error sin regla aplicable devuelve el código genérico documentado, error sin acción sugerible no incluye el campo de acción, y ninguna respuesta expone trazas, SQL ni rutas del sistema de archivos, y verificar en rojo
- [x] 4.4 Implementar el handler único de errores en `backend/app/main.py` conservando la compatibilidad con la forma `detail` dict ya usada por el slice archivado, y verificar que los tests de 4.3 pasan
- [x] 4.5 Escribir test en rojo de compatibilidad: el endpoint de cancelación existente sigue respondiendo `409` con `{code: "RN-AG-01", message, action}` tras el cambio de handler, y verificar en rojo
- [x] 4.6 Ajustar el handler hasta que el test de 4.5 pase sin cambiar el contrato del spec `agenda/cancelacion-turno`, y verificar que el spec sigue validando

## 5. Health checks de liveness y readiness

- [x] 5.1 Escribir tests en rojo: `GET /health` responde `200` con estado, nombre de servicio y versión, y responde `200` aunque las dependencias estén inaccesibles, y verificar en rojo con `pytest backend/tests -k "health"`
- [x] 5.2 Implementar `GET /health` como liveness sin acceso a base de datos ni Redis, y verificar que los tests de 5.1 pasan
- [x] 5.3 Escribir tests en rojo: `GET /health/ready` responde `200` con ambas dependencias operativas y responde `503` identificando el componente fallido cuando la base de datos o Redis no responden, sin exponer credenciales, y verificar en rojo
- [x] 5.4 Implementar `GET /health/ready` con la verificación por componente, y verificar que los tests de 5.3 pasan

## 6. Base de datos real: Postgres 16 en dev y en CI

- [x] 6.1 Crear `backend/tests/conftest.py` con una fixture de sesión que cree un esquema aislado por corrida sobre Postgres 16 a partir de `TEST_DATABASE_URL` y lo elimine al terminar, y verificar que la suite de tests existentes (`backend/app/modules/agenda/tests/`) pasa contra Postgres
- [x] 6.2 Implementar el modo atajo SQLite cuando `TEST_DATABASE_URL` empieza con `sqlite://`, y verificar que la suite sigue pasando sin conexión a Postgres
- [x] 6.3 Cambiar `backend/alembic/env.py` para tomar la URL desde la configuración y apuntar `target_metadata` al `Base` de todos los módulos, y verificar que `alembic upgrade head` aplica sobre Postgres 16 sin cambios respecto del estado actual
- [x] 6.4 Verificar la reversibilidad de las migraciones ejecutando `alembic upgrade head` → `alembic downgrade -1` → `alembic upgrade head` contra Postgres 16, y confirmar que el esquema final coincide con el de `0001_cancelacion_turno` (R6)

## 7. Compose de un solo deploy y esqueleto del worker

- [x] 7.1 Implementar `backend/app/worker/main.py` con conexión a Redis, logging y un loop de scheduler sin jobs registrados que lo declare explícitamente en cada tick, y verificar que el proceso arranca y registra ese mensaje
- [x] 7.2 Crear el `Dockerfile` multi-stage del backend con imagen final sin herramientas de build, y verificar que la imagen se construye y que el contenedor responde
- [x] 7.3 Crear `docker-compose.yml` con los servicios `db` (Postgres 16 con volumen y healthcheck), `redis` (Redis 7 con AOF y healthcheck), `api` y `worker`, con dependencias condicionadas al estado saludable, y verificar que `docker compose config` es válido y que `docker compose up -d` deja los cuatro servicios arriba
- [x] 7.4 Verificar que `docker-compose.yml` no contiene secretos: solo referencias a variables del `.env`, con `JWT_SECRET` requerido y sin valores sensibles literales
- [x] 7.5 Verificar desde la red de compose que `GET /health` responde `200` y `GET /health/ready` responde `200` con Postgres y Redis operativos

## 8. Frontend: shell, router y cliente de API

- [x] 8.1 Escribir tests en rojo del cliente de API: una respuesta de error `{code, message, action?}` se traduce a un error tipado que expone el `code` y el mensaje en español-AR, y verificar en rojo con `vitest run src/shared`
- [x] 8.2 Implementar `frontend/src/shared/api/client.ts` con la URL base desde la configuración del frontend, timeouts y la traducción del sobre de error, y verificar que los tests de 8.1 pasan
- [x] 8.3 Escribir tests en rojo del shell: la aplicación monta y las rutas `agenda`, `pacientes`, `caja` y `config` resuelven a páginas placeholder, y verificar en rojo
- [x] 8.4 Implementar `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/pages/` y `frontend/src/shared/ui/` con el router y las rutas placeholder, y verificar que los tests de 8.3 pasan y que `tsc --noEmit` no reporta errores (R10, sin `any` explícito)
- [x] 8.5 Verificar que el test existente de cancelación de turnos sigue en verde y que el build de producción (`npm run build`) completa sin errores

## 9. Integración continua con jobs paralelos

- [x] 9.1 Crear `.github/workflows/ci.yml` con el job `backend` (Python 3.12, servicios Postgres 16 y Redis 7, instalación de dependencias, ciclo `upgrade head` → `downgrade -1` → `upgrade head` y `pytest`), y verificar que el workflow es válido y que el job no depende de otro
- [x] 9.2 Agregar al mismo workflow el job `frontend` (Node 20, `npm ci`, `npm run typecheck`, `vitest run`) sin dependencia del job `backend`, y verificar que ambos jobs se ejecutan en paralelo
- [x] 9.3 Verificar que el workflow no persiste secretos y que todas las variables sensibles provienen de los servicios del propio job

## 10. ADRs de las decisiones bloqueantes

- [x] 10.1 Escribir `docs/adr/ADR-001-whatsapp-provider.md` con la decisión `official`, la tabla de costos por tipo de mensaje, entregabilidad, riesgo de baneo, fallback a email, el valor por defecto de `WHATSAPP_PROVIDER` y el runbook de onboarding por tenant (WABA + plantillas preaprobadas), y verificar que el archivo contiene las seis secciones requeridas
- [x] 10.2 Escribir `docs/adr/ADR-002-alcance-facturacion.md` con el modelo exacto de `cobros/` (`cobro` + `cierre_caja`, sin `recibo` ni `numero_comprobante`), la declaración de UI que C-11 debe mostrar y el criterio de re-evaluación para el recibo interno, y verificar que el archivo contiene las cuatro secciones requeridas
- [x] 10.3 Escribir `docs/adr/ADR-003-migrabilidad-fdi.md` con la lista cerrada de campos de `evolucion` v1 migrables, la regla de proyección a odontograma FDI y el criterio de aceptación con test que hereda C-05, y verificar que el archivo contiene las tres secciones requeridas
- [x] 10.4 Crear `docs/adr/README.md` como índice de los ADR y enlazarlo desde `knowledge-base/09_decisiones_y_supuestos.md` y `knowledge-base/10_preguntas_abiertas.md`, y verificar que los enlaces resuelven a archivos existentes

## 11. Verificación integrada del change

- [x] 11.1 Ejecutar la suite completa del backend contra Postgres 16 y la del frontend, y verificar que todo queda en verde
- [x] 11.2 Levantar `docker compose up -d` desde cero y verificar el flujo completo de arranque: los cuatro servicios arriba, migraciones aplicadas, `GET /health` y `GET /health/ready` en `200`
- [x] 11.3 Ejecutar `openspec validate C-01-foundation-setup-decisiones` y verificar que no reporta errores, y que el spec de `agenda/cancelacion-turno` sigue intacto
- [x] 11.4 Revisar que `CHANGES.md` refleje el alcance realmente implementado (migración `002` de C-02, extensión de `turno` en C-07, 14 variables de entorno) y que la KB no conserve preguntas ya resueltas
