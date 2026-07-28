"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { LogOut, Menu } from "lucide-react";
import { NotificationBell } from "@/components/notifications/NotificationBell";
import { AppSidebar } from "@/components/shell/AppSidebar";
import { ThemeToggle } from "@/components/shell/ThemeToggle";
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
      <header className="fixed inset-x-0 top-0 z-50 h-16 border-b border-base-300 bg-base-100/90 shadow-marketing-header backdrop-blur-xl">
        <div className="flex h-full items-center justify-between gap-4 px-4">
          <Link
            className="text-xl font-bold tracking-tight text-primary"
            href="/dashboard"
          >
            Kaziro
          </Link>
          <div className="flex items-center gap-2">
            <div className="dropdown md:hidden">
              <button
                className="btn btn-ghost btn-circle btn-sm"
                tabIndex={0}
                type="button"
              >
                <Menu className="size-5" />
                <span className="sr-only">Open navigation</span>
              </button>
              <ul className="menu dropdown-content z-50 mt-3 w-52 rounded-box border border-base-300 bg-base-100 p-2 shadow">
                <li>
                  <Link href="/dashboard">Dashboard</Link>
                </li>
                <li>
                  <Link href="/jobs">Jobs</Link>
                </li>
                <li>
                  <Link href="/applications">Applications</Link>
                </li>
                <li>
                  <Link href="/settings">Settings</Link>
                </li>
              </ul>
            </div>
            <ThemeToggle />
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
      <AppSidebar />
      <div className="min-h-screen pt-16 md:pl-52">{children}</div>
    </div>
  );
}
