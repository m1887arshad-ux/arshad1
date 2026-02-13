"use client";

import type { ActionStatus } from "@/lib/api";

const statusClasses: Record<ActionStatus, string> = {
  Pending: "bg-pending dark:bg-orange-600 text-white dark:text-white",
  Approved: "bg-approved dark:bg-green-600 text-white dark:text-white",
  Executed: "bg-gray-600 dark:bg-gray-500 text-white dark:text-white",
};

interface StatusBadgeProps {
  status: ActionStatus;
  className?: string;
}

export function StatusBadge({ status, className = "" }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-md px-3 py-1 text-sm font-medium ${statusClasses[status]} ${className}`}
    >
      {status}
    </span>
  );
}
