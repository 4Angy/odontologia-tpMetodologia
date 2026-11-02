# Evidencia del uso de `skill-creator` para generar `visual-explore-options`

> **Procedencia de este archivo.** Todo lo que sigue se recuperó el 2026-10-27 de dos fuentes primarias y se copió literal, sin editar:
> 
> 1. La base de sesiones de OpenCode `~/.local/share/opencode/opencode.db` (tabla `session_message`),
>    sesión **`ses_eb9f350c3ffe0HR38j682fmrMj`** — título *«Cómo usar skill-creator»* — del **2026-10-16**.
> 2. Los archivos que esa sesión dejó en disco (`Downloads\visual-explore-options\`,
>    `Downloads\visual-explore-options.md`, `Downloads\visual-explore-options-workspace\`).
>
> Los bloques entre ~~~~ son copia textual. Lo que está fuera de ~~~~ es encuadre mío para que se sepa de dónde sale cada cosa.
> Al final hay una sección de **límites de esta evidencia** con lo que NO se pudo recuperar.

---

## 1. La solicitud

### 1.1 Invocación de la skill

Herramienta `skill` de OpenCode, al inicio de la sesión:

~~~~json
{"id": "skill-creator"}
~~~~

Respuesta inmediata del agente (parte `text` del mismo mensaje):

~~~~
Cargando la guía de skill-creator.
~~~~

### 1.2 Pedido del usuario

Mensaje de usuario de apertura (texto literal del registro):

~~~~
como se usa la skill-creator?
~~~~

Segundo mensaje, con el borrador adjunto:

~~~~
Attached file: `C:\Users\Cara Palida\Downloads\visual-explore-options.md`
~~~~

El adjunto es `~\Downloads\visual-explore-options.md` (4050 bytes, utf-8). Copia literal de ese borrador:

~~~~markdown
# Skill: Visual Explore Options (`visual-explore-options`)

## Propósito
Estandarizar la etapa de exploración (`explore`) del flujo de Spec-Driven Development (SDD), obligando al agente a presentar las opciones técnicas, de arquitectura, de base de datos o de desarrollo de forma sencilla, explicando claramente por qué se elige cada tecnología y cómo se va a utilizar, acompañado de un esquema visual o conceptual antes de que el usuario acepte avanzar.

## Cuándo se Activa
- Al iniciar la fase de exploración de un nuevo *change* que implique decisiones de diseño de componentes, arquitectura de backend, esquemas de bases de datos, APIs o interfaces en el sistema odontológico.

## Entradas Necesarias
- El contexto del change actual (leído desde el archivo `proposal.md` o el roadmap del repositorio).
- Las alternativas viables evaluadas para resolver el requerimiento.

## Procedimiento Operativo del Agente
1. **Identificar Alternativas:** Evaluar al menos dos opciones viables para el change.
2. **Explicitación Práctica:** Explicar de forma sencilla por qué se elige esa tecnología y cómo se va a utilizar en el proyecto.
3. **Generación de Representación Visual o Conceptual:** Diseñar un esquema sencillo en texto o diagrama ASCII (visual para frontend o de flujo/capas para backend).
4. **Presentación Clara:** Mostrar las opciones explicadas de forma súper fácil y directa.
5. **Pausa de Selección Obligatoria:** Solicitar explícitamente al usuario que elija una opción antes de avanzar hacia la fase de diseño (`design.md`).

---

## Ejemplos de Salida Esperada de la Skill

Cuando esta skill se active, el agente estructurará su respuesta explicando el "por qué" y el "cómo" de forma muy sencilla:

### 1. Ejemplo de Salida para Frontend / Interfaz de Usuario:
#### Opción A: Panel de Turnos en Tres Columnas
* **¿Qué es?:** Una pantalla dividida en tres partes para ver el menú a la izquierda, la información en el centro y los botones para elegir turnos a la derecha.
* **Por qué y cómo se va a utilizar:** Usaremos `React` porque nos permite reutilizar componentes de forma modular y mantener el estado de los turnos en tiempo real mediante *hooks*. Para darle diseño y adaptabilidad de manera rápida y limpia, aplicaremos clases utilitarias de `Tailwind CSS`.
* **Esquema Visual (ASCII):**
  ```text
  +-------------------------------------------------------------+
  |                   LAYOUT DE 3 COLUMNAS                      |
  +-------------------+-------------------+---------------------+
  |     SIDEBAR       |    THEORY PANEL   |   ACTION COMPONENT  |
  |  • Paciente A     |  # Gestión Cita   |  Seleccione Turno:  |
  |  ✓ Paciente B     |                   |  o 1) 10:00 hs      |
  +-------------------+-------------------+---------------------+
