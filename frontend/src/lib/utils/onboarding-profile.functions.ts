import { profileBasicsSchema } from '$lib/schemas/profile';
import type { OnboardingProfileDraft } from '$lib/utils/onboarding';

/** Map draft → shape expected by `profileBasicsSchema` (skills as comma text). */
export function profileDraftToBasicsInput(d: OnboardingProfileDraft): {
	full_name: string;
	professional_summary?: string;
	domain?: string;
	experience_years?: number | null;
	skills?: string;
} {
	return {
		full_name: d.full_name ?? '',
		professional_summary: d.professional_summary,
		domain: d.domain,
		experience_years: d.experience_years ?? undefined,
		skills: d.skillsText
	};
}

/**
 * Validate accumulated onboarding profile draft and build the API body for `PUT /profile`.
 */
export function validateProfileDraftForSubmit(
	d: OnboardingProfileDraft | undefined
):
	| { ok: true; body: Record<string, unknown> }
	| { ok: false; fieldErrors: Record<string, string> } {
	if (!d?.full_name?.trim()) {
		return { ok: false, fieldErrors: { full_name: 'Name is required' } };
	}
	const parsed = profileBasicsSchema.safeParse(profileDraftToBasicsInput(d));
	if (!parsed.success) {
		const fieldErrors: Record<string, string> = {};
		for (const iss of parsed.error.issues) {
			const k = String(iss.path[0] ?? 'form');
			fieldErrors[k] = iss.message;
		}
		return { ok: false, fieldErrors };
	}
	const skillsList = parsed.data.skills
		? parsed.data.skills
				.split(',')
				.map((s) => s.trim())
				.filter(Boolean)
		: [];
	const body: Record<string, unknown> = {
		full_name: parsed.data.full_name,
		professional_summary: parsed.data.professional_summary?.trim()
			? parsed.data.professional_summary
			: undefined,
		domain: parsed.data.domain?.trim() ? parsed.data.domain : undefined,
		experience_years: parsed.data.experience_years ?? undefined,
		skills: skillsList
	};
	return { ok: true, body };
}
