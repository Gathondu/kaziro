import { apiClient } from "@/lib/api/client";
import type {
  NotificationItem,
  NotificationListResponse,
} from "@/lib/api/types";

export async function listNotifications(
  token: string,
  unreadOnly = false,
): Promise<NotificationListResponse> {
  const query = unreadOnly ? "?unread_only=true" : "";
  return await apiClient.get<NotificationListResponse>(
    `/api/v1/notifications${query}`,
    token,
  );
}

export async function markNotificationRead(
  token: string,
  notificationId: string,
): Promise<NotificationItem> {
  return await apiClient.post<NotificationItem>(
    `/api/v1/notifications/${notificationId}/read`,
    {},
    token,
  );
}

export async function markAllNotificationsRead(
  token: string,
): Promise<NotificationListResponse> {
  return await apiClient.post<NotificationListResponse>(
    "/api/v1/notifications/read-all",
    {},
    token,
  );
}
