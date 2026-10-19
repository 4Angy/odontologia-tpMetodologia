#!/usr/bin/env python3
"""Genera un PDF a partir de un markdown, con el mismo estilo que los PDFs
del TP (docs/skills-mcp/TP-*.pdf).

Estilo (medido sobre `TP-aplicacion-puntos-5-a-6.pdf`):
  - A4 (595.28 x 841.89 pt), margen izquierdo 45.35 pt
  - Helvetica-Bold 16 (titulo), 14 (subtitulo), 12 (H2), 11 (H3)
  - Helvetica 10 (cuerpo), Courier 9 (bloques de codigo)
  - WinAnsiEncoding (CP1252), interlineado 15.59 pt
  - Aplanado de markdown: los codigos deNeighbors se sustituyen por
    "[bloque de codigo]", se quitan los `#` de los titulos y se conserva el
    resto del texto tal cual (negritas, backticks, guiones y tablas).

Uso:
  python md2pdf.py <entrada.md> <salida.pdf> ["Titulo"] ["Subtitulo"]
"""
from __future__ import annotations

import re
import sys
import zlib
from pathlib import Path

# --- Geometria (medida sobre el PDF de referencia) ---
PAGE_W, PAGE_H = 595.28, 841.89
MARGIN_X = 45.35
TOP_Y = 781.81
BOTTOM_Y = 60.0
LINE_H = 15.59
WRAP_CHARS = 96  # aprox. 10pt Helvetica sobre 505pt utiles

# --- Sustituciones para ganar compatibilidad con CP1252 ---
TRANSLIT = {
    "→": "->", "←": "<-", "↔": "<->", "⇒": "=>", "✓": "OK", "✔": "OK",
    "⚠": "!", "…": "...", "‑": "-", "–": "-", "—": "-",
    "•": "*", "‘": "'", "’": "'", "“": '"', "”": '"',
    "≥": ">=", "≤": "<=", "≠": "!=", "×": "x", "·": "-",
    "│": "|", "─": "-", "┌": "+", "┐": "+", "└": "+", "┘": "+",
    "├": "+", "┤": "+", "┬": "+", "┴": "+", "┼": "+", "▸": ">",
    "◀": "<", "▲": "^", "▼": "v", "«": '"', "»": '"',
    "°": "o", "±": "+/-", "€": "EUR", "“": '"',
}


def sanitize(text: str) -> str:
    for origen, destino in TRANSLIT.items():
        text = text.replace(origen, destino)
    return text


def flatten(markdown: str) -> list[tuple[str, str]]:
    """Convierte markdown en una lista de (tipo, texto) planos.

    tipo: 'title' | 'subtitle' | 'h2' | 'h3' | 'body' | 'code' | 'meta'
    """
    lineas: list[tuple[str, str]] = []
    en_codigo = False
    for cruda in markdown.splitlines():
        linea = cruda.rstrip()
        if linea.strip().startswith("```"):
            en_codigo = not en_codigo
            if en_codigo:
                lineas.append(("code", "[bloque de codigo]"))
            continue
        if en_codigo:
            continue
        if not linea.strip():
            lineas.append(("body", ""))
            continue
        if linea.startswith("# "):
            lineas.append(("title", sanitize(linea[2:].strip())))
        elif linea.startswith("## "):
            lineas.append(("subtitle", sanitize(linea[3:].strip())))
        elif linea.startswith("### "):
            lineas.append(("h2", sanitize(linea[4:].strip())))
        elif linea.startswith("#### "):
            lineas.append(("h3", sanitize(linea[5:].strip())))
        else:
            # "**Proyecto**" / "**Fecha**" como lineas de metadato
            if re.match(r"^\*\*(Proyecto|Fecha|Change revisado|Alcance)\*\*", linea.strip()):
                lineas.append(("meta", sanitize(linea.strip())))
            else:
                lineas.append(("body", sanitize(linea)))
    return lineas


def wrap(texto: str, ancho: int = WRAP_CHARS) -> list[str]:
    if not texto:
        return [""]
    palabras = texto.split(" ")
    lineas: list[str] = []
    actual = ""
    for palabra in palabras:
        candidata = f"{actual} {palabra}".strip()
        if len(candidata) <= ancho:
            actual = candidata
        else:
            if actual:
                lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas


