"""Genera la guia PDF 'levantar-local' en la carpeta Descargas."""
import os

from fpdf import FPDF

OUT = os.path.join(os.path.expanduser("~"), "Downloads", "guia-levantar-sistema.pdf")


class PDF(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 9)
        self.set_text_color(120)
        self.cell(0, 8, "Consultorio Odontologico - Guia para levantar el sistema local", align="R", new_x="LMARGIN", new_y="NEXT")
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)

    def footer(self):
        self.set_y(-12)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(120)
        self.cell(0, 8, f"Pagina {self.page_no()}/{{nb}}", align="C")

    def h1(self, txt):
        self.set_font("helvetica", "B", 15)
        self.set_text_color(20, 60, 110)
        self.multi_cell(0, 8, txt)
        self.ln(1)

    def h2(self, txt):
        self.set_font("helvetica", "B", 12)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 7, txt)
        self.ln(0.5)

    def p(self, txt):
        self.set_font("helvetica", "", 10)
        self.set_text_color(30)
        self.multi_cell(0, 5.5, txt)
        self.ln(1)

    def bullet(self, txt):
        self.set_font("helvetica", "", 10)
        self.set_text_color(30)
        self.multi_cell(0, 5.5, "  - " + txt)
        self.ln(0.5)

    def code(self, txt):
        self.set_font("courier", "", 8)
        self.set_fill_color(240, 240, 240)
        self.set_text_color(20)
        self.multi_cell(0, 4.4, txt, fill=True)
        self.ln(1.5)

    def note(self, txt):
        self.set_font("helvetica", "I", 9.5)
        self.set_text_color(140, 70, 0)
        self.multi_cell(0, 5.5, "Nota: " + txt)
        self.ln(1)


pdf = PDF()
pdf.alias_nb_pages()
pdf.set_auto_page_break(auto=True, margin=18)
pdf.add_page()

pdf.h1("Levantar el sistema - Guia rapida")
pdf.p("SaaS de gestion para consultorios odontologicos (FastAPI + React + Postgres + Redis).")

pdf.h2("Requisitos")
pdf.bullet("Docker Desktop abierto")
pdf.bullet("Python 3.12+ (backend)")
pdf.bullet("Node.js 20+ y npm (frontend)")
pdf.ln(2)

pdf.h2("1. Clonar el proyecto")
pdf.code("git clone https://github.com/juliiirnr-hash/odontologia-tpMetodologia.git\ncd odontologia-tpMetodologia")

pdf.h2("2. Base de datos y Redis (Docker)")
pdf.p("Abrir Docker Desktop. En PowerShell cada comando va en UNA SOLA LINEA (el simbolo ^ no funciona en PowerShell):")
pdf.code(
    "docker run -d --name odonto-pg -e POSTGRES_USER=odontologia -e POSTGRES_PASSWORD=odontologia "
    "-e POSTGRES_DB=odontologia -p 5432:5432 postgres:16\n\n"
    "docker run -d --name odonto-redis -p 6379:6379 redis:7"
)
pdf.note("Si los contenedores ya existen: 'docker start odonto-pg odonto-redis'. "
         "Si el puerto 5432 esta ocupado, cambiar a -p 5433:5432 y ajustar DATABASE_URL.")

pdf.h2("3. Backend (FastAPI)")
pdf.p("En una terminal de PowerShell:")
pdf.code(
    "cd backend\n"
    "python -m venv .venv\n"
    ".\\.venv\\Scripts\\Activate.ps1\n"
    "pip install -r requirements.txt"
)
pdf.note("Si Activate.ps1 falla por politica de ejecucion, correr antes: "
         "Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass")
pdf.p("Migraciones:")
pdf.code(
    "$env:DATABASE_URL=\"postgresql+psycopg://odontologia:odontologia@localhost:5432/odontologia\"\n"
    "python -m alembic upgrade head"
)
pdf.p("Levantar la API (dejar esta terminal abierta):")
pdf.code(
    "$env:DATABASE_URL=\"postgresql+psycopg://odontologia:odontologia@localhost:5432/odontologia\"\n"
    "$env:REDIS_URL=\"redis://localhost:6379/0\"\n"
    "$env:JWT_SECRET=\"secreto-de-prueba-local-0123456789abcdef\"\n"
    "$env:SEED_DEMO=\"true\"\n"
    "python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
)
pdf.note("En cmd.exe usar 'set NOMBRE=valor'; en Mac/Linux usar 'export NOMBRE=valor'.")

pdf.h2("4. Frontend (React + Vite)")
pdf.p("En OTRA terminal de PowerShell:")
pdf.code(
    "cd frontend\n"
    "npm install\n"
    "npm run dev"
)
pdf.p("Abrir en el navegador: http://localhost:5173")

pdf.h2("5. Entrar al sistema")
pdf.bullet("recepcion@demo.com  /  demo1234   (recepcion)")
pdf.bullet("dueno@demo.com      /  demo1234   (dueno: ve auditoria, usuarios, config)")
pdf.bullet("odontologo@demo.com /  demo1234   (odontologo)")
pdf.bullet("multi@demo.com      /  demo1234   (todos los roles)")
pdf.ln(2)

pdf.h2("URLs utiles")
pdf.bullet("App (frontend):      http://localhost:5173")
pdf.bullet("API (backend):       http://localhost:8000")
pdf.bullet("Swagger (docs API):  http://localhost:8000/docs")
pdf.bullet("Reserva publica:     http://localhost:5173/r/demo  (sin login)")

pdf.h2("Si el login falla")
pdf.p(
    "Los usuarios demo se crean sin contrasena. Asignarla una vez con este "
    "script (dentro de backend/, con el entorno virtual activo):"
)
pdf.code(
    "python -c \"from sqlalchemy import create_engine; from sqlalchemy.orm import Session; "
    "from app.core.tenancy.models import UsuarioModel; from app.modules.auth.passwords import hash_password; "
    "e=create_engine('postgresql+psycopg://odontologia:odontologia@localhost:5432/odontologia'); "
    "s=Session(e); "
    "[setattr(u,'password_hash',hash_password('demo1234')) for u in s.query(UsuarioModel).filter(UsuarioModel.email.like('%@demo.com'))]; "
    "s.commit()\""
)

pdf.h2("Verificar que todo funciona")
pdf.bullet("Health check:   curl http://localhost:8000/health")
pdf.bullet("Tests backend: cd backend; python -m pytest")
pdf.bullet("Tests frontend: cd frontend; npm test")

pdf.ln(4)
pdf.set_font("helvetica", "I", 9)
pdf.set_text_color(100)
pdf.multi_cell(0, 5.5,
    "Datos 100% sinteticos/demostrativos (R14). Nunca subir .env ni secretos reales al repo.")

pdf.output(OUT)
print("OK ->", OUT)
