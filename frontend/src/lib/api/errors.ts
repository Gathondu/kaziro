export class ApiError extends Error {
	readonly code: string;
	readonly status: number;
	readonly details: unknown;
	readonly traceId?: string;

	constructor(
		message: string,
		opts: { code: string; status: number; details?: unknown; traceId?: string }
	) {
		super(message);
		this.name = 'ApiError';
		this.code = opts.code;
		this.status = opts.status;
		this.details = opts.details;
		this.traceId = opts.traceId;
	}
}
