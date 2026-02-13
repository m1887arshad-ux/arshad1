"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { OwnerShell } from "@/components/OwnerShell";
import {
  getCurrentUser,
  getCurrentOwner,
  getAnalyticsSummary,
  getDailySales,
  getTopProducts,
  getActionStats,
  type AnalyticsSummary,
  type DailySalesData,
  type TopProductData,
  type ActionStats,
} from "@/lib/api";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
  LineChart,
  Line,
} from "recharts";


export default function AnalyticsPage() {
  const router = useRouter();
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [ownerName, setOwnerName] = useState("Owner");
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [dailySales, setDailySales] = useState<DailySalesData[]>([]);
  const [topProducts, setTopProducts] = useState<TopProductData[]>([]);
  const [actionStats, setActionStats] = useState<ActionStats | null>(null);
  const [loading, setLoading] = useState(true);

  // Check auth before rendering
  useEffect(() => {
    async function checkAuth() {
      try {
        await getCurrentUser();
        // Auth successful
        setCheckingAuth(false);
      } catch (err) {
        // Not logged in
        router.replace("/login");
      }
    }
    checkAuth();
  }, []);

  useEffect(() => {
    async function load() {
      if (checkingAuth) return;
      try {
        const [owner, summaryData, sales, products, stats] = await Promise.all([
          getCurrentOwner(),
          getAnalyticsSummary(),
          getDailySales(7),
          getTopProducts(5),
          getActionStats(),
        ]);
        setOwnerName(owner.name);
        setSummary(summaryData);
        setDailySales(sales);
        setTopProducts(products);
        setActionStats(stats);
      } catch (err) {
        const msg = err instanceof Error ? err.message : "";
        if (msg.includes("not set up") || msg.includes("404")) {
          window.location.href = "/setup";
          return;
        }
        console.error("Analytics load error:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [checkingAuth]);

  const actionPieData = actionStats
    ? [
        { name: "Pending", value: actionStats.pending, color: "#f59e0b" },
        { name: "Approved", value: actionStats.approved, color: "#3b82f6" },
        { name: "Executed", value: actionStats.executed, color: "#10b981" },
        { name: "Rejected", value: actionStats.rejected, color: "#ef4444" },
      ].filter((d) => d.value > 0)
    : [];

  return (
    <OwnerShell title="Analytics" ownerName={ownerName}>
      {checkingAuth ? (
        <div className="flex items-center justify-center p-12">
          <p className="text-gray-900">Loading...</p>
        </div>
      ) : (
      <div className="space-y-6 text-gray-900">
        <h2 className="text-2xl font-bold text-black">Business Analytics</h2>

        {loading ? (
          <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
            <div className="animate-pulse text-black">Loading analytics…</div>
          </div>
        ) : (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              <SummaryCard
                title="Total Revenue"
                value={`₹${(summary?.total_revenue || 0).toLocaleString("en-IN")}`}
                icon={<RupeeIcon />}
                color="bg-green-500"
              />
              <SummaryCard
                title="Today's Revenue"
                value={`₹${(summary?.today_revenue || 0).toLocaleString("en-IN")}`}
                icon={<TrendUpIcon />}
                color="bg-blue-500"
              />
              <SummaryCard
                title="Total Invoices"
                value={String(summary?.total_invoices || 0)}
                icon={<DocIcon />}
                color="bg-purple-500"
              />
              <SummaryCard
                title="Customers"
                value={String(summary?.total_customers || 0)}
                icon={<UsersIcon />}
                color="bg-indigo-500"
              />
              <SummaryCard
                title="Pending Actions"
                value={String(summary?.pending_actions || 0)}
                icon={<ClockIcon />}
                color="bg-amber-500"
              />
              <SummaryCard
                title="Low Stock Items"
                value={String(summary?.low_stock_count || 0)}
                icon={<AlertIcon />}
                color="bg-red-500"
              />
            </div>

            {/* Charts Row 1: Sales + Action Stats */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Daily Sales Bar Chart */}
              <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 p-6">
                <h3 className="text-lg font-semibold text-black mb-4">
                  Daily Sales (Last 7 Days)
                </h3>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={dailySales}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="#111827" />
                      <YAxis tick={{ fontSize: 12 }} stroke="#111827" />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#fff",
                          border: "1px solid #e5e7eb",
                          borderRadius: "8px",
                          color: "#111827",
                        }}
                        formatter={(value: number) => [`₹${value.toLocaleString("en-IN")}`, "Revenue"]}
                      />
                      <Bar dataKey="revenue" fill="#6366f1" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Action Stats Pie Chart */}
              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <h3 className="text-lg font-semibold text-black mb-4">Action Status</h3>
                <div className="h-72">
                  {actionPieData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={actionPieData}
                          cx="50%"
                          cy="50%"
                          innerRadius={50}
                          outerRadius={80}
                          paddingAngle={2}
                          dataKey="value"
                          label={({ name, percent }: { name: string; percent: number }) =>
                            `${name} ${(percent * 100).toFixed(0)}%`
                          }
                          labelLine={false}
                        >
                          {actionPieData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <Legend wrapperStyle={{ color: "#111827" }} />
                        <Tooltip contentStyle={{ color: "#111827" }} />
                      </PieChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="flex items-center justify-center h-full text-black">
                      No action data yet
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Charts Row 2: Revenue Trend + Top Products */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Revenue Trend Line Chart */}
              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <h3 className="text-lg font-semibold text-black mb-4">
                  Revenue Trend
                </h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={dailySales}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="#111827" />
                      <YAxis tick={{ fontSize: 12 }} stroke="#111827" />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#fff",
                          border: "1px solid #e5e7eb",
                          borderRadius: "8px",
                          color: "#111827",
                        }}
                        formatter={(value: number) => [`₹${value.toLocaleString("en-IN")}`, "Revenue"]}
                      />
                      <Line
                        type="monotone"
                        dataKey="revenue"
                        stroke="#10b981"
                        strokeWidth={2}
                        dot={{ fill: "#10b981", strokeWidth: 2 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Top Products */}
              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <h3 className="text-lg font-semibold text-black mb-4">
                  Top Products by Stock
                </h3>
                <div className="h-64">
                  {topProducts.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={topProducts} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis type="number" tick={{ fontSize: 12 }} stroke="#111827" />
                        <YAxis
                          dataKey="name"
                          type="category"
                          tick={{ fontSize: 12 }}
                          stroke="#111827"
                          width={80}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "#fff",
                            border: "1px solid #e5e7eb",
                            borderRadius: "8px",
                            color: "#111827",
                          }}
                          formatter={(value: number) => [`${value} units`, "Stock"]}
                        />
                        <Bar dataKey="quantity" radius={[0, 4, 4, 0]}>
                          {topProducts.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="flex items-center justify-center h-full text-black">
                      No product data yet
                    </div>
                  )}
                </div>
              </div>
            </div>
          </>
        )}
      </div>
      )}
    </OwnerShell>
  );
}

// Summary Card Component
function SummaryCard({
  title,
  value,
  icon,
  color,
}: {
  title: string;
  value: string;
  icon: React.ReactNode;
  color: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div className="flex items-center gap-3">
        <div className={`${color} text-white p-2 rounded-lg`}>{icon}</div>
        <div className="min-w-0">
          <p className="text-xs text-black truncate">{title}</p>
          <p className="text-lg font-bold text-black truncate">{value}</p>
        </div>
      </div>
    </div>
  );
}

// Icons
function RupeeIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 8h6m-5 0a3 3 0 110 6H9l3 3m-3-6h6m6 1a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}

function TrendUpIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
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

function UsersIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
    </svg>
  );
}

function ClockIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}

function AlertIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  );
}
