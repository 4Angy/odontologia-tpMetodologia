# Informe de pruebas de integración y carga — Consultorio Odontológico

**Fecha:** 2026-11-09
**Alcance:** integración real frontend (Vite dev :5173) ↔ backend (FastAPI :8000) ↔ Postgres 16 (:55432) + pruebas de volumen contra la API.
**Scripts:** `scripts/e2e_integracion.py` (Playwright/Chromium), `scripts/load_test.py` (concurrencia con hilos). Resultados crudos en `scripts/e2e_integracion_resultado.json` y `scripts/load_test_resultado.json`.

---

## 1. Entorno de prueba

| Componente | Detalle |
|---|---|
| Backend | `uvicorn app.main:app` (1 worker, sync SQLAlchemy + threadpool) |
| DB | Postgres 16 en Docker (`odontologia-test-pg`), migrada a head `017_audit_rol_activo`, seed demo |
| Redis | **No levantado** → la app cae al rate limiter in-memory (comportamiento previsto, ver §5) |
| Frontend | `npm run dev` (Vite 6) con proxy de rutas API |
| Datos | Solo seed sintético demo (R14 cumplido) |

---

## 2. Resultados de integración UI ↔ API (Playwright)

| # | Check | Resultado | Detalle |
|---|-------|-----------|---------|
| 1 | Reserva pública `/r/demo` carga | ✅ | ~1,3 s primera carga (dev, sin bundle) |
| 2 | Slug inexistente `/r/tenant-que-no-existe` | ✅ | Muestra "No pudimos cargar la disponibilidad. Probá de nuevo." |
| 3 | Login password incorrecta | ✅ | `role=alert`: "Email o contraseña incorrectos." |
| 4 | Login email inexistente | ✅ | **Mismo mensaje** que password incorrecta (anti-enumeración RN-AU-01 correcto) |
| 5 | Submit de login vacío | ✅ | Validación HTML5, **0 requests** a `/auth/login` |
| 6 | Login exitoso | ✅ | Redirige a `/agenda` en ~400 ms |
| 7 | Agenda carga con datos | ✅ | Turnos demo visibles |
| 8 | Deep-link `/agenda` (F5 / URL directa) | ❌ **BUG** | Devuelve `{"detail":"Not Found"}` — ver §3.1 |
| 9 | Deep-link `/pacientes` | ❌ **BUG** | Devuelve `{"code":"RN-AU-01"...}` JSON crudo — §3.1 |
| 10 | Deep-link `/config` | ❌ **BUG** | Ídem — §3.1 |
| 11 | Pacientes vía navegación interna | ✅ | Lista carga OK |
| 12 | Recepción → Configuración | ⚠️ | Muestra "Sin permiso" (correcto) **pero el enlace es visible en el nav** — §3.2 |
| 13 | API caída durante login (request abortada) | ✅ | Muestra "Ingresando…" → mensaje de error, no crashea ni cuelga |
| 14 | Ruta inexistente `/ruta-que-no-existe` | ✅ | NotFoundPage |
| 15 | Sesión persiste tras reload | ✅ | `/agenda` sigue autenticado (refresh token OK) |

**Console errors:** solo `401/403/404` de recursos esperados (endpoints protegidos antes del login, probing de rutas). Ningún error de JS no controlado.

---

## 3. Bugs y casos borde encontrados

### 3.1 ~~BUG~~ ✅ CORREGIDO — El proxy de Vite sombrea las rutas SPA (deep-link roto en dev)

`vite.config.ts` proxea prefijos que **colisionan con rutas del frontend**: `/agenda`, `/pacientes`, `/caja`, `/config` (y potencialmente `/turnos`, `/profesionales`, etc. si se agregan vistas con esos nombres).

- Navegación interna (click en el nav) → funciona, porque es client-side routing.
- **Recarga de página (F5), bookmark o link compartido** a `/agenda`, `/pacientes`, `/caja` o `/config` → el dev server reenvía la request a la API, que responde `404 {"detail":"Not Found"}` o `401 {"code":"RN-AU-01"}` y el usuario ve **JSON crudo en el navegador**.
- `/r/{slug}` ya resolvió este mismo problema con un `bypass` para `Accept: text/html`; las demás rutas no lo tienen.

**Impacto:** en dev es molestia; **en producción hay que verificar** cómo se sirve la SPA — si el mismo patrón de prefijos se repite (SPA + API en el mismo origen sin `/api` prefix), el bug es idéntico y rompe todos los deep-links.

