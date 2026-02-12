"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { OwnerShell } from "@/components/OwnerShell";
import { ActionCard } from "@/components/ActionCard";
import { 
  getCurrentOwner, 
  getRecentActions, 
  getLowStockItems,
  getExpiringItems,
  type AgentAction,
  type LowStockItem,
  type ExpiringItem
} from "@/lib/api";

const POLL_INTERVAL = 10000; // 10 seconds

function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("bharat_owner_token");
}

export default function DashboardPage() {
  const router = useRouter();
  const [ownerName, setOwnerName] = useState("Owner");
  const [actions, setActions] = useState<AgentAction[]>([]);
  const [lowStockItems, setLowStockItems] = useState<LowStockItem[]>([]);
  const [expiringItems, setExpiringItems] = useState<ExpiringItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [isPolling, setIsPolling] = useState(true);

  // Check auth before rendering
  useEffect(() => {
    if (!getStoredToken()) {
      router.replace("/login");
    }
  }, [router]);

  // Fetch function for polling
  const fetchData = useCallback(async (showLoading = false) => {
    if (showLoading) setLoading(true);
    try {
      const [list, lowStock, expiring] = await Promise.all([
        getRecentActions(),
        getLowStockItems(20),
        getExpiringItems(30),
      ]);
      setActions(list);
      setLowStockItems(lowStock);
      setExpiringItems(expiring);
      setLastUpdated(new Date());
      setError("");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "";
      if (msg.includes("not set up") || msg.includes("404")) {
        window.location.href = "/setup";
        return;
      }
      // Don't show error during background polling
      if (showLoading) {
        if (msg.includes("Failed to fetch") || msg.includes("NetworkError")) {
          setError("Cannot connect to server. Please make sure the backend is running.");
        } else {
          setError(msg || "Failed to load data");
        }
      }
    } finally {
      if (showLoading) setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    async function load() {
      if (!getStoredToken()) return; // Wait for auth check
      
      try {
        const owner = await getCurrentOwner();
        setOwnerName(owner.name);
        await fetchData(true);
      } catch (err) {
        const msg = err instanceof Error ? err.message : "";
        if (msg.includes("not set up") || msg.includes("404")) {
          window.location.href = "/setup";
          return;
        }
        if (msg.includes("Failed to fetch") || msg.includes("NetworkError")) {
          setError("Cannot connect to server. Please make sure the backend is running.");
        } else {
          setError(msg || "Failed to load data");
        }
        setLoading(false);
      }
    }
    load();
  }, [fetchData]);

  // Polling effect
  useEffect(() => {
    if (!isPolling) return;

    const interval = setInterval(() => {
      fetchData(false);
    }, POLL_INTERVAL);

    return () => clearInterval(interval);
  }, [isPolling, fetchData]);

  const pendingCount = actions.filter((a) => a.status === "Pending").length;

  return (
    <OwnerShell title="Home" ownerName={ownerName}>
      <div className="space-y-6">
        {/* Header with polling status */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <h2 className="text-2xl font-bold text-gray-900">Activity Overview</h2>
          <div className="flex items-center gap-3">
            {pendingCount > 0 && (
              <span className="bg-pending text-white px-3 py-1 rounded-full text-sm font-medium">
                {pendingCount} action{pendingCount > 1 ? "s" : ""} pending
              </span>
            )}
            {/* Live indicator */}
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <span
                className={`w-2 h-2 rounded-full ${isPolling ? "bg-green-500 animate-pulse" : "bg-gray-300"}`}
              />
              <span>{isPolling ? "Live" : "Paused"}</span>
              <button
                onClick={() => setIsPolling(!isPolling)}
                className="text-primary hover:underline"
              >
                {isPolling ? "Pause" : "Resume"}
              </button>
            </div>
          </div>
        </div>

        {/* Low Stock Alert Banner */}
        {lowStockItems.length > 0 && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0">
                <AlertIcon className="w-5 h-5 text-red-500" />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-sm font-semibold text-red-800 dark:text-red-200">
                  ⚠️ {lowStockItems.length} medicine{lowStockItems.length > 1 ? "s" : ""} running low!
                </h3>
                <p className="text-sm text-red-700 dark:text-red-300 mt-1">
                  {lowStockItems.slice(0, 5).map((item, i) => (
                    <span key={item.id}>
                      <strong>{item.item_name}</strong> ({Math.round(item.quantity)})
                      {i < Math.min(lowStockItems.length, 5) - 1 && ", "}
                    </span>
                  ))}
                  {lowStockItems.length > 5 && (
                    <span> and {lowStockItems.length - 5} more...</span>
                  )}
                </p>
                <Link
                  href="/records?tab=inventory"
                  className="inline-block mt-2 text-sm text-red-800 dark:text-red-200 font-medium hover:underline"
                >
                  View Inventory →
                </Link>
              </div>
            </div>
          </div>
        )}

        {/* Expiry Alert Banner */}
        {expiringItems.length > 0 && (
          <div className="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0">
                <CalendarIcon className="w-5 h-5 text-orange-500" />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-sm font-semibold text-orange-800 dark:text-orange-200">
                  ⏰ {expiringItems.length} medicine{expiringItems.length > 1 ? "s" : ""} expiring soon!
                </h3>
                <p className="text-sm text-orange-700 dark:text-orange-300 mt-1">
                  {expiringItems.slice(0, 3).map((item, i) => (
                    <span key={item.id}>
                      <strong>{item.item_name}</strong> ({item.days_until_expiry} days)
                      {i < Math.min(expiringItems.length, 3) - 1 && ", "}
                    </span>
                  ))}
                  {expiringItems.length > 3 && (
                    <span> and {expiringItems.length - 3} more...</span>
                  )}
                </p>
                <Link
                  href="/records?tab=inventory"
                  className="inline-block mt-2 text-sm text-orange-800 dark:text-orange-200 font-medium hover:underline"
                >
                  View Inventory →
                </Link>
              </div>
            </div>
          </div>
        )}
        
        {/* Trust message */}
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <p className="text-sm text-blue-800 dark:text-blue-200">
            <strong>Human Approval Required:</strong> All agent actions require your explicit approval before execution. Nothing happens without your consent.
          </p>
        </div>

        {/* Last updated */}
        {lastUpdated && (
          <p className="text-xs text-gray-400">
            Last updated: {lastUpdated.toLocaleTimeString()}
          </p>
        )}

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
            <button
              onClick={() => fetchData(true)}
              className="mt-2 text-sm text-primary hover:underline"
            >
              Retry
            </button>
          </div>
        ) : actions.length === 0 ? (
          <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
            <p className="text-gray-500">No agent actions yet.</p>
            <p className="text-sm text-gray-400 mt-1">Actions from Telegram will appear here for your approval.</p>
          </div>
        ) : (
          <div className="bg-white rounded-lg border border-gray-200 overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">
                    Action
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900 hidden sm:table-cell">Time</th>
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

function AlertIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  );
}

function CalendarIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
  );
}
