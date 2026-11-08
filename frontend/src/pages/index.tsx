export { PacientesPage } from "../features/pacientes/PacientesPage";
export { ConfiguracionPage as ConfigPage } from "../features/agenda/ConfiguracionPage";
export { AgendaPage } from "../features/agenda/AgendaPage";
export { CajaPage } from "../features/caja/CajaPage";

import { PaginaPlaceholder } from "../shared/ui/AppShell";

export function NotFoundPage(): JSX.Element {
  return (
    <PaginaPlaceholder
      titulo="Página no encontrada"
      descripcion="La ruta solicitada no existe en la aplicación."
    />
  );
}
