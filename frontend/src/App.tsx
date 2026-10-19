import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./shared/ui/AppShell";
import {
  AgendaPage,
  CajaPage,
  ConfigPage,
  NotFoundPage,
  PacientesPage,
} from "./pages";

/** Rutas de la aplicación. Los permisos por rol llegan con C-03. */
export function AppRutas(): JSX.Element {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/agenda" replace />} />
      <Route path="/agenda" element={<AgendaPage />} />
      <Route path="/pacientes" element={<PacientesPage />} />
      <Route path="/caja" element={<CajaPage />} />
      <Route path="/config" element={<ConfigPage />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}

export function App(): JSX.Element {
  return (
    <BrowserRouter>
      <AppShell>
        <AppRutas />
      </AppShell>
    </BrowserRouter>
  );
}
