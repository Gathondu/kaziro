"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, CheckCheck } from "lucide-react";
import { useEffect, useRef } from "react";
import {
  listNotifications,
  markAllNotificationsRead,
} from "@/lib/api/notifications";
import { useAuthStore } from "@/lib/stores/auth";
import { useToastStore } from "@/lib/stores/toast";

export function NotificationBell() {
  const token = useAuthStore((state) => state.token?.access_token ?? null);
  const queryClient = useQueryClient();
  const pushToast = useToastStore((state) => state.push);
  const seenIds = useRef(new Set<string>());

  const notifications = useQuery({
    queryKey: ["notifications", "unread"],
    queryFn: () => listNotifications(token ?? "", true),
    enabled: Boolean(token),
    refetchInterval: 15_000,
  });

  const markAll = useMutation({
    mutationFn: () => markAllNotificationsRead(token ?? ""),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  useEffect(() => {
    const items = notifications.data?.items ?? [];
    for (const item of items) {
      if (seenIds.current.has(item.id)) {
        continue;
      }
      seenIds.current.add(item.id);
      pushToast("info", item.title);
    }
  }, [notifications.data?.items, pushToast]);

  const unreadCount = notifications.data?.unread_count ?? 0;

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
          <button
            className="btn btn-ghost btn-xs gap-1"
            disabled={unreadCount === 0 || markAll.isPending}
            onClick={() => markAll.mutate()}
            type="button"
          >
            <CheckCheck className="size-3.5" aria-hidden="true" />
            Read
          </button>
        </div>
        <div className="max-h-72 space-y-2 overflow-y-auto scroll-region">
          {(notifications.data?.items ?? []).length === 0 ? (
            <p className="py-6 text-center text-sm text-base-content/65">
              No unread notifications
            </p>
          ) : (
            notifications.data?.items.map((item) => (
              <article className="rounded-xl bg-base-200 p-3" key={item.id}>
                <p className="text-sm font-semibold">{item.title}</p>
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
