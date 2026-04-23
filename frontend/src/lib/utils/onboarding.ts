const KEY = 'kaziro.onboarding.v1';

export type OnboardingDraft = {
	step: 1 | 2 | 3;
	profile?: Record<string, unknown>;
	lastConfigId?: string;
};

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
}
