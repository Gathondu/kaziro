export interface PageMeta {
	next_cursor: string | null;
	total: number | null;
}

export interface ErrorBody {
	code: string;
	message: string;
	details?: unknown;
	trace_id?: string;
}

export interface Envelope<T> {
	data: T | null;
	meta: PageMeta | null;
	error: ErrorBody | null;
}
