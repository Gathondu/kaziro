import { ApiError, type ApiEnvelope } from "@/lib/api/types";
import {
  fetchEventSource,
  type EventSourceMessage,
} from "@microsoft/fetch-event-source";

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

type StreamOptions<TEventData> = {
  token?: string;
  signal?: AbortSignal;
  onMessage: (data: TEventData, event: EventSourceMessage) => void;
  onClose?: () => void;
  onError?: (error: Error | ApiError) => void;
};

export async function apiStreamRequest<TEventData>(
  path: string,
  options: StreamOptions<TEventData>,
): Promise<void> {
  const { token, signal, onMessage, onClose, onError } = options;

  await fetchEventSource(`${apiOrigin}${path}`, {
    method: "GET",
    headers: {
      Accept: "text/event-stream",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    signal,
    // Disables automatic infinite retries if an explicit abort occurs
    openWhenHidden: true,

    async onopen(response) {
      // Handle server-side authentication or connection errors gracefully
      if (!response.ok) {
        const errorBody = await response.json().catch(() => null);
        const error = new ApiError(
          response.status,
          errorBody?.error?.code ?? "stream_failed",
          errorBody?.error?.message ??
            `Failed to initiate stream with status ${response.status}`,
        );

        if (onError) onError(error);
        throw error;
      }
    },

    onmessage(event) {
      // 1. Skip system connection markers or heartbeat payloads
      if (
        !event.data ||
        event.data.trim() === "" ||
        event.data.startsWith(":")
      ) {
        return;
      }

      try {
        const parsedData = JSON.parse(event.data) as TEventData;
        onMessage(parsedData, event);
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      } catch (_) {
        if (onError) {
          onError(
            new Error(`Failed to parse stream JSON payload: ${event.data}`),
          );
        }
      }
    },

    onclose() {
      if (onClose) onClose();
    },

    onerror(err) {
      if (onError) onError(err);
      throw err;
    },
  });
}

// Exported wrapper to match your apiHorizontal object architecture
export const apiStreamClient = {
  connect: <TEventData>(path: string, options: StreamOptions<TEventData>) =>
    apiStreamRequest<TEventData>(path, options),
};
