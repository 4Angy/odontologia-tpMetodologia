# Proposal

## Why

El frontend real (C-01 → C-13) funcionaba pero visualmente era inconsistentre: solo la agenda tenía estilos propios (`AgendaPage.css`) y el resto de las pantallas — shell, login, pacientes, caja, reserva pública — era HTML semántico sin CSS. Además se detectaron dos defectos de experiencia/infra durante la verificación manual: el campo de monto de caja exigía pensar en centavos enteros y la lista de espera fallaba en dev por un prefijo de proxy faltante en Vite. Sin una base visual común ni instrucciones de lanzamiento, el sistema no era presentable ni reproducible para el onboarding.

## What Changes

- Nuevo `frontend/src/styles/global.css`: tokens de diseño (paleta alineada con la agenda), estilos base de tipografía, botones, formularios, tablas, alerts, diálogos nativos, utilidad `.sr-only` y layout del `.app-shell` (header con navegación en pills, estado activo, logout, contenedor centrado, breakpoint móvil).
- `CajaPage`: el campo de monto pasa a ingresar **pesos con decimales** y se convierte a `monto_cents` al enviar (contrato de API sin cambios); deudas, cobros y cierre del día se muestran formateados como moneda `es-AR`.
- `vite.config.ts`: se agregan los prefijos `/lista-espera` y `/export` a `API_PREFIXES` para que el proxy dev cubra todas las rutas de API que consume el frontend.
- `backend/docker-entrypoint.sh`: conversión CRLF → LF para que el entrypoint funcione en checkouts de Windows.
- `README.md`: sección "Levantar la app completa (demo local)" con `.env`, compose, usuarios demo, asignación de passwords del seed y nota del proxy; conteos de tests actualizados a los valores verificados.
- `samples/pacientes-demo.csv`: CSV sintético de ejemplo para el import de pacientes.

## Capabilities

### New Capabilities

- `frontend-ui`: sistema visual global del frontend — tokens, shell, controles, tablas, formato de montos y requisitos de legibilidad/accesibilidad mínimos en todas las rutas.

### Modified Capabilities

- Ninguna: no cambia contratos de API, RBAC, tenancy ni reglas de negocio.

## Impact

- Frontend: `src/styles/global.css` (nuevo), `src/main.tsx` (import), `src/features/caja/CajaPage.tsx`, `vite.config.ts`.
- Backend: solo `docker-entrypoint.sh` (fin de línea); cero cambios de comportamiento.
- Documentación: `README.md`, `CHANGES.md` (estado de C-10 corregido), `samples/pacientes-demo.csv` (nuevo).
- Sin migraciones, sin variables de entorno nuevas, sin dependencias nuevas.