### 2. Ejemplo de Salida para Backend / Base de Datos / Arquitectura:
Opción B: Endpoints REST con FastAPI y Base de Datos
* **¿Qué es?:** Una estructura donde las peticiones del usuario van directo al servidor ordenadas por rutas, conectándose de forma segura a la base de datos.

* **Por qué y cómo se va a utilizar:** Elegimos FastAPI porque nos ofrece validación automática de datos y documentación interactiva nativa para nuestras rutas de turnos. Se conectará a PostgreSQL estructurando las consultas mediante un mapeo de objetos para mantener limpio el código del servidor.

Esquema Conceptual (ASCII):

Plaintext
[ Cliente HTTP ] ---> ( Servidor / Rutas ) ---> [ Base de Datos ]
[PAUSA OBLIGATORIA]
Por favor, indique qué opción desea aceptar para proceder con la generación del archivo design.md.

Criterios de Revisión del Resultado
Las explicaciones deben justificar claramente el "por qué" y el "cómo" de la tecnología de forma sencilla y directa.

Los esquemas visuales o conceptuales deben mostrarse de forma limpia mediante bloques de código texto/ASCII.

El flujo debe detenerse obligatoriamente a esperar la aprobación del usuario.
~~~~

### 1.3 Pregunta de alcance y de pruebas

Antes de escribir nada, la skill hizo una pausa con la herramienta `question`. Entrada literal:

~~~~json
{
  "questions": [
    {
      "header": "Alcance de la skill",
      "options": [
        {
          "description": "Mantener foco en sistema odontológico, SDD con proposal.md/design.md",
          "label": "Solo odontológico"
        },
        {
          "description": "Generalizar para cualquier proyecto SDD: frontend/backend/DB/API",
          "label": "General SDD"
        },
        {
          "description": "Híbrida: lógica general + ejemplos odontológicos",
          "label": "Híbrida (Recomendado)"
        }
      ],
      "question": "¿Querés la skill solo para el sistema odontológico o general reutilizable?"
    },
    {
      "header": "Test con skill-creator",
      "options": [
        {
          "description": "Probar con 2-3 prompts (uno frontend, uno backend/DB) con y sin skill y revisar en viewer",
          "label": "Sí, crear evals"
        },
        {
          "description": "Solo pulir el SKILL.md y empaquetar sin pruebas",
          "label": "No, solo borrador"
        }
      ],
      "question": "¿Armamos los 2-3 casos de prueba para validar la skill?"
    }
  ]
}
~~~~

Confirmación registrada por el agente en el mensaje siguiente (es el único registro de la respuesta:
la salida de la herramienta `question` no quedó almacenada — ver límites al pie):

~~~~
Perfecto, general SDD + con evals. Armo el SKILL.md corregido y los casos de prueba.
~~~~

---

## 2. Qué produjo

### 2.1 El `SKILL.md` (una sola escritura, 2026-10-16 15:55)

Destino registrado en la llamada `write`: `C:\Users\Cara Palida\Downloads\visual-explore-options\SKILL.md`

Archivo resultante: **~\Downloads\visual-explore-options\SKILL.md** — 3392 bytes, utf-8, SHA-256 `454A839D71C803A38184C8F6CCB7EDAAB71EFB5CB37A7A51CBEC2BB6F3CF5B34`.

Contenido literal:

~~~~markdown
---
name: visual-explore-options
description: Estandariza la fase explore de Spec-Driven Development presentando al menos 2 opciones tecnicas con por-que, como se usa y esquema ASCII, y pausando por seleccion antes de design.md. Usa esta skill siempre que inicies la exploracion de un change que implique decisiones de arquitectura, frontend, backend, base de datos, APIs o componentes, incluso si el usuario no pide explicitamente comparar opciones.
---

# Visual Explore Options

Estandariza la etapa `explore` de SDD. No avances a `design.md` sin seleccion explicita del usuario.

## Cuando activar

Activa cuando:
- Inicias `explore` de un change nuevo con decisiones abiertas, o
- El contexto menciona arquitectura, componentes UI, backend, schema DB, API, o trade-offs tecnicos.

Si el change es trivial (bug de una linea, rename, sin alternativas), explica en 2 lineas por que no hay opciones y pide confirmacion para seguir.

## Entradas

