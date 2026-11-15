"""Genera la presentacion PPTX del TPI (version liviana, soporte del video).

Salida: ~/Downloads/presentacion-tpi-odontologia.pptx
"""
import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

OUT = os.path.join(os.path.expanduser("~"), "Downloads", "presentacion-tpi-odontologia.pptx")

AZUL = RGBColor(0x1F, 0x4E, 0x79)
GRIS = RGBColor(0x59, 0x59, 0x59)
BLANCO = RGBColor(0xFF, 0xFF, 0xFF)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]


def slide():
    return prs.slides.add_slide(BLANK)


def caja(s, l, t, w, h, fill=None):
    sh = s.shapes.add_shape(1, Inches(l), Inches(t), Inches(w), Inches(h))
    if fill is None:
        sh.fill.background()
    else:
        sh.fill.solid()
        sh.fill.fore_color.rgb = fill
    sh.line.fill.background()
    return sh


def texto(s, l, t, w, h, items, align=PP_ALIGN.LEFT):
    """items: lista de (texto, bold, size, color) o listas de runs."""
    tb = s.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(10)
        runs = item if isinstance(item, list) else [item]
        for txt, b, sz, c in runs:
            r = p.add_run()
            r.text = txt
            r.font.size = Pt(sz)
            r.font.bold = b
            r.font.color.rgb = c
            r.font.name = "Calibri"
    return tb


def titulo(s, txt, sub=None):
    caja(s, 0, 0, 13.333, 0.9, AZUL)
    texto(s, 0.5, 0.12, 12.3, 0.7, [[(txt, True, 28, BLANCO)]])
    if sub:
        texto(s, 0.5, 0.98, 12.3, 0.5, [[(sub, False, 14, GRIS)]])


def tabla(s, l, t, w, h, datos, col_w=None, size=15):
    rows, cols = len(datos), len(datos[0])
    shp = s.shapes.add_table(rows, cols, Inches(l), Inches(t), Inches(w), Inches(h))
    t_ = shp.table
    if col_w:
        for i, cw in enumerate(col_w):
            t_.columns[i].width = Inches(cw)
    for ri, row in enumerate(datos):
        for ci, val in enumerate(row):
            cell = t_.cell(ri, ci)
            cell.text = str(val)
            for p in cell.text_frame.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(size if ri else size + 1)
                    r.font.name = "Calibri"
                    r.font.bold = (ri == 0)
                    r.font.color.rgb = BLANCO if ri == 0 else GRIS
            if ri == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = AZUL
    return t_


def divisor(letra, subtitulo, quien, tiempo):
    s = slide()
    caja(s, 0, 0, 13.333, 7.5, AZUL)
    texto(s, 0.8, 2.4, 11.7, 1.4, [[(letra, True, 44, BLANCO)]])
    texto(s, 0.8, 3.7, 11.7, 1.0, [
        [(subtitulo, False, 26, RGBColor(0xBF, 0xD7, 0xEE))],
        [(quien + "  ·  " + tiempo, False, 18, BLANCO)],
    ])
    return s


# 1. Portada
s = slide()
caja(s, 0, 0, 13.333, 7.5, AZUL)
texto(s, 0.8, 2.2, 11.7, 1.6, [[("Consultorio Odontológico SaaS", True, 44, BLANCO)]])
texto(s, 0.8, 3.6, 11.7, 0.8, [[("Del proyecto fundado al sistema funcionando", False, 24, RGBColor(0xBF, 0xD7, 0xEE))]])
texto(s, 0.8, 4.9, 11.7, 1.2, [
    [("Metodología I · Trabajo Práctico Integrador", False, 18, BLANCO)],
    [("Herrera, Julieta  ·  Zalazar, María de los Ángeles", False, 18, BLANCO)],
    [("github.com/4Angy/odontologia-tpMetodologia", False, 16, RGBColor(0xBF, 0xD7, 0xEE))],
])

# 2. Qué pide la consigna
s = slide()
titulo(s, "Qué pide la consigna")
texto(s, 0.8, 1.6, 11.7, 4.5, [
    [("Cambios completos explicados y probados", True, 22, AZUL)],
    [("Sistema levantado y funcionando", True, 22, AZUL)],
    [("Skill propia + servidor MCP, con su aporte concreto", True, 22, AZUL)],
    [("Video de hasta 10 minutos · todos los integrantes hablan", False, 17, GRIS)],
])

# 3. Reparto
s = slide()
titulo(s, "Reparto")
tabla(s, 1.2, 2.0, 10.9, 2.6, [
    ["Parte", "Quién", "Contenido", "Tiempo"],
    ["A", "Integrante 1 (skill)", "Apertura, changes de la base (Cancelar turno, C-01 a C-06) y la skill visual-explore-options", "4,5 min"],
    ["B", "Integrante 2 (MCP)", "Changes de agenda a cierre (C-07 a C-13 y pulido), los dos MCP y la demo del sistema", "5,5 min"],
], col_w=[1.0, 2.4, 6.3, 1.4], size=14)

