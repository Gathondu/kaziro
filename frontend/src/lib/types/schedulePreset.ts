import type { FetchScheduleCron } from '$lib/constants/fetchSchedule';

export type SchedulePresetId = 'daily' | 'weekly';

export interface SchedulePreset {
	id: SchedulePresetId;
	label: string;
	fetch_schedule_cron: FetchScheduleCron;
}
