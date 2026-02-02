"use client";

import { useEffect, useState } from "react";
import { OwnerShell } from "@/components/OwnerShell";
import { ActionCard } from "@/components/ActionCard";
import { getCurrentOwner, getRecentActions, type AgentAction } from "@/lib/api";

export default function DashboardPage() {
  const [ownerName, setOwnerName] = useState("Owner");
  const [actions, setActions] = useState<AgentAction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const [owner, list] = await Promise.all([getCurrentOwner(), getRecentActions()]);
        setOwnerName(owner.name);
        setActions(list);
      } catch (err) {
        const msg = err instanceof Error ? err.message : "";
        if (msg.includes("not set up") || msg.includes("404")) {
          window.location.href = "/setup";
          return;
        }
        setError(msg || "Failed to load data");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const pendingCount = actions.filter((a) => a.status === "Pending").length;

  return (
    <OwnerShell title="Home" ownerName={ownerName}>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900">Activity Overview</h2>
          {pendingCount > 0 && (
            <span className="bg-pending text-white px-3 py-1 rounded-full text-sm font-medium">
              {pendingCount} action{pendingCount > 1 ? "s" : ""} pending approval
            </span>
          )}
        </div>
        
        {/* Trust message */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-sm text-blue-800">
            <strong>Human Approval Required:</strong> All agent actions require your explicit approval before execution. Nothing happens without your consent.
          </p>
        </div>

        <p className="text-sm font-semibold text-gray-700">Recent Agent Actions</p>

        {loading ? (
          <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
            <div className="animate-pulse flex flex-col items-center gap-2">
              <div className="w-8 h-8 bg-gray-200 rounded-full"></div>
              <p className="text-gray-500">Loading actions…</p>
            </div>
          </div>
        ) : error ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
            <p className="text-red-600">{error}</p>
          </div>
        ) : actions.length === 0 ? (
          <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
            <p className="text-gray-500">No agent actions yet.</p>
            <p className="text-sm text-gray-400 mt-1">Actions from Telegram will appear here for your approval.</p>
          </div>
        ) : (
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">
                    Action
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Time</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {actions.map((action) => (
                  <ActionCard key={action.id} action={action} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </OwnerShell>
  );
}
