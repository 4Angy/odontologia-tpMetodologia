# Design

## Context

El frontend real usa React 18 + TypeScript + Vite con CSS plano por feature (`AgendaPage.css` scoped bajo `.agenda-*`). El shell (`AppShell`) ya exponía `className="app-shell"` pero ninguna hoja de estilos lo definía, igual que `.sr-only` usado en markup. La agenda define su propia paleta (`--agenda-*`, acento `#174f91`); el resto de la app no tenía estilo alguno. Caja pedía `monto_cents` como `input[type=number]` (step=1 implícito → solo enteros) y mostraba centavos crudos. El proxy de Vite enumeraba prefijos de API a mano y se había desincronizado del backend (`/lista-espera`, `/export` faltaban → la SPA recibía 404/HTML y el cliente API mostraba el error genérico).

## Goals / Non-Goals

**Goals:**
- Una hoja global única y predecible, sin frameworks ni dependencias nuevas.
- Paleta y radios coherentes con la agenda existente.
- Mejora visible en todas las rutas (autenticadas, login, reserva pública) sin tocar comportamiento.
- Caja usable por humanos (pesos, no centavos) manteniendo `monto_cents` entero hacia la API.
- Proxy dev completo y arranque reproducible documentado.

**Non-Goals:**
- No se migran los estilos scoped de la agenda a tokens globales (riesgo de regresión visual sin beneficio; conviven: `.agenda-page` define sus propias custom properties).
- No se rediseñan layouts internos de cada feature (tablas de pacientes, formularios de config quedan con estilo base global).
- No se cambia el contrato `monto_cents` ni se agrega formateo de moneda en otros módulos.
- No se implementa un design system con componentes (sigue siendo CSS plano).

## Decisions

### D1 — CSS plano global en vez de extender `AgendaPage.css`

`AgendaPage.css` está scoped bajo `.agenda-page` y define sus propios tokens `--agenda-*`. Meter estilos globales ahí acoplaría el shell al feature agenda. Se crea `src/styles/global.css` importado desde `main.tsx`, con tokens `--ui-*` propios pero misma familia cromática (`#174f91`). Alternativa descartada: CSS-in-JS o Tailwind — el repo real nunca los adoptó y agregarlos solo para este pulido sería desproporcionado.

### D2 — `button[type="submit"]` como primario, el resto secundario

Las páginas usan `<button>` planos sin clases de variante. En vez de agregar classNames a ~20 componentes, el submit se estiliza como acción primaria por semántica HTML (`type="submit"`). Limitación conocida: un submit que no sea "la" acción principal se verá primario igual; se acepta por simplicidad.

### D3 — Input de monto en pesos con conversión a centavos

`pesosACentavos()` normaliza coma/punto, valida `> 0` y `Math.round(pesos * 100)`; el payload sigue siendo `monto_cents` entero (R5 intacto). Se usa `input[type=text][inputMode=decimal]` para aceptar `1500,50`. Mostrar centavos crudos se reemplaza por `Intl.NumberFormat("es-AR", currency ARS)`.

### D4 — Proxy por lista explícita de prefijos

Vite necesita saber qué rutas son API (el resto es SPA). Se mantiene el enfoque de lista explícita y se agregan los prefijos faltantes (`/lista-espera`, `/export`). Riesgo residual: un futuro endpoint con prefijo nuevo vuelve a romperse en dev; se mitiga con la verificación manual del checklist de lanzamiento.

### D5 — `docker-entrypoint.sh` en LF

Git en Windows checkout con CRLF; el shebang `#!/bin/sh\r` rompe el entrypoint (`exec format error`). Se normaliza el archivo a LF en el repo. Alternativa descartada: `.gitattributes` global — más invasivo para un solo archivo.

## Risks / Trade-offs

- Estilos globales de elementos (`button`, `input`, `table`) aplican también dentro de `.agenda-page`: la especificidad de clase de `AgendaPage.css` gana donde define la misma propiedad; donde no define (ej. `label`), el estilo global mejora sin romper.
- `color-mix()` en `:focus-visible` requiere navegador moderno (2023+); aceptable para el público objetivo.
