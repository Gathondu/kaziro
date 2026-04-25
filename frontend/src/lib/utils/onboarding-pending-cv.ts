/**
 * Holds the selected CV file between onboarding steps until Finish setup
 * (sessionStorage is not suitable for PDFs). Cleared after successful upload
 * or with the onboarding draft.
 */
let pendingCvFile: File | null = null;

export function setOnboardingPendingCv(file: File | null): void {
	pendingCvFile = file;
}

export function getOnboardingPendingCv(): File | null {
	return pendingCvFile;
}

export function clearOnboardingPendingCv(): void {
	pendingCvFile = null;
}
