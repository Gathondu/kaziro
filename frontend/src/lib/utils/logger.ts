const dev = import.meta.env.DEV;

function emit(level: string, msg: string, meta?: Record<string, unknown>): void {
	const line = `[kaziro] ${level} ${msg}`;
	if (level === 'debug' || level === 'info') {
		if (meta && Object.keys(meta).length) {
			console.log(line, meta);
		} else {
			console.log(line);
		}
		return;
	}
	if (level === 'warn') {
		if (meta && Object.keys(meta).length) {
			console.warn(line, meta);
		} else {
			console.warn(line);
		}
		return;
	}
	if (meta && Object.keys(meta).length) {
		console.error(line, meta);
	} else {
		console.error(line);
	}
}

export const logger = {
	debug: (msg: string, meta?: Record<string, unknown>) => {
		if (dev) emit('debug', msg, meta);
	},
	info: (msg: string, meta?: Record<string, unknown>) => {
		if (dev) emit('info', msg, meta);
	},
	warn: (msg: string, meta?: Record<string, unknown>) => {
		if (dev) emit('warn', msg, meta);
	},
	error: (msg: string, err?: unknown) => {
		if (dev) emit('error', msg, err ? { err } : undefined);
	}
};
