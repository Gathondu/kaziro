import { ApiError, type ApiEnvelope } from "@/lib/api/types";
import {
  fetchEventSource,
  type EventSourceMessage,
} from "@microsoft/fetch-event-source";

export const apiOrigin =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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

async function apiEmptyRequest(
  path: string,
  method: "DELETE" | "POST",
  token?: string,
): Promise<void> {
  const response = await fetch(`${apiOrigin}${path}`, {
    method,
    headers: {
      Accept: "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (!response.ok) {
    throw new ApiError(response.status, "request_failed", "Request failed.");
  }
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
  patch: <TData>(path: string, body: unknown, token?: string) =>
    apiRequest<TData>(path, { method: "PATCH", body, token }),
  delete: <TData>(path: string, token?: string) =>
    apiRequest<TData>(path, { method: "DELETE", token }),
  deleteEmpty: (path: string, token?: string) =>
    apiEmptyRequest(path, "DELETE", token),
  postEmpty: (path: string, token?: string) =>
    apiEmptyRequest(path, "POST", token),
};

export async function downloadAuthenticatedFile(
  path: string,
  token: string,
  filename: string,
): Promise<void> {
  const response = await fetch(`${apiOrigin}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    throw new ApiError(response.status, "download_failed", "Download failed.");
  }
  const objectUrl = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(objectUrl);
}

export async function getAuthenticatedBlob(
  path: string,
  token: string,
): Promise<Blob> {
  const response = await fetch(`${apiOrigin}${path}`, {
    headers: {
      Accept: "application/pdf",
      Authorization: `Bearer ${token}`,
    },
  });
  if (!response.ok) {
    const envelope = (await response
      .json()
      .catch(() => null)) as ApiEnvelope<never> | null;
    throw new ApiError(
      response.status,
      envelope?.error?.code ?? "file_request_failed",
      envelope?.error?.message ?? "Unable to load the requested file.",
    );
  }
  return await response.blob();
}

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
  let attempts = 0;
  let lastEventId = "";
  while (!signal?.aborted && attempts < 6) {
    try {
      await fetchEventSource(`${apiOrigin}${path}`, {
        method: "GET",
        headers: {
          Accept: "text/event-stream",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...(lastEventId ? { "Last-Event-ID": lastEventId } : {}),
        },
        signal,
        openWhenHidden: true,
        async onopen(response) {
          if (!response.ok) {
            const errorBody = await response.json().catch(() => null);
            throw new ApiError(
              response.status,
              errorBody?.error?.code ?? "stream_failed",
              errorBody?.error?.message ??
                `Failed to initiate stream with status ${response.status}`,
            );
          }
        },
        onmessage(event) {
          if (!event.data || event.data.trim() === "") return;
          try {
            if (event.id) lastEventId = event.id;
            attempts = 0;
            onMessage(JSON.parse(event.data) as TEventData, event);
          } catch {
            onError?.(
              new Error(`Failed to parse stream JSON payload: ${event.data}`),
            );
          }
        },
        onclose() {
          throw new Error("Notification stream closed.");
        },
        onerror(error) {
          throw error;
        },
      });
    } catch (error) {
      if (signal?.aborted) return;
      attempts += 1;
      const streamError =
        error instanceof Error
          ? error
          : new Error("Notification stream failed.");
      onError?.(streamError);
      if (attempts >= 6) break;
      await abortableDelay(
        Math.min(1000 * 2 ** (attempts - 1), 30_000),
        signal,
      );
    }
  }
  onClose?.();
}

async function abortableDelay(
  milliseconds: number,
  signal?: AbortSignal,
): Promise<void> {
  await new Promise<void>((resolve) => {
    const timer = window.setTimeout(resolve, milliseconds);
    signal?.addEventListener(
      "abort",
      () => {
        window.clearTimeout(timer);
        resolve();
      },
      { once: true },
    );
  });
}

// Exported wrapper to match your apiHorizontal object architecture
export const apiStreamClient = {
  connect: <TEventData>(path: string, options: StreamOptions<TEventData>) =>
    apiStreamRequest<TEventData>(path, options),
};
