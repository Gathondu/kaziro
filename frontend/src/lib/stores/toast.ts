export type ToastLevel = 'success' | 'warning' | 'error' | 'info';

export interface ToastItem {
	id: string;
	level: ToastLevel;
	message: string;
}

const listeners = new Set<() => void>();
let items: ToastItem[] = [];

function emit(): void {
	for (const l of listeners) l();
}

export function getToasts(): ToastItem[] {
	return items;
}

export function subscribeToasts(cb: () => void): () => void {
	listeners.add(cb);
	cb();
	return () => listeners.delete(cb);
}

function push(level: ToastLevel, message: string): void {
	const id = crypto.randomUUID();
	items = [...items, { id, level, message }];
	emit();
	setTimeout(() => dismiss(id), 7000);
}

export function dismiss(id: string): void {
	items = items.filter((t) => t.id !== id);
	emit();
}

export const toast = {
	success: (m: string) => push('success', m),
	warning: (m: string) => push('warning', m),
	error: (m: string) => push('error', m),
	info: (m: string) => push('info', m)
};
