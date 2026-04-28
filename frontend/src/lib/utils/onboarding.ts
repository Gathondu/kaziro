import { clearOnboardingPendingCv } from '$lib/utils/onboarding-pending-cv';

const KEY = 'kaziro.onboarding.v1';

export type ProfileOnboardingSubStep = 'about' | 'summary' | 'domain' | 'experience' | 'skills';

export type OnboardingProfileDraft = {
	full_name?: string;
	professional_summary?: string;
	domain?: string;
	experience_years?: number | null;
	skillsText?: string;
};

export type OnboardingDraft = {
	step: 1 | 2 | 3;
	profileSubStep?: ProfileOnboardingSubStep;
	profile?: OnboardingProfileDraft;
	lastConfigId?: string;
};

/** Linear onboarding order for progress UI (full-screen flow). */
export const ONBOARDING_PATH_STEPS: Record<string, number> = {
	'/onboarding/about-you': 1,
	'/onboarding/summary': 2,
	'/onboarding/domain': 3,
	'/onboarding/experience': 4,
	'/onboarding/skills': 5,
	'/onboarding/cv': 6,
	'/onboarding/config': 7
};

export const ONBOARDING_STEP_TOTAL = 7;

export function onboardingStepMeta(pathname: string): { current: number; total: number } | null {
	const current = ONBOARDING_PATH_STEPS[pathname];
	if (!current) return null;
	return { current, total: ONBOARDING_STEP_TOTAL };
}

export function loadOnboardingDraft(): OnboardingDraft | null {
	if (typeof sessionStorage === 'undefined') return null;
	try {
		const raw = sessionStorage.getItem(KEY);
		if (!raw) return null;
		return JSON.parse(raw) as OnboardingDraft;
	} catch {
		return null;
	}
}

export function saveOnboardingDraft(draft: OnboardingDraft): void {
	try {
		sessionStorage.setItem(KEY, JSON.stringify(draft));
	} catch {
		// ignore
	}
}

export function clearOnboardingDraft(): void {
	try {
		sessionStorage.removeItem(KEY);
	} catch {
		// ignore
	}
	// Staged CV lives only in memory; clear with draft so abandoned flows do not leak a File.
	clearOnboardingPendingCv();
}

/** Next URL for the onboarding entry redirector and legacy `/onboarding/profile` links. */
export function resumeOnboardingPath(d: OnboardingDraft | null): string {
	if (!d) return '/onboarding/about-you';
	if (d.step === 2) return '/onboarding/cv';
	if (d.step === 3) return '/onboarding/config';
	const sub = d.profileSubStep ?? 'about';
	if (sub === 'summary') return '/onboarding/summary';
	if (sub === 'domain') return '/onboarding/domain';
	if (sub === 'experience') return '/onboarding/experience';
	if (sub === 'skills') return '/onboarding/skills';
	return '/onboarding/about-you';
}

type OnboardingBackSpec = {
	path: string;
	step: 1 | 2 | 3;
	profileSubStep?: ProfileOnboardingSubStep;
};

/** Linear back chain (step 1 = about-you has no back). */
const ONBOARDING_BACK: Record<string, OnboardingBackSpec> = {
	'/onboarding/summary': { path: '/onboarding/about-you', step: 1, profileSubStep: 'about' },
	'/onboarding/domain': { path: '/onboarding/summary', step: 1, profileSubStep: 'summary' },
	'/onboarding/experience': { path: '/onboarding/domain', step: 1, profileSubStep: 'domain' },
	'/onboarding/skills': { path: '/onboarding/experience', step: 1, profileSubStep: 'experience' },
	'/onboarding/cv': { path: '/onboarding/skills', step: 1, profileSubStep: 'skills' },
	'/onboarding/config': { path: '/onboarding/cv', step: 2 }
};

export function hasOnboardingBack(pathname: string): boolean {
	return pathname in ONBOARDING_BACK;
}

/**
 * Rewrites the session draft for the previous onboarding step and returns its path.
 * Keeps `profile` / `lastConfigId` so fields refill when the prior screen remounts.
 */
export function prepareOnboardingBack(pathname: string): string | null {
	const spec = ONBOARDING_BACK[pathname];
	if (!spec) return null;
	const d = loadOnboardingDraft();
	const next: OnboardingDraft = {
		step: spec.step,
		profile: d?.profile ?? {}
	};
	if (spec.profileSubStep !== undefined) {
		next.profileSubStep = spec.profileSubStep;
	}
	if (d?.lastConfigId !== undefined) {
		next.lastConfigId = d.lastConfigId;
	}
	saveOnboardingDraft(next);
	return spec.path;
}
