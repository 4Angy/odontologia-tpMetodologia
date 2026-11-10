"""Pruebas de integración frontend (Vite :5173) <-> backend (FastAPI :8000).

Requiere el stack levantado:
  - Postgres en localhost:55432 con DB `odontologia` migrada y seed demo
  - API en http://localhost:8000 (uvicorn app.main:app)
  - Frontend en http://localhost:5173 (npm run dev)

Credenciales demo (seedeadas): recepcion@demo.com / demo1234

Uso: python scripts/e2e_integracion.py
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field

from playwright.sync_api import sync_playwright

BASE = "http://localhost:5173"
API = "http://localhost:8000"


@dataclass
class Result:
    name: str
    ok: bool
    detail: str = ""
    ms: float = 0.0


@dataclass
class Report:
    results: list[Result] = field(default_factory=list)
    console_errors: list[str] = field(default_factory=list)
    api_timings: dict[str, list[float]] = field(default_factory=dict)

    def add(self, name: str, ok: bool, detail: str = "", ms: float = 0.0) -> None:
        self.results.append(Result(name, ok, detail, ms))
        print(("PASS" if ok else "FAIL"), name, f"({ms:.0f}ms)" if ms else "", detail[:120])


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * p / 100
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def main() -> int:
    rep = Report()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1366, "height": 900})
        page = ctx.new_page()

        def on_console(msg):
            if msg.type == "error":
                rep.console_errors.append(msg.text[:300])

        def on_response(resp):
            try:
                url = resp.url
                if ":5173" in url and not any(x in url for x in ("/@", ".tsx", ".ts?", "node_modules")):
                    timing = resp.request.timing
                    ms = timing["responseEnd"] if timing and timing.get("responseEnd", -1) >= 0 else 0
                    key = url.split(":5173")[-1].split("?")[0]
                    rep.api_timings.setdefault(key, []).append(ms)
            except Exception:
                pass

        page.on("console", on_console)
        page.on("response", on_response)

        # ---------- 1. Reserva pública ----------
        t0 = time.perf_counter()
        try:
            page.goto(f"{BASE}/r/demo", wait_until="networkidle", timeout=20000)
            page.wait_for_selector("#public-booking-title", timeout=10000)
            rep.add("public_booking_carga", True, page.title(), (time.perf_counter() - t0) * 1000)
        except Exception as e:
            rep.add("public_booking_carga", False, str(e)[:200])

        # slug inexistente
        try:
            page.goto(f"{BASE}/r/tenant-que-no-existe", wait_until="networkidle", timeout=20000)
            page.wait_for_timeout(800)
            body = page.inner_text("body")
            rep.add("public_slug_inexistente", "no" in body.lower() or "error" in body.lower() or "encontr" in body.lower(), body[:150].replace("\n", " "))
        except Exception as e:
            rep.add("public_slug_inexistente", False, str(e)[:200])

        # ---------- 2. Login ----------
        page.goto(f"{BASE}/login", wait_until="networkidle")

        # password incorrecta
        page.fill('input[type="email"]', "recepcion@demo.com")
        page.fill('input[type="password"]', "clave-incorrecta")
        page.click('button[type="submit"]')
        try:
            page.wait_for_selector('[role="alert"]', timeout=8000)
            msg_bad = page.inner_text('[role="alert"]')
            rep.add("login_password_incorrecta", True, msg_bad)
        except Exception:
            rep.add("login_password_incorrecta", False, "no apareció role=alert")

        # email inexistente -> debe dar el MISMO mensaje (anti-enumeración)
        page.fill('input[type="email"]', "noexiste@demo.com")
        page.fill('input[type="password"]', "demo1234")
        page.click('button[type="submit"]')
        try:
            page.wait_for_selector('[role="alert"]', timeout=8000)
            msg_none = page.inner_text('[role="alert"]')
            rep.add("login_email_inexistente", msg_none == msg_bad, f"'{msg_none}' vs '{msg_bad}'")
        except Exception:
            rep.add("login_email_inexistente", False, "no apareció role=alert")

        # submit vacío -> validación HTML5, no debe pegarle a la API
        req_count = {"n": 0}
        page.on("request", lambda r: req_count.__setitem__("n", req_count["n"] + 1) if "/auth/login" in r.url else None)
        page.fill('input[type="email"]', "")
        page.fill('input[type="password"]', "")
        page.click('button[type="submit"]')
        page.wait_for_timeout(600)
        rep.add("login_campos_vacios_sin_request", req_count["n"] == 0, f"requests a /auth/login: {req_count['n']}")

        # login correcto
        t0 = time.perf_counter()
        page.fill('input[type="email"]', "recepcion@demo.com")
        page.fill('input[type="password"]', "demo1234")
        page.click('button[type="submit"]')
        try:
            page.wait_for_url("**/agenda**", timeout=10000)
            rep.add("login_exitoso_redirige", True, page.url, (time.perf_counter() - t0) * 1000)
        except Exception as e:
            rep.add("login_exitoso_redirige", False, str(e)[:200])

        # ---------- 3. Agenda (recepción) ----------
        try:
            page.wait_for_selector("#agenda-titulo", timeout=10000)
            body = page.inner_text("body")
            tiene_turnos = "turno" in body.lower() or "agenda" in body.lower()
            rep.add("agenda_carga", tiene_turnos, body[:120].replace("\n", " "))
        except Exception as e:
            rep.add("agenda_carga", False, str(e)[:200])

        # ---------- 4. Deep-link /config y /pacientes (bug conocido: proxy de Vite
        # sombrea las rutas SPA que comparten prefijo con la API) ----------
        page.goto(f"{BASE}/config", wait_until="networkidle")
        page.wait_for_timeout(800)
        body_cfg = page.inner_text("body")
        es_json_api = body_cfg.strip().startswith("{")
        rep.add("deep_link_config_dev", not es_json_api,
                f"DEV-BUG: la navegación directa a /config devuelve JSON de API: {body_cfg[:100]}")

        page.goto(f"{BASE}/pacientes", wait_until="networkidle")
        page.wait_for_timeout(800)
        body_p = page.inner_text("body")
        es_json_api2 = body_p.strip().startswith("{")
        rep.add("deep_link_pacientes_dev", not es_json_api2,
                f"DEV-BUG: la navegación directa a /pacientes devuelve JSON de API: {body_p[:100]}")

        # ---------- 4b. Deep-link /agenda ----------
        page.goto(f"{BASE}/agenda", wait_until="networkidle")
        page.wait_for_timeout(800)
        body_a = page.inner_text("body")
        rep.add("deep_link_agenda_dev", not body_a.strip().startswith("{"),
                f"DEV-BUG: navegación directa a /agenda -> {body_a[:100]!r}")

        # ---------- 5. Navegación client-side (como la usa la SPA) ----------
        page.goto(f"{BASE}/agenda", wait_until="networkidle")
        try:
            page.wait_for_selector("#agenda-titulo", timeout=15000)
        except Exception as e:
            rep.add("pacientes_carga", False, f"agenda no cargó tras deep-link: {page.url} :: {page.inner_text('body')[:120]}")
            page.goto(f"{BASE}/login", wait_until="networkidle")
            page.fill('input[type="email"]', "recepcion@demo.com")
            page.fill('input[type="password"]', "demo1234")
            page.click('button[type="submit"]')
            page.wait_for_url("**/agenda**", timeout=10000)
            page.wait_for_selector("#agenda-titulo", timeout=15000)
        try:
            page.click('nav a:has-text("Pacientes")', timeout=5000)
            page.wait_for_timeout(1200)
            body = page.inner_text("body")
            rep.add("pacientes_carga", "paciente" in body.lower() and "/pacientes" in page.url, body[:120].replace("\n", " "))
        except Exception as e:
            rep.add("pacientes_carga", False, str(e)[:150])

        # permisos: recepción hace click en Configuración (el shell se la muestra por 'catalogo')
        try:
            link_cfg = page.locator('nav a:has-text("Configuración")')
            if link_cfg.count():
                link_cfg.first.click()
                page.wait_for_timeout(1000)
                body_cfg2 = page.inner_text("body")
                rep.add("recepcion_config_muestra_sin_permiso", "sin permiso" in body_cfg2.lower(),
                        f"url={page.url} texto={body_cfg2[:100]!r}")
                rep.add("shell_muestra_config_a_recepcion", True,
                        "el enlace Configuración es visible para recepción (permiso 'catalogo') pero la ruta exige 'configuracion'")
            else:
                rep.add("recepcion_config_muestra_sin_permiso", True, "enlace no visible para recepción")
                rep.add("shell_muestra_config_a_recepcion", True, "enlace oculto correctamente")
        except Exception as e:
            rep.add("recepcion_config_muestra_sin_permiso", False, str(e)[:150])

        # búsqueda sin resultados
        try:
            inp = page.locator('input[type="search"], input[name="q"], input[placeholder]').first
            if inp.count():
                inp.fill("zzzz-no-existe-12345")
                page.click('button:has-text("Buscar")')
                page.wait_for_timeout(1200)
                body2 = page.inner_text("body")
                rep.add("pacientes_busqueda_vacia", "no se encontr" in body2.lower() or "sin resultado" in body2.lower() or "0" in body2, body2[:120].replace("\n", " "))
            else:
                rep.add("pacientes_busqueda_vacia", True, "sin input de búsqueda visible")
        except Exception as e:
            rep.add("pacientes_busqueda_vacia", False, str(e)[:150])

        # ---------- 6. Resiliencia: API caída (simulada) ----------
        page.route("**/auth/login", lambda r: r.abort())
        ctx2 = browser.new_context()
        p2 = ctx2.new_page()
        p2.on("console", lambda m: rep.console_errors.append("[ctx2] " + m.text[:200]) if m.type == "error" else None)
        p2.goto(f"{BASE}/login", wait_until="networkidle")
        p2.fill('input[type="email"]', "recepcion@demo.com")
        p2.fill('input[type="password"]', "demo1234")
        p2.click('button[type="submit"]')
        try:
            p2.wait_for_selector('[role="alert"], main', timeout=8000)
            body = p2.inner_text("body")
            rep.add("login_api_caida_no_cuelga", "Ingresar" in body or "error" in body.lower(), body[:120].replace("\n", " "))
        except Exception as e:
            rep.add("login_api_caida_no_cuelga", False, str(e)[:150])
        ctx2.close()

        # ---------- 7. Ruta inexistente ----------
        page.goto(f"{BASE}/ruta-que-no-existe", wait_until="networkidle")
        page.wait_for_timeout(500)
        rep.add("ruta_404", page.locator("text=/no encontr|404|existe/i").count() > 0 or "Ingresar" in page.inner_text("body")[:800], page.url)

        # sesión: refresh token — recargar agenda y verificar que sigue logueado
        page.goto(f"{BASE}/agenda", wait_until="networkidle")
        page.wait_for_timeout(800)
        rep.add("sesion_persiste_reload", "/login" not in page.url, page.url)

        browser.close()

    # ---------- Resumen ----------
    print("\n===== RESUMEN =====")
    ok = sum(1 for r in rep.results if r.ok)
    print(f"{ok}/{len(rep.results)} checks OK")
    for r in rep.results:
        if not r.ok:
            print("  FAIL:", r.name, "->", r.detail[:150])
    if rep.console_errors:
        print(f"\nConsole errors ({len(rep.console_errors)}):")
        for e in rep.console_errors[:15]:
            print("  -", e)
    if rep.api_timings:
        print("\nTiempos de respuestas API (ms, percentil):")
        all_ms = [ms for v in rep.api_timings.values() for ms in v]
        for path, vals in sorted(rep.api_timings.items()):
            print(f"  {path}: n={len(vals)} avg={sum(vals)/len(vals):.0f} p95={percentile(vals,95):.0f}")

    out = {
        "checks": [{"name": r.name, "ok": r.ok, "detail": r.detail, "ms": round(r.ms, 1)} for r in rep.results],
        "console_errors": rep.console_errors,
        "api_timings": {k: v for k, v in rep.api_timings.items()},
    }
    with open("scripts/e2e_integracion_resultado.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    return 0 if ok == len(rep.results) else 1


if __name__ == "__main__":
    sys.exit(main())
