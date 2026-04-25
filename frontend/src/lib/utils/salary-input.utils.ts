/** Upper bound for salary fields (whole units, e.g. USD). */
const SALARY_INPUT_MAX = 999_999_999;
const SALARY_INPUT_MAX_DIGITS = 9;

/**
 * Strip non-digits, cap length, parse as integer, clamp to 0–SALARY_INPUT_MAX.
 * Empty string when cleared.
 */
export function sanitizeSalaryInput(raw: string): string {
	const digits = raw.replace(/\D/g, '').slice(0, SALARY_INPUT_MAX_DIGITS);
	if (digits === '') return '';
	const n = parseInt(digits, 10);
	if (Number.isNaN(n)) return '';
	return String(Math.min(SALARY_INPUT_MAX, Math.max(0, n)));
}
