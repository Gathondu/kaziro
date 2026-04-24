/** Must match ``backend.services.schedule_presets`` cron literals. */

export const FETCH_CRON_DAILY = '0 6 * * *' as const;
export const FETCH_CRON_WEEKLY = '0 6 * * 1' as const;

export const FETCH_SCHEDULE_CRONS = [FETCH_CRON_DAILY, FETCH_CRON_WEEKLY] as const;

export type FetchScheduleCron = (typeof FETCH_SCHEDULE_CRONS)[number];
