import { ApiError, type ApiEnvelope } from "@/lib/api/types";

const apiOrigin = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: FormData | unknown;
  token?: string;
};

export async function apiRequest<TData>(
  path: string,
  options: RequestOptions = {},
): Promise<TData> {
  const { body, headers, token, ...init } = options;
  const hasFormData = body instanceof FormData;
  const hasJsonBody = body !== undefined && !hasFormData;
  const response = await fetch(`${apiOrigin}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(hasJsonBody ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    body: hasFormData ? body : hasJsonBody ? JSON.stringify(body) : undefined,
  });

  const envelope = (await response.json().catch(() => ({
    data: null,
    meta: null,
    error: { code: "invalid_response", message: "API returned invalid JSON." },
  }))) as ApiEnvelope<TData>;

  if (!response.ok || envelope.error) {
    throw new ApiError(
      response.status,
      envelope.error?.code ?? "request_failed",
      envelope.error?.message ?? "Request failed.",
    );
  }

  if (envelope.data === null) {
    throw new ApiError(
      response.status,
      "empty_response",
      "API returned no data.",
    );
  }

  return envelope.data;
}

export const apiClient = {
  get: <TData>(path: string, token?: string) =>
    apiRequest<TData>(path, { token }),
  post: <TData>(path: string, body: unknown, token?: string) =>
    apiRequest<TData>(path, { method: "POST", body, token }),
  postForm: <TData>(path: string, body: FormData, token?: string) =>
    apiRequest<TData>(path, { method: "POST", body, token }),
  put: <TData>(path: string, body: unknown, token?: string) =>
    apiRequest<TData>(path, { method: "PUT", body, token }),
  delete: <TData>(path: string, token?: string) =>
    apiRequest<TData>(path, { method: "DELETE", token }),
};
