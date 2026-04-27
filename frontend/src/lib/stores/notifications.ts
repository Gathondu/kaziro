import { browser } from '$app/environment';
import { getPublicApiUrl, getPublicWsUrl } from '$lib/env/public';
import { getQueryClient } from '$lib/queryClientSingleton';
import type { NotificationMessage } from '$lib/types/notifications';
import { logger } from '$lib/utils/logger';
import { toast } from './toast';

type Handler = (msg: NotificationMessage) => void;

const handlers = new Set<Handler>();
const listeners = new Set<() => void>();

let socket: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let heartbeatTimer: ReturnType<typeof setInterval> | null = null;
let backoffMs = 1000;
let lastServerMessageAt = 0;
let currentToken: string | null = null;
let reconnectPending = false;

function emitConnection(): void {
	for (const l of listeners) l();
}

export type NotificationsConnectionVisualState = 'live' | 'pending' | 'offline';

export function isNotificationsConnected(): boolean {
	return socket !== null && socket.readyState === WebSocket.OPEN;
}

export function getNotificationsConnectionVisualState(): NotificationsConnectionVisualState {
	if (!browser) return 'offline';
	if (isNotificationsConnected()) return 'live';
	if (reconnectTimer !== null) return 'pending';
	if (reconnectPending) return 'pending';
	if (socket?.readyState === WebSocket.CONNECTING || socket?.readyState === WebSocket.CLOSING) {
		return 'pending';
	}
	return 'offline';
}

export function subscribeConnection(cb: () => void): () => void {
	listeners.add(cb);
	cb();
	return () => listeners.delete(cb);
}

export function subscribeNotifications(handler: Handler): () => void {
	handlers.add(handler);
	return () => handlers.delete(handler);
}

function wsUrl(token: string): string {
	const explicitWsBase = getPublicWsUrl();
	const fallbackApiBase = getPublicApiUrl();
	const base = explicitWsBase ?? (fallbackApiBase.includes('localhost') ? fallbackApiBase : undefined);
	if (!base) {
		return '';
	}
	const u = new URL(base);
	if (u.protocol === 'https:') {
		u.protocol = 'wss:';
	} else if (u.protocol === 'http:') {
		u.protocol = 'ws:';
	}
	if (!explicitWsBase) {
		u.pathname = '/api/v1/ws/notifications';
	}
	u.search = '';
	u.searchParams.set('token', token);
	return u.toString();
}

function dispatch(msg: NotificationMessage): void {
	const qc = getQueryClient();
	if (msg.type === 'evaluation_complete') {
		toast.success(
			'Evaluation finished for a job.'
		);
		qc?.invalidateQueries({ queryKey: ['jobs'] });
		qc?.invalidateQueries({ queryKey: ['job', msg.job_posting_id] });
		qc?.invalidateQueries({ queryKey: ['job', msg.job_posting_id, 'evaluation'] });
		qc?.invalidateQueries({ queryKey: ['dashboard'] });
	}
	if (msg.type === 'documents_ready') {
		toast.success('Application documents are ready.');
		qc?.invalidateQueries({ queryKey: ['applications'] });
		qc?.invalidateQueries({ queryKey: ['dashboard'] });
		if (msg.job_posting_id) {
			qc?.invalidateQueries({ queryKey: ['job', msg.job_posting_id, 'evaluation'] });
		}
	}
	if (msg.type === 'application_event') {
		qc?.invalidateQueries({ queryKey: ['application', msg.application_id] });
		qc?.invalidateQueries({ queryKey: ['applications'] });
		qc?.invalidateQueries({ queryKey: ['dashboard'] });
	}
	for (const h of handlers) {
		try {
			h(msg);
		} catch (e) {
			logger.error('notifications.handler_failed', e);
		}
	}
}

function parseMessage(raw: string): NotificationMessage | null {
	try {
		const data = JSON.parse(raw) as unknown;
		if (typeof data !== 'object' || data === null || !('type' in data)) {
			return null;
		}
		return data as NotificationMessage;
	} catch {
		return null;
	}
}

function clearTimers(): void {
	if (reconnectTimer) {
		clearTimeout(reconnectTimer);
		reconnectTimer = null;
	}
	if (heartbeatTimer) {
		clearInterval(heartbeatTimer);
		heartbeatTimer = null;
	}
}

function scheduleReconnect(): void {
	clearTimers();
	if (!browser || !currentToken) return;
	reconnectPending = true;
	emitConnection();
	reconnectTimer = setTimeout(() => {
		reconnectTimer = null;
		reconnectPending = false;
		emitConnection();
		connectNotifications(currentToken!);
	}, backoffMs);
	backoffMs = Math.min(backoffMs * 2, 30_000);
}

export function connectNotifications(token: string): void {
	if (!browser) return;
	currentToken = token;
	const explicitWsBase = getPublicWsUrl();
	const url = wsUrl(token);
	if (!url) {
		reconnectPending = false;
		emitConnection();
		return;
	}
	if (
		socket &&
		(socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)
	) {
		emitConnection();
		return;
	}
	socket?.close();
	clearTimers();
	reconnectPending = false;

	try {
		socket = new WebSocket(url);
		emitConnection();
	} catch (e) {
		logger.error('notifications.ws_construct_failed', e);
		scheduleReconnect();
		return;
	}

	socket.addEventListener('open', () => {
		backoffMs = 1000;
		reconnectPending = false;
		lastServerMessageAt = Date.now();
		emitConnection();
	});

	socket.addEventListener('message', (ev) => {
		lastServerMessageAt = Date.now();
		const raw = typeof ev.data === 'string' ? ev.data : '';
		const msg = parseMessage(raw);
		if (!msg) return;
		if (msg.type === 'ping') {
			try {
				socket?.send(JSON.stringify({ type: 'pong', ts: Date.now() }));
			} catch {
				// ignore
			}
			return;
		}
		dispatch(msg);
	});

	socket.addEventListener('close', () => {
		emitConnection();
		scheduleReconnect();
	});

	socket.addEventListener('error', () => {
		emitConnection();
		socket?.close();
	});

	heartbeatTimer = setInterval(() => {
		if (!socket || socket.readyState !== WebSocket.OPEN) return;
		if (explicitWsBase) return;
		if (Date.now() - lastServerMessageAt > 90_000) {
			logger.warn('notifications.stale_connection');
			socket.close();
		}
	}, 10_000);
}

export function disconnectNotifications(): void {
	currentToken = null;
	reconnectPending = false;
	clearTimers();
	socket?.close();
	socket = null;
	emitConnection();
}
