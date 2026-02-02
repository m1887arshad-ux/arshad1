"use client";

import { StatusBadge } from "./StatusBadge";
import { PrimaryButton } from "./PrimaryButton";
import type { AgentAction } from "@/lib/api";

interface ActionCardProps {
  action: AgentAction;
}

export function ActionCard({ action }: ActionCardProps) {
  const needsReview = action.status === "Pending";

  return (
    <tr className="border-b border-gray-200 hover:bg-gray-50/50 transition-colors">
      <td className="py-4 px-4 text-gray-900">{action.action}</td>
      <td className="py-4 px-4">
        <StatusBadge status={action.status} />
        {needsReview && (
          <span className="ml-3 inline-block">
            <PrimaryButton href={`/approve/${action.id}`} variant="warning" icon={<CheckIcon />}>
              Review
            </PrimaryButton>
          </span>
        )}
      </td>
      <td className="py-4 px-4 text-gray-600">{action.time}</td>
    </tr>
  );
}

function CheckIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  );
}