1. Lee el contexto del change: `proposal.md`, `openspec/proposal.md`, `CHANGES.md`, o roadmap del repo. Si no existe, pide: objetivo, restricciones y stack actual.
2. Identifica restricciones duras: stack existente, DB existente, performance, equipo.

## Procedimiento

Sigue estos pasos en orden. Usa forma imperativa y lenguaje simple, sin jerga innecesaria.

### 1. Identifica al menos 2 alternativas viables

Evalua al menos 2 opciones reales. No inventes opciones de relleno. Para cada una indica:
- Que es (1-2 lineas, simple)
- Por que y como se usaria en este proyecto (tecnologia + uso concreto: hooks, validacion, ORM, migraciones, etc.)
- Trade-offs: ventaja principal + costo/riesgo principal

### 2. Genera esquema visual o conceptual ASCII

- Frontend/UI: layout en bloque ASCII dentro de ```text.
- Backend/DB/Arquitectura: flujo en una linea o capas:
  `[ Cliente ] ---> ( Servidor / Rutas ) ---> [ Base de Datos ]`
- Mantenlo pequeno: max 10 lineas, solo cajas y flechas, sin arte complejo.

### 3. Presenta con esta plantilla exacta

Usa SIEMPRE esta plantilla:

```markdown
## Opcion A: [Nombre corto]
* **Que es?:** [1-2 lineas simples]
* **Por que y como:** [tecnologia + por que elegida + como se usa en este change]
* **Trade-off:** Pro: [uno] / Contra: [uno]
* **Esquema:**
```text
[ASCII aqui]
```

## Opcion B: [Nombre corto]
(mismo formato)

## Recomendacion
[1-3 lineas: cual conviene y por que, sin imponer]

[PAUSA OBLIGATORIA]
Indica que opcion deseas (A, B, o combinacion) para generar `design.md`.
```

### 4. Pausa obligatoria

Termina SIEMPRE con la pausa. No generes `design.md`, no escribas codigo, no asumas eleccion. Espera respuesta explicita.

## Criterios de calidad

- Cada opcion justifica por-que y como en lenguaje simple.
- Esquemas en bloque ```text, limpios y cortos.
- Al menos 2 opciones comparables, no una obvia + una absurda.
- Flujo detenido hasta seleccion.

## Ejemplo backend (resumido)

## Opcion A: REST con FastAPI + PostgreSQL
* **Que es?:** Peticiones por rutas ordenadas hacia un servidor que guarda en DB relacional.
* **Por que y como:** FastAPI por validacion automatica y docs interactivas para rutas de turnos. SQLAlchemy como ORM contra PostgreSQL para mantener queries limpias + migraciones con Alembic.
* **Trade-off:** Pro: tipado y rapidez / Contra: requiere modelar schema upfront
* **Esquema:**
```text
[ Cliente HTTP ] ---> ( FastAPI / Rutas ) ---> [ PostgreSQL ]
```
~~~~

### 2.2 Los casos de prueba (`evals.json`)

Destino registrado en la llamada `write`: `C:\Users\Cara Palida\Downloads\visual-explore-options\evals\evals.json`

Archivo resultante: `~\Downloads\visual-explore-options\evals\evals.json` — 1143 bytes, utf-8. Contenido literal (está detallado en `skill-creator-pruebas.md`):

~~~~json
{"evals": [{"expected_output": "Dos opciones UI comparadas con Que es, Por que/como, Trade-off, esquema ASCII 3 columnas o similar, y pausa obligatoria sin generar design.md", "files": [], "id": 0, "prompt": "Estamos en fase explore del change 'pantalla de gestion de turnos': necesitamos mostrar lista de pacientes y huecos disponibles. Stack actual React + Tailwind. Presenta opciones."}, {"expected_output": "Dos opciones backend/DB comparadas (ej SQL vs NoSQL o REST vs alternativa) con por-que/como concreto, esquema flujo ASCII y pausa obligatoria", "files": [], "id": 1, "prompt": "Estamos en fase explore del change 'persistencia de citas y pacientes': 10k citas/mes, consultas por fecha y paciente. Stack FastAPI + PostgreSQL existente pero abierto a alternativas. Presenta opciones."}, {"expected_output": "Dos opciones API/arquitectura comparadas con trade-offs, esquema ASCII y pausa obligatoria", "files": [], "id": 2, "prompt": "Estamos en fase explore del change 'API de pacientes para app movil y web': alta lectura, pocas escrituras, auth necesaria. Presenta opciones de diseno API."}], "skill_name": "visual-explore-options"}
~~~~

### 2.3 Las copias repartidas

