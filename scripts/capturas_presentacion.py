"""Capturas de pantalla para la presentacion del TPI.

Requiere: API en :8000 y frontend dev en :5174 (o ajustar BASE).
Salida: docs/presentacion/capturas/*.png
"""
import os
from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE_URL", "http://localhost:5174")
OUT = os.path.join(os.path.dirname(__file__), "..", "docs", "presentacion", "capturas")
os.makedirs(OUT, exist_ok=True)


def shot(page, name):
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)
    path = os.path.join(OUT, name + ".png")
    page.screenshot(path=path, full_page=False)
    print("OK", name, "->", page.url)


def ir(page, ruta, name):
    page.goto(BASE + ruta)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)
    if "no encontrada" in page.inner_text("body").lower():
        print("OJO: posible 404 en", name, page.url)
    shot(page, name)


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 810})

    # Login
    page.goto(BASE + "/login")
    page.wait_for_load_state("networkidle")
    shot(page, "01-login")
    page.fill('input[type="email"], input[name="email"]', "dueno@demo.com")
    page.fill('input[type="password"]', "demo1234")
    page.click('button[type="submit"]')
    try:
        page.wait_for_url("**/agenda**", timeout=15000)
        print("login OK ->", page.url)
    except Exception:
        alert = page.locator('[role="alert"]').inner_text() if page.locator('[role="alert"]').count() else "(sin alerta)"
        print("LOGIN FALLO:", alert, page.url)
        raise SystemExit(1)
    page.wait_for_timeout(1500)

    ir(page, "/agenda", "02-agenda")

    # Vista semana: muestra los turnos demo (el dia puede estar vacio)
    try:
        page.click('button:has-text("Semana")', timeout=4000)
        page.wait_for_timeout(1500)
        page.screenshot(path=os.path.join(OUT, "02b-agenda-semana.png"))
        print("OK agenda-semana ->", page.url)
    except Exception as e:
        print("agenda-semana fallo:", e)

    ir(page, "/pacientes", "03-pacientes")
    ir(page, "/caja", "04-caja")
    ir(page, "/transparencia", "05-auditoria")

    # Reserva publica (sin login, otra pestana limpia)
    pub = browser.new_page(viewport={"width": 1440, "height": 810})
    pub.goto(BASE + "/r/demo")
    pub.wait_for_load_state("networkidle")
    pub.wait_for_timeout(800)
    pub.screenshot(path=os.path.join(OUT, "06-reserva-publica.png"))
    print("OK reserva-publica")
    pub.close()

    # Swagger
    api = browser.new_page(viewport={"width": 1440, "height": 810})
    api.goto("http://127.0.0.1:8000/docs")
    api.wait_for_load_state("networkidle")
    api.wait_for_timeout(800)
    api.screenshot(path=os.path.join(OUT, "07-swagger.png"))
    print("OK swagger")

    browser.close()
print("Listo ->", OUT)
