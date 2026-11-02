import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth, tienePermiso } from "./auth";

export function RequireAuth(): JSX.Element {
  const { loading, user } = useAuth();
  const location = useLocation();
  if (loading) return <p role="status">Cargando sesión…</p>;
  if (user === null) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return <Outlet />;
}

interface RequirePermissionProps {
  permiso: string;
}

export function RequirePermission({ permiso }: RequirePermissionProps): JSX.Element {
  const { user } = useAuth();
  if (!tienePermiso(user, permiso)) {
    return (
      <section>
        <h2>Sin permiso</h2>
        <p>Tu rol no permite acceder a esta sección.</p>
      </section>
    );
  }
  return <Outlet />;
}