Todas las copias existentes hoy del `SKILL.md`, con su hash frente al archivo recién generado:

| Ubicación | Bytes | SHA-256 frente al producido |
|---|---|---|
| `~/.config/opencode/skills/visual-explore-options/SKILL.md` | 3392 | idéntico |
| `.opencode/skills/visual-explore-options/SKILL.md (repo)` | 3392 | idéntico |
| `.claude/skills/visual-explore-options/SKILL.md (repo)` | 3392 | idéntico |
| `.devin/skills/visual-explore-options/SKILL.md (repo)` | 3392 | idéntico |
| `skills/visual-explore-options.md (repo)` | 3392 | idéntico |

---

## 3. Qué se adaptó a mano después

### 3.1 El `SKILL.md` NO se modificó a mano

Busqué en **todas** las sesiones de la base cualquier `write` o `edit` sobre un path `*visual-explore-options*SKILL.md`.
Encontré **1** operación:

| Sesión | seq | Herramienta | Path |
|---|---|---|---|
| `ses_eb9f350c3ffe0HR38j682fmrMj` | 66 | `write` | `C:\Users\Cara Palida\Downloads\visual-explore-options\SKILL.md` |

Es decir: una única escritura (la de §2.1) y ningún `edit` posterior. Lo confirma la tabla de §2.3, donde las
5 copias dan **idénticas** al archivo producido. **El texto de la skill nunca fue corregido a mano después de generarse.**

### 3.2 El empaquetado sí se hizo a mano

Primero se intentó con el script de `skill-creator`:

~~~~powershell
$pkg = python $env:USERPROFILE\.config\opencode\skills\skill-creator\scripts\package_skill.py 'C:\Users\Cara Palida\Downloads\visual-explore-options' --output 'C:\Users\Cara Palida\Downloads'; echo $pkg; ls 'C:\Users\Cara Palida\Downloads\*.skill' | Sort-Object LastWriteTime -Descending | Select-Object -First 3
~~~~

~~~~powershell
python -m scripts.package_skill 'C:\Users\Cara Palida\Downloads\visual-explore-options' --help; echo '---TRY2---'; cd $env:USERPROFILE\.config\opencode\skills\skill-creator; python -m scripts.package_skill 'C:\Users\Cara Palida\Downloads\visual-explore-options' --output 'C:\Users\Cara Palida\Downloads'
~~~~

Después, en los tres mensajes siguientes, se empaquetó a mano con `Compress-Archive`:

~~~~powershell
$srcDir = 'C:\Users\Cara Palida\Downloads\visual-explore-options'; $out = 'C:\Users\Cara Palida\Downloads\visual-explore-options.skill'; if (Test-Path $out) { Remove-Item $out -Force }; Compress-Archive -Path "$srcDir\SKILL.md" -DestinationPath "$out"; ls $out; echo 'OK para enviar'
~~~~

~~~~powershell
$tmp = 'C:\Users\Cara Palida\Downloads\visual-explore-options.zip'; $out = 'C:\Users\Cara Palida\Downloads\visual-explore-options.skill'; if (Test-Path $tmp) { Remove-Item $tmp -Force }; if (Test-Path $out) { Remove-Item $out -Force }; Compress-Archive -Path 'C:\Users\Cara Palida\Downloads\visual-explore-options\SKILL.md' -DestinationPath $tmp; Move-Item -Force $tmp $out; ls $out
~~~~

~~~~powershell
$stage = 'C:\Users\Cara Palida\AppData\Local\Temp\opencode\pkg-stage'; $out = 'C:\Users\Cara Palida\Downloads\visual-explore-options.skill'; Remove-Item -Recurse -Force $stage -ErrorAction SilentlyContinue; New-Item -ItemType Directory -Force -Path "$stage\visual-explore-options" | Out-Null; Copy-Item -Force 'C:\Users\Cara Palida\Downloads\visual-explore-options\SKILL.md' "$stage\visual-explore-options\SKILL.md"; $tmp = "$stage.zip"; if (Test-Path $tmp) { Remove-Item $tmp -Force }; if (Test-Path $out) { Remove-Item $out -Force }; Compress-Archive -Path "$stage\visual-explore-options" -DestinationPath $tmp; Move-Item -Force $tmp $out; python -c "import zipfile; print(zipfile.ZipFile(r'C:\Users\Cara Palida\Downloads\visual-explore-options.skill').namelist())"; ls $out
~~~~