**Fix aplicado (2026-11-09):** `vite.config.ts` ahora aplica el `bypass` de `Accept: text/html → /index.html` a **todos** los prefijos proxied (antes solo `/r`). Verificado: deep-links a `/agenda`, `/pacientes` y `/config` sirven la SPA y los 17 checks E2E pasan. **Queda pendiente verificar la config de deploy productivo** — si sirve SPA+API en el mismo origen con estos prefijos, el bug se repite fuera de dev.

### 3.2 ~~Inconsistencia~~ ✅ CORREGIDO — Permisos: shell vs. guard de ruta

- `AppShell` decide qué enlaces mostrar con un mapa propio (`permisosPorRuta`) que **no coincide** con los `RequirePermission` de `App.tsx`:
  - `/config`: el shell lo muestra con permiso `catalogo` (recepción lo tiene) pero la ruta exige `configuracion` → recepción ve el enlace "Configuración", hace click y cae en "Sin permiso".
  - `/lista-espera`: shell usa `agenda`, ruta exige `notificaciones`.
- **Fix aplicado (2026-11-09):** `AppShell.permisosPorRuta` ahora coincide exactamente con los `RequirePermission` de `App.tsx` (`/config` y `/transparencia` → `configuracion`; `/lista-espera` → `notificaciones`). Verificado: recepción ya no ve el enlace "Configuración" y el nav queda consistente con lo que cada ruta permite.

### 3.3 🟡 `GET /pacientes` sin paginación

Devuelve `list[PacienteResponse]` completo, y además calcula `saldo_derivado` **por paciente en loop** (N+1 potencial: una query extra por paciente). Con pocos cientos de pacientes anda; con miles la respuesta se degrada y el frontend renderiza todo el DOM.

**Fix:** paginación (`limit`/`offset` o cursor) + revisar si `saldo_derivado` puede resolverse en una sola query agregada.

### 3.4 🟡 Rate limit de login cuenta también los éxitos

`login` aplica 5 intentos/60s por IP+email **sin distinguir éxito de fallo**. Un usuario legítimo que se equivoca 4 veces y entra bien, consume cuota; en oficinas con IP compartida (NAT) varios usuarios comparten el límite por IP+email (email difiere, OK) — el riesgo real es bajo, pero un usuario que entra/sale seguido podría ver 429. Considerar resetear el contador tras login exitoso o aplicar la cuota solo a fallos.

### 3.5 🟡 `localhost` vs `127.0.0.1` — resolución IPv6

Las pruebas contra `http://localhost:8000` desde Python/urllib tardaban **~2 s por request** (intento IPv6 `::1` sin listener + fallback). Contra `127.0.0.1` vuela. En Windows con uvicorn bindeado a IPv4, `localhost` puede resolver a `::1` primero.

**Impacto real:** bajo (los browsers y `curl` hacen happy-eyeballs), pero conviene bindear uvicorn a dual-stack o documentar `127.0.0.1` en dev.

### 3.6 Casos borde cubiertos correctamente ✅

- Anti-enumeración de login (mismo mensaje para email inexistente y password mala).
- Validación client-side evita requests inválidos.
- Rate limits funcionan: `/r/{slug}` corta a 60 req/min por IP (20×429 en la prueba), login corta a 5/60s (12×429 en la prueba).
- API caída → error genérico legible, sin pantalla en blanco ni spinner eterno.
- Sesión: access token 15 min + refresh cookie; reload mantiene sesión.
- 404s de API responden en ~55 ms aun bajo 20 workers concurrentes.

---

## 4. Pruebas de carga / volumen

### 4.1 Línea base secuencial (1 request a la vez)

| Endpoint | Latencia media |
|---|---|
| `GET /health` | ~5 ms |
| `GET /agenda/dia` | ~22 ms |
| `GET /pacientes` | ~35 ms |
| `GET /pacientes?q=a` | ~35 ms |
| `GET /r/demo` (público) | ~39 ms |

### 4.2 Bajo concurrencia (hilos, uvicorn 1 worker)

| Escenario | Requests | Workers | RPS | p50 | p95 | p99 | Errores |
|---|---|---|---|---|---|---|---|
| `GET /health` | 200 | 20 | 309 | 63 ms | 73 ms | 77 ms | 0 |
| `GET /health` | 500 | 50 | 299 | 162 ms | 188 ms | 194 ms | 0 |
| `GET /agenda/dia` | 100 | 10 | 90 | 100 ms | 169 ms | 182 ms | 0 |
| `GET /agenda/dia` | 300 | 30 | 94 | 297 ms | **455 ms** | 488 ms | 0 |
| `GET /pacientes` | 100 | 10 | 54 | 178 ms | 246 ms | 353 ms | 0 |
| `GET /pacientes?q=a` | 100 | 20 | 57 | 334 ms | **393 ms** | 415 ms | 0 |
| `GET /r/demo` | 80 | 10 | 75 | 148 ms | 193 ms | 209 ms | 20×429 (rate limit, esperado) |
| `POST /auth/login` | 15 | 5 | 47 | 10 ms | 315 ms | 315 ms | 12×429 (rate limit, esperado) |
| `GET /no-existe` | 100 | 20 | 319 | 61 ms | 67 ms | 67 ms | 404 (esperado) |

