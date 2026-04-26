/** Copy plain text to the system clipboard (browser API). */

export async function copyTextToClipboard(text: string): Promise<void> {
	if (typeof navigator === 'undefined' || !navigator.clipboard?.writeText) {
		throw new Error('Clipboard is not available in this environment.');
	}
	await navigator.clipboard.writeText(text);
}
