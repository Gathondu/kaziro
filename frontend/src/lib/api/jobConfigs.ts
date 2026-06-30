import { apiClient } from "@/lib/api/client";
import type {
  JobConfigPayload,
  JobConfigResponse,
  RunConfigResponse,
  SchedulePreset,
} from "@/lib/api/types";

export async function listJobConfigs(
  token: string,
): Promise<JobConfigResponse[]> {
  return await apiClient.get<JobConfigResponse[]>("/api/v1/job-configs", token);
}

export async function listSchedulePresets(
  token: string,
): Promise<SchedulePreset[]> {
  return await apiClient.get<SchedulePreset[]>(
    "/api/v1/job-configs/schedule-presets",
    token,
  );
}

export async function createJobConfig(
  token: string,
  payload: JobConfigPayload,
): Promise<JobConfigResponse> {
  return await apiClient.post<JobConfigResponse>(
    "/api/v1/job-configs",
    payload,
    token,
  );
}

export async function runJobConfig(
  token: string,
  configId: string,
): Promise<RunConfigResponse> {
  return await apiClient.post<RunConfigResponse>(
    `/api/v1/job-configs/${configId}/run`,
    {},
    token,
  );
}
