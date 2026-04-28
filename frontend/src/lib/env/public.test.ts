import { describe, expect, it } from 'vitest';
import { normalizePublicApiUrl } from './public';

describe('normalizePublicApiUrl', () => {
	it('keeps a bare API origin unchanged', () => {
		expect(normalizePublicApiUrl('https://example.com')).toBe('https://example.com');
	});

	it('removes a trailing slash from a bare API origin', () => {
		expect(normalizePublicApiUrl('https://example.com/')).toBe('https://example.com');
	});

	it('removes a versioned api suffix from the configured base URL', () => {
		expect(normalizePublicApiUrl('https://example.com/api/v1')).toBe('https://example.com');
	});

	it('removes a versioned api suffix and trailing slash together', () => {
		expect(normalizePublicApiUrl('https://example.com/api/v1/')).toBe('https://example.com');
	});
});
