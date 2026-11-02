/**
 * Cliente HTTP base del frontend.
 *
 * Traduce el sobre de error del backend `{code, message, action?}` (R9 /
 * RN-GL-01) a un error tipado, para que cada pantalla pueda mostrar el
 * mensaje en español-AR y la acción sugerible sin reinterpretar el contrato.
 */

export interface ApiErrorAction {
  type: string;
  hint: string;
}

export interface ApiErrorBody {
  code: string;
  message: string;
  action?: ApiErrorAction;
}

/** Código genérico: el mismo que usa el backend cuando no hay regla aplicable. */
export const GENERIC_ERROR_CODE = "RN-GL-00";

export const GENERIC_ERROR_MESSAGE = "Ocurrió un error inesperado. Probá de nuevo.";

export class ApiError extends Error {
  readonly code: string;
  readonly action: ApiErrorAction | undefined;
  readonly status: number;

  constructor(body: ApiErrorBody, status: number) {
    super(body.message);
    this.name = "ApiError";
    this.code = body.code;
    this.action = body.action;
    this.status = status;
  }
}

export function isApiErrorBody(value: unknown): value is ApiErrorBody {
  if (typeof value !== "object" || value === null) return false;
  const candidato = value as Record<string, unknown>;
  return typeof candidato["code"] === "string" && typeof candidato["message"] === "string";
}

export function toApiError(payload: unknown, status: number): ApiError {
  if (isApiErrorBody(payload)) return new ApiError(payload, status);
  return new ApiError({ code: GENERIC_ERROR_CODE, message: GENERIC_ERROR_MESSAGE }, status);
}

export interface ApiClientOptions {
  baseUrl?: string;
  fetchImpl?: typeof fetch;
  timeoutMs?: number;
}

const DEFAULT_TIMEOUT_MS = 15000;

export class ApiClient {
  private readonly baseUrl: string;
  private readonly fetchImpl: typeof fetch;
  private readonly timeoutMs: number;

  constructor(options: ApiClientOptions = {}) {
    const base = options.baseUrl ?? import.meta.env.VITE_API_BASE_URL ?? "";
    this.baseUrl = base.replace(/\/+$/, "");
    this.fetchImpl = options.fetchImpl ?? globalThis.fetch.bind(globalThis);
    this.timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  }

  url(path: string): string {
    const sufijo = path.startsWith("/") ? path : `/${path}`;
    return `${this.baseUrl}${sufijo}`;
  }

  async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const controlador = new AbortController();
    const temporizador = setTimeout(() => controlador.abort(), this.timeoutMs);
    try {
      const headers = new Headers(init.headers);
      if (!headers.has("Accept")) headers.set("Accept", "application/json");
      const respuesta = await this.fetchImpl(this.url(path), {
        method: "GET",
        ...init,
        credentials: init.credentials ?? "include",
        signal: init.signal ?? controlador.signal,
        headers,
      });
      const cuerpo = await this.leerCuerpo(respuesta);
      if (!respuesta.ok) {
        throw toApiError(cuerpo, respuesta.status);
      }
      return cuerpo as T;
    } finally {
      clearTimeout(temporizador);
    }
  }

  private async leerCuerpo(respuesta: Response): Promise<unknown> {
    if (respuesta.status === 204) return null;
    const texto = await respuesta.text();
    if (texto === "") return null;
    try {
      return JSON.parse(texto) as unknown;
    } catch {
      return null;
    }
  }
}

/** Cliente por defecto: usa la URL base de la configuración del frontend. */
export const apiClient = new ApiClient();
