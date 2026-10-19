import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";

/** Enlaces del shell. Las rutas definitivas las define C-03 (auth + permisos). */
export const ENLACES: ReadonlyArray<{ to: string; label: string }> = [
  { to: "/agenda", label: "Agenda" },
  { to: "/pacientes", label: "Pacientes" },
  { to: "/caja", label: "Caja" },
  { to: "/config", label: "Configuración" },
];

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps): JSX.Element {
  return (
    <div className="app-shell">
      <header>
        <h1>Consultorio Odontológico</h1>
        <nav aria-label="Principal">
          <ul>
            {ENLACES.map((enlace) => (
              <li key={enlace.to}>
                <NavLink to={enlace.to}>{enlace.label}</NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </header>
      <main>{children}</main>
    </div>
  );
}

interface PaginaPlaceholderProps {
  titulo: string;
  descripcion: string;
}

/** Página placeholder: C-04/C-07/C-11 reemplazan el contenido. */
export function PaginaPlaceholder({ titulo, descripcion }: PaginaPlaceholderProps): JSX.Element {
  return (
    <section>
      <h2>{titulo}</h2>
      <p>{descripcion}</p>
    </section>
  );
}
