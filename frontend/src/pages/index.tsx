import { PaginaPlaceholder } from "../shared/ui/AppShell";

export function AgendaPage(): JSX.Element {
  return (
    <PaginaPlaceholder
      titulo="Agenda"
      descripcion="La agenda diaria y semanal llega con C-07 (turnos, bloqueos y anti-solape)."
    />
  );
}

export function PacientesPage(): JSX.Element {
  return (
    <PaginaPlaceholder
      titulo="Pacientes"
      descripcion="La ficha de pacientes, los opt-ins y la importación CSV llegan con C-04."
    />
  );
}

export function CajaPage(): JSX.Element {
  return (
    <PaginaPlaceholder
      titulo="Caja"
      descripcion="Cobros, saldos, deudas y cierre del día llegan con C-11."
    />
  );
}

export function ConfigPage(): JSX.Element {
  return (
    <PaginaPlaceholder
      titulo="Configuración"
      descripcion="La configuración del consultorio (antelación, seña, plantillas) llega con C-06."
    />
  );
}

export function NotFoundPage(): JSX.Element {
  return (
    <PaginaPlaceholder
      titulo="Página no encontrada"
      descripcion="La ruta solicitada no existe en la aplicación."
    />
  );
}
