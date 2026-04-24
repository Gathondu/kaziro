import { z } from 'zod';

export const profileBasicsSchema = z.object({
	full_name: z.string().min(1, 'Name is required').max(255),
	professional_summary: z.string().max(4000).optional().or(z.literal('')),
	domain: z
		.string()
		.max(100, 'Domain must be at most 100 characters')
		.optional()
		.or(z.literal('')),
	experience_years: z.coerce.number().int().min(0).max(80).optional().nullable(),
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
