import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { LoginPage } from "./features/auth/LoginPage";
import { ResetPasswordPage } from "./features/auth/ResetPasswordPage";
import { RequireAuth, RequirePermission } from "./features/auth/guards";
import { AuthProvider } from "./features/auth/auth";
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
      <Route path="/login" element={<LoginPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route element={<RequireAuth />}>
        <Route path="/" element={<Navigate to="/agenda" replace />} />
        <Route element={<RequirePermission permiso="agenda" />}>
          <Route path="/agenda" element={<AgendaPage />} />
        </Route>
        <Route element={<RequirePermission permiso="pacientes" />}>
          <Route path="/pacientes" element={<PacientesPage />} />
        </Route>
        <Route element={<RequirePermission permiso="cobros" />}>
          <Route path="/caja" element={<CajaPage />} />
        </Route>
        <Route element={<RequirePermission permiso="configuracion" />}>
          <Route path="/config" element={<ConfigPage />} />
        </Route>
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}

export function App(): JSX.Element {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppShell>
          <AppRutas />
        </AppShell>
      </BrowserRouter>
    </AuthProvider>
  );
}