# 4. Skill y MCP: mismo change
s = slide()
titulo(s, "Skill y MCP: mismo change")
texto(s, 0.8, 1.5, 11.7, 1.0, [
    [("La skill ordena la decisión de diseño; el MCP la respalda con evidencia real.", False, 18, GRIS)],
])
tabla(s, 0.8, 2.7, 11.7, 3.0, [
    ["Change", "Skill (visual-explore-options)", "MCP", "Aporte del MCP"],
    ["C-02 tenancy", "4 ejes explorados, 2 opciones c/u", "filesystem", "La decisión de roles citó la KB: cita, no preferencia"],
    ["C-09 notificaciones", "6 ejes, pausa para elegir", "Redis", "Verificó durabilidad real: cola en Postgres + lock con TTL"],
], col_w=[2.6, 3.7, 1.6, 3.8], size=13)

# 5. Tests
divisor_texto = None
s = slide()
caja(s, 1.5, 2.6, 10.3, 2.0, RGBColor(0xEA, 0xF2, 0xF8))
texto(s, 1.8, 3.0, 9.7, 1.4, [
    [("TDD + Postgres 16 real · un esquema por test", False, 22, AZUL)],
    [("Backend: 219 tests   ·   Frontend: 64 tests", True, 24, AZUL)],
], align=PP_ALIGN.CENTER)

# 6. Divisor A
divisor("PARTE A", "Base del sistema y la skill", "Integrante 1", "4,5 minutos")

# 7. Apertura
s = slide()
titulo(s, "Apertura")
texto(s, 0.8, 1.6, 11.7, 3.0, [
    [("SaaS multi-tenant para consultorios odontológicos: agenda con recordatorios por WhatsApp, ", False, 20, GRIS)],
    [("caja y seña por Mercado Pago. 15 changes archivados con OpenSpec.", False, 20, GRIS)],
])
caja(s, 0.8, 4.9, 11.7, 1.3, RGBColor(0xF2, 0xF2, 0xF2))
texto(s, 1.0, 5.15, 11.3, 0.9, [
    [("openspec/changes/archive/   ·   CHANGES.md", False, 15, GRIS)],
])

# 8. Changes base
s = slide()
titulo(s, "Changes de la base", "Cancelar turno · C-01 a C-06")
tabla(s, 0.8, 1.4, 11.7, 4.6, [
    ["Change", "Qué hizo", "Cómo se probó"],
    ["Cancelar turno", "Regla de antelación (RN-AG-01) y liberar horario", "26/26 tareas; tests con código de error"],
    ["C-01 foundation", "Config, health check, errores con código, CI y compose; ADRs", "53/53 tareas; CI en verde"],
    ["C-02 tenancy", "Aislamiento por tenant_id (R1)", "Postgres real; migración up/down/up; 13 escenarios"],
    ["C-03 auth y RBAC", "Login, refresh con rotación, roles acumulables", "Tests por rol y reutilización de token"],
    ["C-04 pacientes", "CRUD, opt-in WhatsApp, CSV", "Tests + samples/pacientes-demo.csv"],
    ["C-05 ficha clínica", "Evoluciones, adjuntos, presupuestos y saldo", "Tests y pantalla en React"],
    ["C-06 catálogo", "Profesionales, prestaciones, bloqueos", "Tests de tenancy cruzada"],
], col_w=[2.4, 5.6, 3.7], size=13)

# 9. Nota C-02
s = slide()
caja(s, 1.2, 2.8, 10.9, 1.8, RGBColor(0xFB, 0xF3, 0xE2))
texto(s, 1.5, 3.1, 10.3, 1.3, [
    [("C-02 es el change crítico: un filtro mal puesto expone datos entre consultorios.", True, 19, RGBColor(0x8A, 0x5A, 0x00))],
    [("Por eso se probó con Postgres real: SQLite no valida claves foráneas.", False, 16, GRIS)],
])

# 10. Skill
s = slide()
titulo(s, "La skill creada", "visual-explore-options · 1,5 min")
texto(s, 0.8, 1.5, 11.7, 4.5, [
    [("Fase explore: ≥2 alternativas con esquema ASCII y pausa hasta que el usuario elija, antes de design.md.", False, 17, GRIS)],
    [("Creada con skill-creator: 15/15 criterios con skill vs 6/15 sin ella.", False, 17, GRIS)],
    [("Registrada en .atl/skill-registry.md y AGENTS.md.", False, 17, GRIS)],
    [("Evidencia: explore-c02 y explore-c09 — la pausa se respetó.", False, 17, GRIS)],
])

# 11. Divisor B
divisor("PARTE B", "Agenda a cierre, MCP y demo", "Integrante 2", "5,5 minutos")

