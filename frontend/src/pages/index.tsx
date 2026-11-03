export { PacientesPage } from "../features/pacientes/PacientesPage";
export { ConfiguracionPage as ConfigPage } from "../features/agenda/ConfiguracionPage";
export { AgendaPage } from "../features/agenda/AgendaPage";

import { PaginaPlaceholder } from "../shared/ui/AppShell";

export function CajaPage(): JSX.Element {
  return (
    <PaginaPlaceholder
      titulo="Caja"
      descripcion="Cobros, saldos, deudas y cierre del día llegan con C-11."
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
