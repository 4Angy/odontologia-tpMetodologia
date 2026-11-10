"""Prueba de carga/volumen contra la API (http://localhost:8000).

Mide latencia (avg/p50/p95/p99), throughput y códigos de error con
concurrencia creciente. NO genera datos de pacientes reales (R14): solo
GETs de lectura y un caso controlado de rate-limit en login.

Uso: python scripts/load_test.py
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import urllib.request
import urllib.error

API = "http://127.0.0.1:8000"


def req(method: str, path: str, body: dict | None = None, token: str | None = None,
        timeout: float = 30.0) -> tuple[int, float]:
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(API + path, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", f"Bearer {token}")
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            resp.read()
            return resp.status, (time.perf_counter() - t0) * 1000
    except urllib.error.HTTPError as e:
        e.read()
        return e.code, (time.perf_counter() - t0) * 1000
    except Exception:
        return 0, (time.perf_counter() - t0) * 1000


def percentil(vals: list[float], p: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    k = (len(s) - 1) * p / 100
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def escenario(nombre: str, fn, n: int, workers: int) -> dict:
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        resultados = list(ex.map(fn, range(n)))
    wall = time.perf_counter() - t0
    lat = [ms for _, ms in resultados]
    codigos: dict[int, int] = {}
    for code, _ in resultados:
        codigos[code] = codigos.get(code, 0) + 1
    ok = codigos.get(200, 0) + codigos.get(201, 0)
    return {
        "escenario": nombre,
        "requests": n,
        "workers": workers,
        "wall_s": round(wall, 2),
        "rps": round(n / wall, 1) if wall else 0,
        "codigos": codigos,
        "exito_pct": round(100 * ok / n, 1),
        "avg_ms": round(statistics.mean(lat), 1) if lat else 0,
        "p50_ms": round(percentil(lat, 50), 1),
        "p95_ms": round(percentil(lat, 95), 1),
        "p99_ms": round(percentil(lat, 99), 1),
        "max_ms": round(max(lat), 1) if lat else 0,
    }


def main() -> int:
    salida: list[dict] = []

    # Token de sesión (consume 1 de los 5 intentos/min de login)
    code, ms = req("POST", "/auth/login",
                   {"email": "recepcion@demo.com", "password": "demo1234"})
    token = None
    if code == 200:
        import urllib.request as u
        r = u.Request(API + "/auth/login", method="POST",
                      data=json.dumps({"email": "recepcion@demo.com", "password": "demo1234"}).encode(),
                      headers={"Content-Type": "application/json"})
        # re-login consume otro intento; mejor parsear la primera respuesta
    # rehacer login guardando body
    r = urllib.request.Request(API + "/auth/login", method="POST",
                               data=json.dumps({"email": "recepcion@demo.com", "password": "demo1234"}).encode(),
                               headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            token = json.loads(resp.read())["access_token"]
    except Exception as e:
        print("no se pudo obtener token:", e)
        return 1
    print("token ok")

    hoy = date.today().isoformat()

    # 1. Health (sin auth, sin DB pesada)
    salida.append(escenario("GET /health x200 w20", lambda _: req("GET", "/health"), 200, 20))
    salida.append(escenario("GET /health x500 w50", lambda _: req("GET", "/health"), 500, 50))

    # 2. Agenda del día (auth, query a Postgres)
    if token:
        salida.append(escenario("GET /agenda/dia x100 w10",
                                lambda _: req("GET", f"/agenda/dia?fecha={hoy}", token=token), 100, 10))
        salida.append(escenario("GET /agenda/dia x300 w30",
                                lambda _: req("GET", f"/agenda/dia?fecha={hoy}", token=token), 300, 30))
        salida.append(escenario("GET /pacientes x100 w10",
                                lambda _: req("GET", "/pacientes", token=token), 100, 10))
        salida.append(escenario("GET /pacientes?q=x x100 w20",
                                lambda _: req("GET", "/pacientes?q=a", token=token), 100, 20))

    # 3. Disponibilidad pública (rate limit 60/min por IP -> esperar 429)
    salida.append(escenario("GET /r/demo x80 w10",
                            lambda _: req("GET", "/r/demo"), 80, 10))

    # 4. Login: rate limit 5/60s por IP+email -> esperar 429 tras 5
    salida.append(escenario("POST /auth/login x15 w5",
                            lambda _: req("POST", "/auth/login",
                                          {"email": "recepcion@demo.com", "password": "demo1234"}), 15, 5))

    # 5. Endpoint inexistente / error handling bajo carga
    salida.append(escenario("GET /no-existe x100 w20",
                            lambda _: req("GET", "/definitivamente-no-existe"), 100, 20))

    print("\n===== RESULTADOS =====")
    for s in salida:
        print(json.dumps(s, ensure_ascii=False))
    with open("scripts/load_test_resultado.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