# 12. Changes agenda a cierre
s = slide()
titulo(s, "Changes de agenda a cierre", "C-07 a C-13 + pulido frontend")
tabla(s, 0.8, 1.35, 11.7, 4.6, [
    ["Change", "Qué hizo", "Cómo se probó"],
    ["C-07 turnos", "Agenda día/semana, sin dobles reservas, auditoría", "Tests de concurrencia e idempotencia"],
    ["C-08 reserva pública", "Página /r/:slug, tokens con hash, rate limit", "Tests de expiración y revocación"],
    ["C-09 notificaciones", "Recordatorios T-48h/T-24h, cola durable, anti-spam", "27/28 tareas; test_c09_core.py"],
    ["C-10 lista de espera", "Oferta al primero elegible con TTL de 2 h", "Tests de la máquina de estados"],
    ["C-11 caja", "Cobros manuales y cierre; montos en centavos (R5)", "Tests de saldo y cierre"],
    ["C-12 señas MP", "Mercado Pago + webhook idempotente (R8)", "Tests con cliente falso"],
    ["C-13 hardening", "Auditoría con rol activo, rate limit Redis, seed", "Informe integración y carga"],
    ["Frontend polish", "Estilos globales y campo de monto en caja", "14/14 tareas"],
], col_w=[2.4, 5.6, 3.7], size=12)

# 13. MCPs
s = slide()
titulo(s, "Los dos MCP")
texto(s, 0.8, 1.5, 11.7, 4.5, [
    [("MCP filesystem", True, 20, AZUL)],
    [("Lee archivos del proyecto sin salir del chat. Usado en C-02 para citar la KB en la decisión de roles.", False, 16, GRIS)],
    [("MCP Redis", True, 20, AZUL)],
    [("Inspecciona claves, colas y jobs (redis_health, redis_scan, redis_get). Usado en C-09 para verificar durabilidad y el lock con TTL.", False, 16, GRIS)],
    [("MCPs existentes, sin credenciales ni servicios pagos. Configuración reproducible en docs/skills-mcp/.", False, 16, GRIS)],
])

# 14. Sistema levantado / demo en video
s = slide()
titulo(s, "Sistema levantado", "Demo en video · 3 min")
texto(s, 0.8, 1.4, 11.7, 0.8, [
    [("docker compose up -d  ·  /health/ready  ·  npm run dev → localhost:5173", False, 13, GRIS)],
])
tabla(s, 0.8, 2.2, 11.7, 4.0, [
    ["Paso", "Qué se demuestra"],
    ["Login como dueno@demo.com", "Auth y roles (C-03)"],
    ["Agenda: crear un turno", "Sin doble reserva (C-07)"],
    ["Reserva pública /r/demo", "Token (C-08) + seña (C-12)"],
    ["Cancelar un turno", "Lista de espera (C-10)"],
    ["Caja: registrar un cobro", "Caja manual (C-11)"],
    ["Auditoría + redis_health", "Rol activo (C-13) + MCP"],
], col_w=[5.5, 6.2], size=15)

# 15. Evidencia: capturas reales del sistema
CAPTURAS = os.path.join(os.path.dirname(__file__), "..", "docs", "presentacion", "capturas")
s = slide()
titulo(s, "El sistema en pantalla")
grilla = [
    ("02b-agenda-semana.png", "Agenda y turnos"),
    ("03-pacientes.png", "Pacientes y ficha"),
    ("04-caja.png", "Caja y cobros"),
    ("05-auditoria.png", "Auditoría"),
    ("06-reserva-publica.png", "Reserva pública"),
    ("07-swagger.png", "API (Swagger)"),
]
cols, fijas = 3, 2
margen, gap = 0.5, 0.25
ancho = (13.333 - 2 * margen - (cols - 1) * gap) / cols
alto = (7.5 - 1.5 - (fijas - 1) * gap) / fijas
for i, (img, pie) in enumerate(grilla):
    path = os.path.join(CAPTURAS, img)
    if not os.path.exists(path):
        continue
    f = i % cols
    g = i // cols
    l = margen + f * (ancho + gap)
    t = 1.35 + g * (alto + gap)
    s.shapes.add_picture(path, Inches(l), Inches(t), width=Inches(ancho))
    texto(s, l, t + alto - 0.05, ancho, 0.35, [[(pie, False, 11, GRIS)]], align=PP_ALIGN.CENTER)

# 16. Cierre
s = slide()
caja(s, 1.2, 2.8, 10.9, 1.9, RGBColor(0xEA, 0xF2, 0xF8))
texto(s, 1.5, 3.1, 10.3, 1.4, [
    [("15 changes archivados · 219 tests backend · 64 frontend · sistema corriendo.", False, 20, AZUL)],
    [("La skill ordena las decisiones; los MCP las respaldan con evidencia real.", False, 17, GRIS)],
], align=PP_ALIGN.CENTER)

prs.save(OUT)
print("OK ->", OUT)
