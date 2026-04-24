import { FETCH_SCHEDULE_CRONS } from '$lib/constants/fetchSchedule';
import { z } from 'zod';

export const jobConfigFormSchema = z
	.object({
		name: z.string().max(255).optional().or(z.literal('')),
		keywordsText: z.string().min(1, 'Add at least one keyword'),
		location: z.string().max(255).optional().or(z.literal('')),
		remote_only: z.boolean(),
		salary_min: z.coerce.number().min(0).optional().nullable(),
		salary_max: z.coerce.number().min(0).optional().nullable(),
		fetch_schedule_cron: z.enum(FETCH_SCHEDULE_CRONS, {
			message: 'Choose a fetch schedule'
		})
	})
	.refine(
		(d) =>
			d.salary_min == null ||
			d.salary_max == null ||
			(d.salary_min <= d.salary_max && d.salary_max >= d.salary_min),
		{ message: 'Min salary cannot exceed max', path: ['salary_max'] }
	);

export type JobConfigFormInput = z.infer<typeof jobConfigFormSchema>;
