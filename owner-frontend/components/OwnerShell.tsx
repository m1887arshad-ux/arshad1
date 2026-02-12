"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { logout } from "@/lib/api";

const nav = [
  { href: "/dashboard", label: "Home", icon: HomeIcon },
  { href: "/analytics", label: "Analytics", icon: ChartIcon },
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
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // Detect mobile viewport
  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  // Close sidebar on route change (mobile)
  useEffect(() => {
    setSidebarOpen(false);
  }, [pathname]);

  function handleLogout() {
    if (confirm("Are you sure you want to logout?")) {
      logout();
      router.replace("/login");
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Mobile overlay */}
      {sidebarOpen && isMobile && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          ${isMobile ? "fixed inset-y-0 left-0 z-50" : "relative"}
          ${isMobile && !sidebarOpen ? "-translate-x-full" : "translate-x-0"}
          w-56 bg-sidebar dark:bg-sidebar-dark text-white flex flex-col shrink-0 transition-transform duration-200 ease-in-out
        `}
      >
        <div className="p-4 flex items-center justify-between border-b border-white/10 dark:border-gray-700">
          <div className="flex items-center gap-2">
            <LogoIcon />
            <span className="font-semibold text-white dark:text-gray-100">Bharat Biz-Agent</span>
          </div>
          {isMobile && (
            <button
              onClick={() => setSidebarOpen(false)}
              className="text-white/80 dark:text-gray-400 hover:text-white dark:hover:text-gray-200 p-1"
            >
              <CloseIcon />
            </button>
          )}
        </div>
        <nav className="p-3 flex flex-col gap-1 flex-1">
          {nav.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(href));
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  active ? "bg-sidebar-active dark:bg-sidebar-active-dark text-white dark:text-gray-100" : "text-white/90 dark:text-gray-300 hover:bg-white/10 dark:hover:bg-gray-700"
                }`}
              >
                <Icon />
                {label}
              </Link>
            );
          })}
        </nav>
        {/* Mobile logout at bottom of sidebar */}
        {isMobile && (
          <div className="p-3 border-t border-white/10 dark:border-gray-700">
            <button
              onClick={handleLogout}
              className="w-full text-left px-3 py-2.5 text-sm text-white/80 dark:text-gray-400 hover:text-white dark:hover:text-gray-200 hover:bg-white/10 dark:hover:bg-gray-700 rounded-lg"
            >
              Logout
            </button>
          </div>
        )}
      </aside>

      {/* Main content */}
      <main className="flex-1 bg-gray-50 dark:bg-gray-900 flex flex-col min-w-0 transition-colors duration-200">
        <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 md:px-6 py-4 flex items-center justify-between transition-colors duration-200">
          <div className="flex items-center gap-3">
            {/* Mobile hamburger */}
            {isMobile && (
              <button
                onClick={() => setSidebarOpen(true)}
                className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 p-1 -ml-1"
              >
                <HamburgerIcon />
              </button>
            )}
            <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100 truncate">{title}</h1>
          </div>
          <div className="flex items-center gap-2 md:gap-4">
            <div className="hidden sm:flex items-center gap-2 text-gray-600 dark:text-gray-400">
              <UserIcon />
              <span className="text-sm font-medium">Owner: {ownerName}</span>
            </div>
            {!isMobile && (
              <button
                type="button"
                onClick={handleLogout}
                className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
              >
                Logout
              </button>
            )}
          </div>
        </header>
        <div className="flex-1 p-4 md:p-6 overflow-auto dark:bg-gray-900">{children}</div>
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

function ChartIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
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

function HamburgerIcon() {
  return (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  );
}
