---
version: 1
slug: "frontend-src-features-agenda-agendapage-tsx"
primary_target: "frontend/src/features/agenda/AgendaPage.tsx"
related_targets: []
---

Scope: agenda interna web de C-07. Mode: Operate.
Audience: recepción y dueño organizan los turnos del consultorio; odontología consulta los propios.
Task: revisar el día o la semana, filtrar por profesional, crear y resolver turnos.
Constraints: mantener acciones claras, mensajes español-AR, evitar exposición de datos ajenos y no mostrar éxito antes de confirmar el servidor.
Direction: lista cronológica de operación, elegida por el usuario (opción B). La agenda se lee como un registro de trabajo del día, no como una miniatura de calendario.
Unresolved: la disponibilidad visible entre profesionales requiere una consulta futura dedicada; en esta entrega se muestran turnos existentes y alternativas devueltas por conflicto.

## Direction contract

THESIS: La pantalla es el registro operativo del consultorio: primero responde qué turno sigue y qué requiere atención. Rechaza una cuadrícula comprimida como representación única, especialmente en móvil.

OWN-WORLD: Una hoja de operación de alto contraste para una recepción iluminada: superficie clara neutra, tinta azul profunda, separadores finos y acento azul reservado a la acción principal y selección. Estados clínico-operativos usan nombres y color semántico; las horas usan cifras tabulares.

STORY: Quien atiende la agenda elige período y profesional, localiza un turno en orden temporal y ejecuta la siguiente acción disponible. Errores de conflicto conservan el formulario y permiten tomar una alternativa real.

FIRST VIEWPORT: Encabezado “Agenda”; debajo, navegación anterior/siguiente, fecha, alternancia Día/Semana, filtro de profesional y acción “Nuevo turno”. La lista cronológica ocupa el ancho disponible; hora, paciente, profesional, prestación y estado se leen sin abrir el turno. Los formularios aparecen inline al pie de la lista o en la fila elegida.

FORM: Opción B, lista operativa cronológica con panel inline para alta/reprogramación y diálogo accesible solo para confirmar cancelación. Seed key: f8ef8a04.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
