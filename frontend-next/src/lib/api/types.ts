export type ApiErrorBody = {
  code: string;
  message: string;
};

export type ApiEnvelope<TData, TMeta = Record<string, unknown> | null> = {
  data: TData | null;
  meta: TMeta;
  error: ApiErrorBody | null;
};

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}
