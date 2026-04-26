import type { ApplicationStatus } from '$lib/types/enums';

const ALLOWED: Record<ApplicationStatus, ReadonlySet<ApplicationStatus>> = {
	DRAFT: new Set(['SENT']),
	SENT: new Set(['INTERVIEWING', 'REJECTED']),
	INTERVIEWING: new Set(['OFFERED', 'REJECTED']),
	OFFERED: new Set(),
	REJECTED: new Set(),
	WITHDRAWN: new Set()
};

export function canTransition(current: ApplicationStatus, target: ApplicationStatus): boolean {
	if (current === target) return true;
	return ALLOWED[current]?.has(target) ?? false;
}
