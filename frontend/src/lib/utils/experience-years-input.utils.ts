/** Upper bound for years of experience (UI + API aligned). */
export const EXPERIENCE_YEARS_MAX = 60;

/** At most two digits (0–60); avoids a third digit appending after clamp (e.g. 60 + 3 → 603). */
const DIGIT_CAP = 2;

/**
 * Strip non-digits, keep at most two digits, parse, clamp to 0–EXPERIENCE_YEARS_MAX.
 * Returns empty string when the user clears the field.
 */
export function sanitizeExperienceYearsInput(raw: string): string {
	const digits = raw.replace(/\D/g, '').slice(0, DIGIT_CAP);
	if (digits === '') return '';
	const n = parseInt(digits, 10);
	if (Number.isNaN(n)) return '';
	return String(Math.min(EXPERIENCE_YEARS_MAX, Math.max(0, n)));
}
