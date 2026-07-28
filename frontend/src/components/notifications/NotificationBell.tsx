"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Bell, Check, CheckCheck } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  markNotificationRead,
  markAllNotificationsRead,
  subscribe,
} from "@/lib/api/notifications";
import type {
  NotificationItem,
  NotificationListResponse,
  NotificationStreamPayload,
} from "@/lib/api/types";
import { useAuthStore } from "@/lib/stores/auth";
import { useToastStore } from "@/lib/stores/toast";

export function NotificationBell() {
  const token = useAuthStore((state) => state.token?.access_token ?? null);
  const queryClient = useQueryClient();
  const pushToast = useToastStore((state) => state.push);
  const initialNotifications =
    queryClient.getQueryData<NotificationListResponse>(["notifications", "all"])
      ?.items ?? [];
  const seenIds = useRef(new Set(initialNotifications.map((item) => item.id)));
  const [notifications, setNotifications] =
    useState<NotificationItem[]>(initialNotifications);
  const [viewAll, setViewAll] = useState<boolean>(false);

  const unreadCount = notifications.filter(
    (notification) => !notification.read_at,
  ).length;

  const markAll = useMutation({
    mutationFn: async () => await markAllNotificationsRead(token ?? ""),
  });

  const markRead = useMutation({
    mutationFn: async (id: string) =>
      await markNotificationRead(token ?? "", id),
  });

  const updateNotificationCache = useCallback(
    (updater: (current: NotificationItem[]) => NotificationItem[]) => {
      setNotifications((current) => {
        const next = updater(current);
        const unread_count = next.filter(
          (notification) => !notification.read_at,
        ).length;

        queryClient.setQueryData<NotificationListResponse>(
          ["notifications", "all"],
          {
            items: next,
            unread_count,
          },
        );

        return next;
      });
    },
    [queryClient],
  );

  useEffect(() => {
    if (!token) {
      return;
    }

    const controller = new AbortController();

    void subscribe(
      token,
      controller.signal,
      (payload: NotificationStreamPayload) => {
        switch (payload.action) {
          case "SYNC":
            setNotifications(payload.items);
            seenIds.current = new Set(payload.items.map((item) => item.id));
            queryClient.setQueryData<NotificationListResponse>(
              ["notifications", "all"],
              {
                items: payload.items,
                unread_count: payload.unread_count,
              },
            );
            break;
          case "NEW_ALERT":
            const nextNotification = payload.notification;

            updateNotificationCache((current) => {
              const filtered = current.filter(
                (item) => item.id !== nextNotification.id,
              );
              return [nextNotification, ...filtered];
            });

            if (!seenIds.current.has(nextNotification.id)) {
              seenIds.current.add(nextNotification.id);
              pushToast("info", payload.message ?? nextNotification.title);
            }
            void queryClient.invalidateQueries({ queryKey: ["jobs"] });
            void queryClient.invalidateQueries({
              queryKey: ["applications"],
            });
            void queryClient.invalidateQueries({
              queryKey: ["job-configs"],
            });
            break;
          case "MARK_SINGLE_READ":
            updateNotificationCache((current) =>
              current.map((notification) =>
                notification.id === payload.notification_id
                  ? {
                      ...notification,
                      read_at: notification.read_at ?? new Date().toISOString(),
                    }
                  : notification,
              ),
            );
            break;
          case "MARK_ALL_READ":
            const readAt = new Date().toISOString();
            updateNotificationCache((current) =>
              current.map((notification) =>
                notification.read_at
                  ? notification
                  : { ...notification, read_at: readAt },
              ),
            );
            break;
        }
      },
      (error) => {
        pushToast("error", error.message);
      },
    ).catch(() => undefined);

    return () => {
      controller.abort();
    };
  }, [pushToast, queryClient, token, updateNotificationCache]);

  const handleViewAll = () => {
    setViewAll((prev) => !prev);
  };

  const allNotifications = notifications;
  const notificationsToView = viewAll
    ? allNotifications
    : allNotifications.filter((notification) => !notification.read_at);

  return (
    <div className="dropdown dropdown-end">
      <button
        className="btn btn-ghost btn-circle relative"
        type="button"
        tabIndex={0}
      >
        <Bell className="size-5" aria-hidden="true" />
        {unreadCount > 0 ? (
          <span className="badge badge-primary badge-sm absolute -right-1 -top-1">
            {`${Math.min(unreadCount, 9)}` + (unreadCount > 9 ? "+" : "")}
          </span>
        ) : null}
        <span className="sr-only">Notifications</span>
      </button>
      <div
        className="dropdown-content z-20 mt-3 w-80 rounded-box border border-base-300 bg-base-100 p-3 shadow-marketing-card"
        tabIndex={0}
      >
        <div className="mb-3 flex items-center justify-between gap-3">
          <p className="font-semibold">Notifications</p>
          <div>
            <button
              className="btn btn-ghost btn-xs gap-1"
              disabled={unreadCount === 0 || markAll.isPending}
              onClick={() => markAll.mutate()}
              type="button"
            >
              <CheckCheck className="size-3.5" aria-hidden="true" />
              Mark all as read
            </button>
            <button className="btn btn-ghost btn-xs" onClick={handleViewAll}>
              {viewAll ? "Unread" : "All"}
            </button>
          </div>
        </div>
        <div className="max-h-72 space-y-2 overflow-y-auto scroll-region">
          {notificationsToView.length === 0 ? (
            <p className="py-6 text-center text-sm text-base-content/65">
              {allNotifications.length === 0
                ? "No notifications yet"
                : "No unread notifications"}
            </p>
          ) : (
            notificationsToView.map((item) => (
              <article className="rounded-xl bg-base-200 p-3" key={item.id}>
                <div className="flex justify-between">
                  <p className="text-sm font-semibold">{item.title}</p>

                  <button
                    className="btn btn-ghost btn-xs gap-1"
                    disabled={unreadCount === 0 || markAll.isPending}
                    onClick={() => markRead.mutate(item.id)}
                    type="button"
                  >
                    <Check className="size-3.5" aria-hidden="true" />
                    Mark as Read
                  </button>
                </div>
                <p className="mt-1 text-xs leading-relaxed text-base-content/70">
                  {item.body}
                </p>
              </article>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
