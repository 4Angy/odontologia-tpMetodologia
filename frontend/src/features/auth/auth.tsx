import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { ApiError, apiClient, type ApiClient } from "../../shared/api/client";

export interface AuthUser {
  sub: string;
  email: string | null;
  nombre: string | null;
  roles: string[];
  permisos: string[];
}

interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
}

interface AuthContextValue {
  accessToken: string | null;
  user: AuthUser | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  request: <T>(path: string, init?: RequestInit) => Promise<T>;
  clearError: () => void;
}

interface AuthProviderProps {
  children: ReactNode;
  client?: ApiClient;
  initialUser?: AuthUser | null;
  initialAccessToken?: string | null;
  restoreSession?: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const PERMISOS_POR_ROL: Record<string, readonly string[]> = {
  recepcion: ["agenda", "pacientes", "cobros", "deudas", "recordatorios", "exportacion"],
  odontologo: ["pacientes", "evoluciones", "presupuestos", "exportacion"],
  dueno: [
    "agenda",
    "reserva_publica",
    "pacientes",
    "evoluciones",
    "presupuestos",
    "cobros",
    "deudas",
    "recordatorios",
    "usuarios",
    "configuracion",
    "exportacion",
    "auditoria",
  ],
};

function permisosPorRoles(roles: readonly string[]): string[] {
  return [...new Set(roles.flatMap((rol) => PERMISOS_POR_ROL[rol] ?? []))].sort();
}

function mensajeDeAuth(error: unknown): string {
  if (error instanceof ApiError && error.status === 403) {
    return "Tu usuario está inactivo. Contactá al dueño del consultorio.";
  }
  if (error instanceof ApiError && error.status === 401) {
    return "Email o contraseña incorrectos.";
  }
  return "No se pudo completar la operación. Probá de nuevo.";
}

export function AuthProvider({
  children,
  client = apiClient,
  initialUser = null,
  initialAccessToken = null,
  restoreSession = true,
}: AuthProviderProps): JSX.Element {
  const [accessToken, setAccessToken] = useState<string | null>(initialAccessToken);
  const [user, setUser] = useState<AuthUser | null>(
    initialUser === null ? null : { ...initialUser, permisos: permisosPorRoles(initialUser.roles) },
  );
  const [loading, setLoading] = useState(initialUser === null);
  const [error, setError] = useState<string | null>(null);

  const loadMe = useCallback(
    async (token: string): Promise<AuthUser> => {
      const identidad = await client.request<AuthUser>("/me", {
        headers: { Authorization: `Bearer ${token}` },
      });
      return { ...identidad, permisos: permisosPorRoles(identidad.roles) };
    },
    [client],
  );

  const refresh = useCallback(async (): Promise<string> => {
    const respuesta = await client.request<TokenResponse>("/auth/refresh", { method: "POST" });
    setAccessToken(respuesta.access_token);
    const identidad = await loadMe(respuesta.access_token);
    setUser(identidad);
    return respuesta.access_token;
  }, [client, loadMe]);

  useEffect(() => {
    if (!restoreSession) {
      setLoading(false);
      return;
    }
    if (initialUser !== null) {
      setLoading(false);
      return;
    }
    let activo = true;
    void refresh()
      .catch(() => {
        if (activo) {
          setAccessToken(null);
          setUser(null);
        }
      })
      .finally(() => {
        if (activo) setLoading(false);
      });
    return () => {
      activo = false;
    };
  }, [initialUser, refresh, restoreSession]);

  const login = useCallback(
    async (email: string, password: string): Promise<void> => {
      setError(null);
      const respuesta = await client.request<TokenResponse>("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      setAccessToken(respuesta.access_token);
      setUser(await loadMe(respuesta.access_token));
    },
    [client, loadMe],
  );

  const logout = useCallback(async (): Promise<void> => {
    try {
      await client.request("/auth/logout", { method: "POST" });
    } finally {
      setAccessToken(null);
      setUser(null);
    }
  }, [client]);

  const request = useCallback(
    async <T,>(path: string, init: RequestInit = {}): Promise<T> => {
      const headers = new Headers(init.headers);
      if (accessToken !== null) headers.set("Authorization", `Bearer ${accessToken}`);
      try {
        return await client.request<T>(path, { ...init, headers });
      } catch (requestError) {
        if (
          !(requestError instanceof ApiError) ||
          ![401, 403].includes(requestError.status) ||
          accessToken === null
        ) {
          throw requestError;
        }
        try {
          const nuevoToken = await refresh();
          const retryHeaders = new Headers(init.headers);
          retryHeaders.set("Authorization", `Bearer ${nuevoToken}`);
          return await client.request<T>(path, { ...init, headers: retryHeaders });
        } catch (refreshError) {
          setAccessToken(null);
          setUser(null);
          throw refreshError;
        }
      }
    },
    [accessToken, client, refresh],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      accessToken,
      user,
      loading,
      error,
      login: async (email, password) => {
        try {
          await login(email, password);
        } catch (loginError) {
          setError(mensajeDeAuth(loginError));
          throw loginError;
        }
      },
      logout,
      request,
      clearError: () => setError(null),
    }),
    [accessToken, error, loading, login, logout, request, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === null) throw new Error("useAuth debe usarse dentro de AuthProvider");
  return context;
}

export function tienePermiso(user: AuthUser | null, permiso: string): boolean {
  return user?.permisos.includes(permiso) ?? false;
}

export { mensajeDeAuth };
