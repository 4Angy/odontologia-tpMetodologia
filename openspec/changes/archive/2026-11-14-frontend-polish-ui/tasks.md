# Tasks

## 1. Sistema visual global

- [x] 1.1 Crear `frontend/src/styles/global.css` con tokens `--ui-*` (paleta alineada a la agenda `#174f91`), reset `box-sizing`, tipografía base, `::selection`, `:focus-visible`, utilidades `.sr-only`/`.muted`; verificar build incluye la hoja.
- [x] 1.2 Estilos base de controles: `button` (hover/disabled), `button[type=submit]` primario, `input`/`select`/`textarea` con focus ring, `label`, `fieldset`/`legend`; verificar legibilidad en login y formularios.
- [x] 1.3 Estilos de `table` (header, hover de fila, bordes), `[role=status]`/`[role=alert]`, `dialog`/`::backdrop`; verificar tablas de pacientes/caja y alerts.
- [x] 1.4 Layout `.app-shell`: header sticky-like con brand, nav en pills con estado activo (`a.active`/`[aria-current]`), logout a la derecha, `main` centrado con `max-width`, breakpoint <640px; verificar shell en todas las rutas autenticadas.
- [x] 1.5 Importar `global.css` desde `frontend/src/main.tsx`; verificar orden de cascada (global antes que `AgendaPage.css`) y que la agenda no sufre regresiones visuales.

## 2. Caja: monto en pesos

- [x] 2.1 Reemplazar `input[type=number]` de monto por texto con `inputMode=decimal`, helper `pesosACentavos` (coma/punto, `>0`, `Math.round(*100)`) y error amigable; verificar payload sigue enviando `monto_cents` entero.
- [x] 2.2 Formatear deudas, cobros y totales de cierre con `Intl.NumberFormat("es-AR", {currency:"ARS"})`; verificar visualización `$ 1.500,50`.

## 3. Infraestructura de desarrollo

- [x] 3.1 Agregar `/lista-espera` y `/export` a `API_PREFIXES` en `frontend/vite.config.ts`; verificar que `GET /lista-espera` y `GET /export/pacientes.csv` llegan al backend a través del proxy.
- [x] 3.2 Normalizar `backend/docker-entrypoint.sh` a fin de línea LF; verificar `docker compose up` arranca api/worker sin `exec format error`.
- [x] 3.3 Crear `.env` de desarrollo con `SEED_DEMO=true` (gitignored) y asignar password `demo1234` a los usuarios seed; verificar login real por `POST /auth/login` y por la UI.
- [x] 3.4 Crear `samples/pacientes-demo.csv` (20 pacientes sintéticos, columnas `nombre,apellido,dni,telefono,email`); verificar formato contra `CSV_ALLOWED_HEADERS` del backend.

## 4. Documentación y verificación

- [x] 4.1 Actualizar `README.md`: sección "Levantar la app completa (demo local)" (.env, compose, health checks, usuarios demo, snippet de passwords, frontend dev, notas proxy/LF/CSV) y conteos de tests reales (backend 219, frontend 64 con 1 fallo conocido).
- [x] 4.2 Corregir estado de C-10 en `CHANGES.md` (`[ ] pendiente` → `[x] archivado`) tras constatar su change archivado con 21/21 tareas.
- [x] 4.3 Verificación: `npm run typecheck` limpio, `npm run build` OK, `npx vitest run` 63/64 (1 fallo preexistente ajeno), `pytest` backend 219/219 con `APP_ENV=test`, smoke manual login → agenda/pacientes/caja/lista-espera.