Resultado en disco: `Downloads\visual-explore-options.skill` (1804 bytes, 2026-10-16 16:27) y
`Downloads\visual-explore-options.zip` (2997 bytes, 2026-10-16 18:47).

### 3.3 La instalación / reparto también fue manual

Comando registrado para llevar la skill a este proyecto (incluye las 4 copias del repo):

~~~~powershell
$proj = 'C:\Users\Cara Palida\Documents\projects\odontologia-tpMetodologia'; $src = 'C:\Users\Cara Palida\.config\opencode\skills\visual-explore-options\SKILL.md'; foreach ($d in @("$proj\.opencode\skills\visual-explore-options", "$proj\.devin\skills\visual-explore-options", "$proj\.claude\skills\visual-explore-options", "$proj\docs\skills-mcp")) { New-Item -ItemType Directory -Force -Path $d | Out-Null }; Copy-Item -Force $src "$proj\.opencode\skills\visual-explore-options\SKILL.md"; Copy-Item -Force $src "$proj\.devin\skills\visual-explore-options\SKILL.md"; Copy-Item -Force $src "$proj\.claude\skills\visual-explore-options\SKILL.md"; Copy-Item -Force $src "$proj\skills\visual-explore-options.md"; Copy-Item -Force 'C:\Users\Cara Palida\Downloads\odontologia-tpMetodologia-main\odontologia-tpMetodologia-main\docs\skills-mcp\investigacion.md' "$proj\docs\skills-mcp\investigacion.md"; Copy-Item -Force 'C:\Users\Cara Palida\Downloads\odontologia-tpMetodologia-main\odontologia-tpMetodologia-main\docs\skills-mcp\aplicacion.md' "$proj\docs\skills-mcp\aplicacion.md"; Copy-Item -Force 'C:\Users\Cara Palida\Downloads\odontologia-tpMetodologia-main\odontologia-tpMetodologia-main\docs\skills-mcp\mcp-configuracion.md' "$proj\docs\skills-mcp\mcp-configuracion.md"; foreach ($p in @("$proj\.opencode\skills\visual-explore-options\SKILL.md", "$proj\.devin\skills\visual-explore-options\SKILL.md", "$proj\.claude\skills\visual-explore-options\SKILL.md", "$proj\skills\visual-explore-options.md", "$proj\docs\skills-mcp\investigacion.md", "$proj\docs\skills-mcp\aplicacion.md", "$proj\docs\skills-mcp\mcp-configuracion.md")) { Test-Path $p }
~~~~

---

## 4. Límites de esta evidencia

Cosas que **no** existen y que por lo tanto no puedo mostrar, sin inventarlas:

1. **La salida (stdout) de los comandos no quedó almacenada.** La base guarda los *inputs* de cada herramienta,
   no sus resultados. Puedo mostrar los comandos de §3.2 literalmente, pero **no** el error de `package_skill.py`
   que motivó el paso a `Compress-Archive`: no está registrado y no lo supongo.
2. **La respuesta elegida en la `question` de §1.3 no está guardada** (campo de salida vacío). Lo único registrado es
   la confirmación textual del agente en ese mismo mensaje («Perfecto, general SDD + con evals»).
3. **No hay `grading.json` ni `feedback.json` de iteración 1, ni carpeta `iteration-2/`.** El `review.html` sí existe
   (69758 bytes) y se abrió en la sesión con la herramienta `browser.preview`, pero el `feedback.json` que debería salir
   de esa revisión nunca se escribió en disco, y la iteración 2 propuesta en el mensaje de cierre no se ejecutó.
4. **El borrador original (`visual-explore-options.md`) es una entrada del usuario, no un producto de `skill-creator`.**
   Está acá porque es el insumo de la comparación, no porque lo haya generado la skill.

## 5. Verificación

Comandos que corrí para armar este archivo (2026-10-27), y lo que devolvieron:

- SHA-256 con `Get-FileHash -Algorithm SHA256` sobre el `SKILL.md` producido y sus 5 copias → todas iguales (§2.3).
- Búsqueda de `write`/`edit` sobre `*visual-explore-options*SKILL.md` en **todas** las sesiones con `sqlite3` en modo
  `file:...?mode=ro` (sólo lectura: la base no se modificó) → **1** operación (§3.1).
- `git status --short` **después** de escribir este archivo:

```
?? docs/skills-mcp/evidencias/skill-creator-pruebas.md
?? docs/skills-mcp/evidencias/skill-creator-uso.md
```

Los dos archivos nuevos quedan sin trackear, como el resto de los cambios pendientes. **No se hizo commit.**
