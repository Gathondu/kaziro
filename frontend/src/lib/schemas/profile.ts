import { z } from 'zod';

export const profileBasicsSchema = z.object({
	full_name: z.string().min(1, 'Name is required').max(255),
	professional_summary: z.string().max(4000).optional().or(z.literal('')),
	domain: z
		.string()
		.max(100, 'Domain must be at most 100 characters')
		.optional()
		.or(z.literal('')),
	experience_years: z.coerce.number().int().min(0).max(60).optional().nullable(),
	skills: z.string().optional()
});

/** Onboarding step: name only */
export const onboardingNameSchema = z.object({
	full_name: z.string().min(1, 'Name is required').max(255)
});

/** Onboarding step: optional professional summary */
export const onboardingProfessionalSummarySchema = z.object({
	professional_summary: z.string().max(4000).optional().or(z.literal(''))
});

/** Onboarding step: optional domain (max 100 chars) */
export const onboardingDomainSchema = z.object({
	domain: z
		.string()
		.max(100, 'Domain must be at most 100 characters')
		.optional()
		.or(z.literal(''))
});

/** Onboarding step: optional years of experience */
export const onboardingExperienceSchema = z.object({
	experience_years: z.coerce.number().int().min(0).max(60).optional().nullable()
});

/** Onboarding step: optional comma-separated skills */
export const onboardingSkillsSchema = z.object({
	skills: z.string().optional()
});

export type ProfileBasicsInput = z.infer<typeof profileBasicsSchema>;

export const profileSettingsSchema = z.object({
	full_name: z.string().min(1).max(255),
	professional_summary: z.string().max(4000).optional().or(z.literal('')),
	skillsText: z.string().optional(),
	domain: z
		.string()
		.max(100, 'Domain must be at most 100 characters')
		.optional()
		.or(z.literal('')),
	values_statement: z.string().max(2000).optional().or(z.literal('')),
	linkedin_url: z
		.string()
		.optional()
		.or(z.literal(''))
		.refine((v) => v === '' || v === undefined || /^https?:\/\/.+/i.test(v), 'Enter a valid URL')
});

export type ProfileSettingsInput = z.infer<typeof profileSettingsSchema>;
