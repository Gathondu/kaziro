"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { LogOut } from "lucide-react";
import { NotificationBell } from "@/components/notifications/NotificationBell";
import { useAuthStore } from "@/lib/stores/auth";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const loadSession = useAuthStore((state) => state.loadSession);
  const hydrated = useAuthStore((state) => state.hydrated);
  const token = useAuthStore((state) => state.token);
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);

  useEffect(() => {
    void loadSession();
  }, [loadSession]);

  useEffect(() => {
    if (hydrated && !user) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [hydrated, pathname, router, user]);

  function signOut(): void {
    logout();
    router.replace("/");
  }

  if (!hydrated || !user || !token) {
    return (
      <main className="grid min-h-screen place-items-center bg-base-200 px-4">
        <span
          className="loading loading-spinner text-primary"
          aria-label="Loading"
        />
      </main>
    );
  }

  return (
    <div className="min-h-screen bg-base-200">
      <header className="sticky top-0 z-30 border-b border-base-300 bg-base-100/90 shadow-marketing-header backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <Link
            className="text-xl font-bold tracking-tight text-primary"
            href="/dashboard"
          >
            Kaziro
          </Link>
          <div className="flex items-center gap-2">
            <NotificationBell />
            <button
              className="btn btn-ghost btn-sm gap-2"
              onClick={signOut}
              type="button"
            >
              <LogOut className="size-4" aria-hidden="true" />
              Sign out
            </button>
          </div>
        </div>
      </header>
      {children}
    </div>
  );
}
