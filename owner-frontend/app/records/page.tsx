"use client";

import { useEffect, useState } from "react";
import { OwnerShell } from "@/components/OwnerShell";
import { Table } from "@/components/Table";
import { getCurrentOwner, getInvoices, getLedgerEntries, getInventoryItems } from "@/lib/api";
import type { InvoiceRow, LedgerRow, InventoryRow } from "@/lib/api";

type TabId = "invoices" | "ledger" | "inventory";

export default function RecordsPage() {
  const [ownerName, setOwnerName] = useState("Owner");
  const [tab, setTab] = useState<TabId>("invoices");
  const [search, setSearch] = useState("");
  const [invoices, setInvoices] = useState<InvoiceRow[]>([]);
  const [ledger, setLedger] = useState<LedgerRow[]>([]);
  const [inventory, setInventory] = useState<InventoryRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadOwner() {
      try {
        const owner = await getCurrentOwner();
        setOwnerName(owner.name);
      } catch {
        window.location.href = "/login";
      }
    }
    loadOwner();
  }, []);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        if (tab === "invoices") {
          const data = await getInvoices(search);
          setInvoices(data);
        } else if (tab === "ledger") {
          const data = await getLedgerEntries();
          setLedger(data);
        } else {
          const data = await getInventoryItems(search);
          setInventory(data);
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : "";
        if (msg.includes("not set up") || msg.includes("404")) window.location.href = "/setup";
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [tab, search]);

  const tabs: { id: TabId; label: string }[] = [
    { id: "invoices", label: "Invoices" },
    { id: "ledger", label: "Ledger" },
    { id: "inventory", label: "Inventory" },
  ];

  return (
    <OwnerShell title="Records & Ledger" ownerName={ownerName}>
      <div className="space-y-6">
        <h2 className="text-2xl font-bold text-gray-900">Records & Ledger</h2>

        <div className="flex border-b border-gray-200 gap-6">
          {tabs.map(({ id, label }) => (
            <button
              key={id}
              type="button"
              onClick={() => setTab(id)}
              className={`pb-3 text-sm font-semibold border-b-2 transition-colors ${
                tab === id
                  ? "border-primary text-primary"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {tab === "invoices" && (
          <div className="relative max-w-md">
            <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search invoices by customer or amount"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            />
          </div>
        )}

        {tab === "inventory" && (
          <div className="relative max-w-md">
            <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search medicines (e.g., Crocin, Paracetamol)"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            />
          </div>
        )}

        {loading ? (
          <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
            <div className="animate-pulse text-gray-500">Loading records…</div>
          </div>
        ) : tab === "invoices" ? (
          invoices.length === 0 ? (
            <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
              <p className="text-gray-500">No invoices found.</p>
              <p className="text-sm text-gray-400 mt-1">Approved invoice actions will appear here.</p>
            </div>
          ) : (
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Date</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">
                    Customer
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Amount</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">
                    View/Download
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {invoices.map((row, i) => (
                  <tr key={i} className="hover:bg-gray-50/50">
                    <td className="px-4 py-3 text-sm text-gray-700">{row.date}</td>
                    <td className="px-4 py-3 text-sm text-gray-700">{row.customer}</td>
                    <td className="px-4 py-3 text-sm text-gray-700">{row.amount}</td>
                    <td className="px-4 py-3 text-sm">
                      <span className="text-primary hover:underline cursor-pointer">
                        View PDF
                      </span>
                      <span className="text-gray-400 mx-1">/</span>
                      <span className="text-primary hover:underline cursor-pointer">
                        Download
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          )
        ) : tab === "ledger" ? (
          ledger.length === 0 ? (
            <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
              <p className="text-gray-500">No ledger entries found.</p>
              <p className="text-sm text-gray-400 mt-1">Ledger entries are created when invoices are approved.</p>
            </div>
          ) : (
          <Table<LedgerRow>
            keyField="description"
            columns={[
              { key: "date", header: "Date" },
              { key: "description", header: "Description" },
              { key: "debit", header: "Debit" },
              { key: "credit", header: "Credit" },
              { key: "balance", header: "Balance" },
            ]}
            data={ledger}
          />
          )
        ) : (
          inventory.length === 0 ? (
            <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
              <p className="text-gray-500">No inventory items found.</p>
              <p className="text-sm text-gray-400 mt-1">
                {search ? "Try a different search term." : "Add medicines using seed script or API."}
              </p>
            </div>
          ) : (
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Medicine</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Quantity</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Unit</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Status</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {inventory.map((row) => (
                  <tr key={row.id} className="hover:bg-gray-50/50">
                    <td className="px-4 py-3 text-sm text-gray-900 font-medium">{row.item_name}</td>
                    <td className="px-4 py-3 text-sm text-gray-700">{row.quantity}</td>
                    <td className="px-4 py-3 text-sm text-gray-500">{row.unit}</td>
                    <td className="px-4 py-3 text-sm">
                      {row.status === "Low Stock" ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                          ⚠️ Low Stock
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          ✓ In Stock
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          )
        )}
      </div>

      <footer className="mt-12 pt-6 border-t border-gray-200 text-center text-sm text-gray-500 space-x-4">
        <a href="#" className="hover:text-primary">Help & Support</a>
        <a href="#" className="hover:text-primary">Privacy Policy</a>
        <a href="#" className="hover:text-primary">Terms of Service</a>
      </footer>
    </OwnerShell>
  );
}

function SearchIcon({ className = "" }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
      />
    </svg>
  );
}
