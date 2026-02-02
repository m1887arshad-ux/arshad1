"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { logout } from "@/lib/api";

const nav = [
  { href: "/dashboard", label: "Home", icon: HomeIcon },
  { href: "/records", label: "Records", icon: DocIcon },
  { href: "/settings", label: "Settings", icon: GearIcon },
];

export function OwnerShell({
  children,
  title,
  ownerName = "Owner",
}: {
  children: React.ReactNode;
  title: string;
  ownerName?: string;
}) {
  const pathname = usePathname();
  const router = useRouter();
  function handleLogout() {
    logout();
    router.replace("/login");
  }

  return (
    <div className="min-h-screen flex">
      <aside className="w-56 bg-sidebar text-white flex flex-col shrink-0">
        <div className="p-4 flex items-center gap-2 border-b border-white/10">
          <LogoIcon />
          <span className="font-semibold">Bharat Biz-Agent</span>
        </div>
        <nav className="p-3 flex flex-col gap-1">
          {nav.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(href));
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  active ? "bg-sidebar-active text-white" : "text-white/90 hover:bg-white/10"
                }`}
              >
                <Icon />
                {label}
              </Link>
            );
          })}
        </nav>
      </aside>
      <main className="flex-1 bg-gray-50 flex flex-col">
        <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h1 className="text-lg font-semibold text-gray-900">{title}</h1>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-gray-600">
              <UserIcon />
              <span className="text-sm font-medium">Owner: {ownerName}</span>
            </div>
            <button
              type="button"
              onClick={handleLogout}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Logout
            </button>
          </div>
        </header>
        <div className="flex-1 p-6">{children}</div>
      </main>
    </div>
  );
}

function LogoIcon() {
  return (
    <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center text-primary font-bold text-sm">
      B
    </div>
  );
}

function HomeIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
    </svg>
  );
}

function DocIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586L17 7.586V19a2 2 0 01-2 2z" />
    </svg>
  );
}

function GearIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  );
}

function UserIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
    </svg>
  );
}