### 4.3 Lectura de performance

- **El sistema aguanta ~300 RPS en endpoints sin DB** y ~55–95 RPS en endpoints con DB, sin errores 5xx ni timeouts — buena resiliencia base.
- **La latencia crece ~lineal con la concurrencia** en endpoints de DB (p95 de `/agenda/dia` pasa de ~170 ms con 10 workers a ~455 ms con 30). Causas probables: pool de conexiones SQLAlchemy default (5+10) y endpoints `def` síncronos en threadpool. No es un defecto para la escala de un consultorio, pero:
  - Si se espera más de ~50 usuarios concurrentes por instancia, revisar `pool_size`/`max_overflow` en `deps.py` y considerar `--workers` en uvicorn o endpoints `async`.
- **`/pacientes?q=` es el endpoint más lento** (~35 ms secuencial, p95 ~390 ms bajo carga): el `ILIKE`/búsqueda probablemente no tiene índice. Con volumen de pacientes conviene `pg_trgm` + índice GIN.
- **Todo el frontend viaja en un solo bundle de 258 kB** (sin `React.lazy` ni code-splitting por ruta). Aceptable hoy; a medida que crezcan agenda/pacientes/caja conviene lazy-load por feature.

---

## 5. Resiliencia y observaciones de infraestructura

- **Redis caído** → rate limiter cae a in-memory con warning en log y `/health/ready` reporta `redis: fallo`. Correcto para dev; en producción con >1 réplica de API el rate limit in-memory es **por proceso** → los límites se multiplican por la cantidad de workers/instancias. El limiter distribuido por Redis ya existe (C-13); asegurarse de que esté activo en deploy.
- **Postgres caído** → `/health/ready` lo reportaría; los endpoints devolverían 500 con `code` trazable (verificado indirectamente por tests de errores).
- **JWT_SECRET dev** en `backend/.env` es un placeholder — obligatorio rotarlo en deploy (ya hay runbook `docs/runbooks/rotacion-secretos.md`).
- **Acceso token de 15 min**: si un usuario deja la agenda abierta más de 15 min, la próxima acción dispara refresh transparente (verificado: sesión persiste tras reload). No se probó expiración forzada del access en medio de una operación — recomendado como caso de prueba manual.

---

## 6. Recomendaciones priorizadas

| P | Ítem | Tipo |
|---|------|------|
| ~~1~~ | ~~Resolver colisión proxy↔rutas SPA~~ **HECHO 2026-11-09** — bypass `text/html` en todos los prefijos. Verificar deploy productivo | Bug dev / riesgo prod |
| ~~2~~ | ~~Unificar mapa permiso↔ruta entre `AppShell` y `App.tsx`~~ **HECHO 2026-11-09** | UX / bug menor |
| 3 | Paginación en `GET /pacientes` + revisar N+1 de `saldo_derivado` | Performance / escalabilidad |
| 4 | Índice para búsqueda de pacientes (`pg_trgm`/GIN) si la base crece | Performance |
| 5 | Evaluar `pool_size` de SQLAlchemy y workers de uvicorn antes de >50 usuarios concurrentes | Performance |
| 6 | Code-splitting del frontend por feature (`React.lazy`) | Performance frontend |
| 7 | Resetear contador de rate-limit de login tras éxito (o contar solo fallos) | UX |
| 8 | Prueba manual pendiente: expiración del access token en medio de una operación larga | Cobertura |

---

## 7. Reproducir

```bash
# 1. Infra
 docker start odontologia-test-pg           # Postgres tests en :55432
docker exec odontologia-test-pg psql -U odontologia -c "CREATE DATABASE odontologia"  # si no existe
cd backend
DATABASE_URL="postgresql+psycopg://odontologia:odontologia@localhost:55432/odontologia" \
  python -m alembic upgrade head
DATABASE_URL="..." SEED_DEMO=true python -m uvicorn app.main:app --port 8000
# asignar password demo a usuarios seed (una vez):
#   recepcion@demo.com / dueno@demo.com / odontologo@demo.com / multi@demo.com -> demo1234

# 2. Frontend
cd frontend && npm run dev -- --port 5173

# 3. Pruebas
python scripts/e2e_integracion.py   # Playwright UI<->API
python scripts/load_test.py         # volumen contra la API
```