def paginar(bloques: list[tuple[str, str]]) -> list[list[tuple[str, float, str]]]:
    """Devuelve paginas con (texto, y, fuente) por linea."""
    paginas: list[list[tuple[str, float, str]]] = []
    pagina: list[tuple[str, float, str]] = []
    y = TOP_Y

    for tipo, texto in bloques:
        if tipo == "title":
            fuente, tam, antes, despues = "F1", 16.0, 0.0, 10.0
        elif tipo == "subtitle":
            fuente, tam, antes, despues = "F1", 14.0, 0.0, 9.0
        elif tipo == "h2":
            fuente, tam, antes, despues = "F1", 12.0, 6.0, 7.0
        elif tipo == "h3":
            fuente, tam, antes, despues = "F1", 11.0, 5.0, 4.0
        elif tipo == "meta":
            fuente, tam, antes, despues = "F1", 10.0, 0.0, 0.0
        elif tipo == "code":
            fuente, tam, antes, despues = "F3", 9.0, 2.0, 2.0
        else:
            fuente, tam, antes, despues = "F2", 10.0, 0.0, 0.0

        y -= antes
        for parte in wrap(texto, WRAP_CHARS if fuente != "F3" else WRAP_CHARS + 12):
            if y < BOTTOM_Y:
                paginas.append(pagina)
                pagina = []
                y = TOP_Y
            if parte:
                pagina.append((parte, y, fuente))
            y -= LINE_H if fuente != "F3" else LINE_H - 1.0
        y -= despues
        if y < BOTTOM_Y:
            paginas.append(pagina)
            pagina = []
            y = TOP_Y

    if pagina:
        paginas.append(pagina)
    return paginas


def escape_pdf(texto: str) -> str:
    texto = texto.encode("cp1252", errors="replace").decode("cp1252")
    return (
        texto.replace("\\", r"\\")
        .replace("(", r"\(")
        .replace(")", r"\)")
    )


def build_pdf(paginas: list[list[tuple[str, float, str]]]) -> bytes:
    objetos: list[bytes] = []

    # 1: Catalog, 2: Pages, 3: F1, 4: F2, 5: F3, 6..: page+content
    n_paginas = len(paginas)
    kids = " ".join(f"{6 + 2 * i} 0 R" for i in range(n_paginas))
    objetos.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objetos.append(f"<< /Type /Pages /Kids [{kids}] /Count {n_paginas} >>".encode("latin-1"))
    for base in (b"Helvetica-Bold", b"Helvetica", b"Courier"):
        objetos.append(
            b"<< /Type /Font /Subtype /Type1 /BaseFont /"
            + base
            + b" /Encoding /WinAnsiEncoding >>"
        )

    for i, pagina in enumerate(paginas):
        partes = [b"BT"]
        fuente_actual = ""
        for texto, y, fuente in pagina:
            if fuente != fuente_actual:
                partes.append(f"/{fuente} {16 if fuente == 'F1' else (9 if fuente == 'F3' else 10)} Tf".encode("latin-1"))
                fuente_actual = fuente
            partes.append(
                f"1 0 0 1 {MARGIN_X:.2f} {y:.2f} Tm ({escape_pdf(texto)}) Tj".encode("latin-1")
            )
        partes.append(b"ET")
        contenido = zlib.compress(b"\n".join(partes))
        objetos.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] "
                f"/Resources << /Font << /F1 3 0 R /F2 4 0 R /F3 5 0 R >> >> "
                f"/Contents {7 + 2 * i} 0 R >>"
            ).encode("latin-1")
        )
        objetos.append(
            b"<< /Length " + str(len(contenido)).encode() + b" /Filter /FlateDecode >>\nstream\n"
            + contenido + b"\nendstream"
        )

    salida = bytearray(b"%PDF-1.3\n%\xe9\xeb\xf1\xbf\n")
    offsets = [0]
    for numero, objeto in enumerate(objetos, start=1):
        offsets.append(len(salida))
        salida += f"{numero} 0 obj\n".encode("latin-1") + objeto + b"\nendobj\n"

    xref = len(salida)
    salida += f"xref\n0 {len(objetos) + 1}\n".encode("latin-1")
    salida += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        salida += f"{off:010d} 00000 n \n".encode("latin-1")
    salida += (
        f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    ).encode("latin-1")
    return bytes(salida)


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    origen = Path(sys.argv[1])
    destino = Path(sys.argv[2])
    markdown = origen.read_text(encoding="utf-8")
    bloques = flatten(markdown)
    paginas = paginar(bloques)
    destino.write_bytes(build_pdf(paginas))
    print(f"{destino} -> {len(paginas)} paginas, {destino.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
