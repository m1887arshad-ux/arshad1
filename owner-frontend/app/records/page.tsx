"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { OwnerShell } from "@/components/OwnerShell";
import { Table } from "@/components/Table";
import { 
  getCurrentUser,
  getCurrentOwner, 
  getInvoices, 
  getLedgerEntries, 
  getInventoryItems,
  addInventoryItem,
  removeInventoryItem,
  exportInvoicesCSV,
  exportInventoryCSV,
} from "@/lib/api";
import type { InventoryItemCreate } from "@/lib/api";

type TabId = "invoices" | "ledger" | "inventory";

// Type aliases for records data
type InvoiceRow = any;
type LedgerRow = any;
type InventoryRow = any;
type InventoryCreateData = InventoryItemCreate;

export default function RecordsPage() {
  const router = useRouter();
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [ownerName, setOwnerName] = useState("Owner");
  const [tab, setTab] = useState<TabId>("invoices");
  const [search, setSearch] = useState("");
  const [invoices, setInvoices] = useState<InvoiceRow[]>([]);
  const [ledger, setLedger] = useState<LedgerRow[]>([]);
  const [inventory, setInventory] = useState<InventoryRow[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Modal state for Add/Edit
  const [showModal, setShowModal] = useState(false);
  const [editingItem, setEditingItem] = useState<InventoryRow | null>(null);
  const [formData, setFormData] = useState<InventoryCreateData>({
    item_name: "",
    quantity: 0,
    price: 50,
    disease: "",
    requires_prescription: false,
  });
  const [formError, setFormError] = useState("");
  const [formLoading, setFormLoading] = useState(false);

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

  // Handle Escape key to close modal
  useEffect(() => {
    if (!showModal) return;
    
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setShowModal(false);
      }
    };
    
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [showModal]);

  useEffect(() => {
    async function loadOwner() {
      if (checkingAuth) return; // Wait for auth check
      
      try {
        const owner = await getCurrentOwner();
        setOwnerName(owner.name);
      } catch {
        window.location.href = "/login";
      }
    }
    loadOwner();
  }, []);

  const loadInventory = useCallback(async () => {
    const data = await getInventoryItems();
    setInventory(data);
  }, []);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        if (tab === "invoices") {
          const data = await getInvoices();
          setInvoices(data);
        } else if (tab === "ledger") {
          const data = await getLedgerEntries();
          setLedger(data);
        } else {
          await loadInventory();
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : "";
        if (msg.includes("not set up") || msg.includes("404")) window.location.href = "/setup";
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [tab, search, loadInventory]);

  const tabs: { id: TabId; label: string }[] = [
    { id: "invoices", label: "Invoices" },
    { id: "ledger", label: "Ledger" },
    { id: "inventory", label: "Inventory" },
  ];

  // Open Add Modal
  const handleAddNew = () => {
    setEditingItem(null);
    setFormData({
      item_name: "",
      quantity: 0,
      price: 50,
      disease: "",
      requires_prescription: false,
    });
    setFormError("");
    setShowModal(true);
  };

  // Open Edit Modal
  const handleEdit = (item: InventoryRow) => {
    setEditingItem(item);
    setFormData({
      item_name: item.item_name,
      quantity: item.quantity,
      price: item.price || 50,
      disease: item.disease || "",
      requires_prescription: item.requires_prescription || false,
    });
    setFormError("");
    setShowModal(true);
  };

  // Delete item
  const handleDelete = async (item: InventoryRow) => {
    if (!confirm(`Are you sure you want to delete "${item.item_name}"?`)) return;
    
    try {
      await removeInventoryItem(item.id);
      await loadInventory();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete");
    }
  };

  // Submit form (Add/Edit)
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError("");
    
    if (!formData.item_name.trim()) {
      setFormError("Medicine name is required");
      return;
    }
    
    setFormLoading(true);
    try {
      if (editingItem) {
        // Delete old item and add new one
        await removeInventoryItem(editingItem.id);
        await addInventoryItem(formData);
      } else {
        await addInventoryItem(formData);
      }
      setShowModal(false);
      setEditingItem(null);
      setFormData({ item_name: "", quantity: 0, price: 50, disease: "", requires_prescription: false });
      await loadInventory();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setFormLoading(false);
    }
  };

  // Export invoices CSV
  const handleExportInvoices = async () => {
    try {
      await exportInvoicesCSV();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to export invoices");
    }
  };

  // Export inventory CSV
  const handleExportInventory = async () => {
    try {
      await exportInventoryCSV();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to export inventory");
    }
  };

  return (
    <OwnerShell title="Records & Ledger" ownerName={ownerName}>
      {checkingAuth ? (
        <div className="flex items-center justify-center p-12">
          <p className="text-gray-600">Loading...</p>
        </div>
      ) : (
      <div className="space-y-6">
        <h2 className="text-2xl font-bold text-gray-900">Records & Ledger</h2>

        <div className="flex border-b border-gray-200 gap-4 md:gap-6 overflow-x-auto">
          {tabs.map(({ id, label }) => (
            <button
              key={id}
              type="button"
              onClick={() => setTab(id)}
              className={`pb-3 text-sm font-semibold border-b-2 transition-colors whitespace-nowrap ${
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
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1 max-w-md">
              <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search invoices by customer or amount"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              />
            </div>
            <button
              onClick={handleExportInvoices}
              className="flex items-center gap-2 px-4 py-3 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 transition-colors whitespace-nowrap"
            >
              <DownloadIcon className="w-5 h-5" />
              Export CSV
            </button>
          </div>
        )}

        {tab === "inventory" && (
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1 max-w-md">
              <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search medicines (e.g., Crocin, Paracetamol)"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              />
            </div>
            <button
              onClick={handleExportInventory}
              className="flex items-center gap-2 px-4 py-3 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 transition-colors whitespace-nowrap"
            >
              <DownloadIcon className="w-5 h-5" />
              Export CSV
            </button>
            <button
              onClick={handleAddNew}
              className="flex items-center gap-2 px-4 py-3 bg-primary text-white font-medium rounded-lg hover:bg-primary/90 transition-colors whitespace-nowrap"
            >
              <PlusIcon className="w-5 h-5" />
              Add Medicine
            </button>
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
          <div className="bg-white rounded-lg border border-gray-200 overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Date</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">
                    Customer
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Amount</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900 hidden sm:table-cell">
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
                    <td className="px-4 py-3 text-sm hidden sm:table-cell">
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
                {search ? "Try a different search term." : "Click 'Add Medicine' to add items."}
              </p>
            </div>
          ) : (
          <div className="bg-white rounded-lg border border-gray-200 overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Medicine</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Quantity</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900 hidden sm:table-cell">Price</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Status</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {inventory.map((row) => (
                  <tr key={row.id} className="hover:bg-gray-50/50">
                    <td className="px-4 py-3 text-sm text-gray-900 font-medium">
                      <div>{row.item_name}</div>
                      {row.requires_prescription && (
                        <span className="text-xs text-red-600">🔴 Rx Required</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-700">{row.quantity}</td>
                    <td className="px-4 py-3 text-sm text-gray-500 hidden sm:table-cell">₹{row.price || 50}</td>
                    <td className="px-4 py-3 text-sm">
                      {row.status === "Low Stock" ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                          ⚠️ Low
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          ✓ OK
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleEdit(row)}
                          className="text-primary hover:text-primary/80 font-medium"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(row)}
                          className="text-red-600 hover:text-red-800 font-medium"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          )
        )}
      </div>
      )}

      {/* Add/Edit Modal */}
      {showModal && (
        <div 
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowModal(false);
          }}
          onKeyDown={(e) => {
            if (e.key === 'Escape') setShowModal(false);
          }}
        >
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">
                  {editingItem ? "Edit Medicine" : "Add New Medicine"}
                </h3>
                <button
                  onClick={() => setShowModal(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <CloseIcon className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Medicine Name *
                  </label>
                  <input
                    type="text"
                    value={formData.item_name}
                    onChange={(e) => setFormData({ ...formData, item_name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="e.g., Paracetamol 500mg"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Quantity
                    </label>
                    <input
                      type="number"
                      value={formData.quantity}
                      onChange={(e) => setFormData({ ...formData, quantity: parseFloat(e.target.value) || 0 })}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                      min="0"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Price (₹)
                    </label>
                    <input
                      type="number"
                      value={formData.price}
                      onChange={(e) => setFormData({ ...formData, price: parseFloat(e.target.value) || 0 })}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                      min="0"
                      step="0.5"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Treats (Disease/Symptoms)
                  </label>
                  <input
                    type="text"
                    value={formData.disease || ""}
                    onChange={(e) => setFormData({ ...formData, disease: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="e.g., Fever, Pain, Headache"
                  />
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="requires_prescription"
                    checked={formData.requires_prescription}
                    onChange={(e) => setFormData({ ...formData, requires_prescription: e.target.checked })}
                    className="w-4 h-4 text-primary rounded focus:ring-primary"
                  />
                  <label htmlFor="requires_prescription" className="text-sm text-gray-700">
                    Requires Prescription (Rx)
                  </label>
                </div>

                {formError && (
                  <p className="text-sm text-red-600">{formError}</p>
                )}

                <div className="flex gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowModal(false)}
                    className="flex-1 px-4 py-2 border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={formLoading}
                    className="flex-1 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50"
                  >
                    {formLoading ? "Saving…" : editingItem ? "Update" : "Add"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

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
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    </svg>
  );
}

function PlusIcon({ className = "" }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
    </svg>
  );
}

function CloseIcon({ className = "" }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  );
}

function DownloadIcon({ className = "" }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
    </svg>
  );
}
