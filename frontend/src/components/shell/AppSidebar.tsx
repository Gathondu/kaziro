"use client";

import {
  BriefcaseBusiness,
  LayoutDashboard,
  Settings,
  Send,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/jobs", label: "Jobs", icon: BriefcaseBusiness },
  { href: "/applications", label: "Applications", icon: Send },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed inset-y-0 left-0 z-40 hidden w-52 border-r border-base-300 bg-base-100 pt-16 md:block">
      <nav
        className="flex h-full flex-col gap-1 p-3"
        aria-label="Main navigation"
      >
        {links.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              className={`btn justify-start gap-3 ${active ? "btn-primary" : "btn-ghost"}`}
              href={href}
              key={href}
            >
              <Icon className="size-4" aria-hidden="true" />
              {label}
            </Link>
          );
        })}
        <p className="mt-auto px-3 pb-3 text-xs text-base-content/50">
          Your job search workspace
        </p>
      </nav>
    </aside>
  );
}
