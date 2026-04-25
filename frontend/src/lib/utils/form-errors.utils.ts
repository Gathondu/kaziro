/** Copy of `errors` with the listed keys removed (no mutation of `errors`). */
export function omitFieldErrors(
	errors: Record<string, string>,
	...keys: string[]
): Record<string, string> {
	const next = { ...errors };
	for (const k of keys) {
		delete next[k];
	}
	return next;
}
