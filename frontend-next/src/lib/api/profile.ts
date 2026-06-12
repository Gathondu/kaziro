import { apiClient } from "@/lib/api/client";
import type {
  CvUploadResponse,
  ProfilePayload,
  ProfileResponse,
} from "@/lib/api/types";

export async function getProfile(token: string): Promise<ProfileResponse> {
  return await apiClient.get<ProfileResponse>("/api/v1/profile", token);
}

export async function putProfile(
  token: string,
  payload: ProfilePayload,
): Promise<ProfileResponse> {
  return await apiClient.put<ProfileResponse>(
    "/api/v1/profile",
    payload,
    token,
  );
}

export async function uploadCvPdf(
  token: string,
  file: File,
): Promise<CvUploadResponse> {
  const formData = new FormData();
  formData.set("file", file);
  return await apiClient.postForm<CvUploadResponse>(
    "/api/v1/profile/cv",
    formData,
    token,
  );
}
