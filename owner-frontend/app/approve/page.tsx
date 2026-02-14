"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { OwnerShell } from "@/components/OwnerShell";
import { getCurrentUser, getCurrentOwner } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type AgentAction = {
  id: number;
  business_id: number;
  intent: string;
  status: string;
  explanation: string | null;
  created_at: string;
  payload?: {
    product?: string;
    quantity?: number;
    amount?: number;
    customer?: string;
    product_id?: number;
    source?: string;
    ocr_detected_name?: string;
  };
};

export default function ApprovePage() {
  const router = useRouter();
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [ownerName, setOwnerName] = useState("Owner");
  const [pending, setPending] = useState<AgentAction[]>([]);
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState<number | null>(null);
  const [rejecting, setRejecting] = useState<number | null>(null);
  const [toast, setToast] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Check auth before rendering
  useEffect(() => {
    async function checkAuth() {
      try {
        await getCurrentUser();
        setCheckingAuth(false);
      } catch (err) {
        router.replace("/login");
      }
    }
    checkAuth();
  }, []);

  useEffect(() => {
    async function load() {
      if (checkingAuth) return;
      
      try {
        const owner = await getCurrentOwner();
        setOwnerName(owner.name);
        
        // Fetch pending actions
        const token = localStorage.getItem("bharat_owner_token");
        const res = await fetch(`${API_BASE}/agent/pending`, {
          headers: {
            "Authorization": `Bearer ${token}`,
            "Content-Type": "application/json"
          }
        });
        
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        const actions = await res.json();
        setPending(actions);
      } catch (err) {
        const msg = err instanceof Error ? err.message : "";
        if (msg.includes("not set up") || msg.includes("404")) {
          window.location.href = "/setup";
          return;
        }
        console.error("Load error:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [checkingAuth]);

  const handleApprove = async (actionId: number) => {
    setApproving(actionId);
    try {
      const token = localStorage.getItem("bharat_owner_token");
      const res = await fetch(`${API_BASE}/agent/actions/${actionId}/approve`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        }
      });
      
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || "Approval failed");
      }
      
      // Remove from pending list
      setPending(pending.filter(p => p.id !== actionId));
      setToast({ type: "success", message: "Order approved and created!" });
      setTimeout(() => setToast(null), 3000);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to approve";
      setToast({ type: "error", message: msg });
      setTimeout(() => setToast(null), 3000);
    } finally {
      setApproving(null);
    }
  };

  const handleReject = async (actionId: number) => {
    setRejecting(actionId);
    try {
      const token = localStorage.getItem("bharat_owner_token");
      const res = await fetch(`${API_BASE}/agent/actions/${actionId}/reject`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        }
      });
      
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || "Rejection failed");
      }
      
      // Remove from pending list
      setPending(pending.filter(p => p.id !== actionId));
      setToast({ type: "success", message: "Order rejected" });
      setTimeout(() => setToast(null), 3000);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to reject";
      setToast({ type: "error", message: msg });
      setTimeout(() => setToast(null), 3000);
    } finally {
      setRejecting(null);
    }
  };

  if (loading || !checkingAuth === false) {
    return (
      <OwnerShell title="Approve Orders" ownerName={ownerName}>
        <p className="text-gray-500 py-8">Loading...</p>
      </OwnerShell>
    );
  }

  return (
    <OwnerShell title="Approve Orders" ownerName={ownerName}>
      {/* Toast notification */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium ${
          toast.type === "success" ? "bg-green-500 text-white" : "bg-red-500 text-white"
        }`}>
          {toast.message}
        </div>
      )}

      <div className="max-w-4xl space-y-4">
        <h2 className="text-2xl font-bold text-gray-900">Pending Orders</h2>
        
        {pending.length === 0 ? (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 text-center">
            <p className="text-blue-800">✓ No pending orders. All caught up!</p>
          </div>
        ) : (
          <div className="space-y-3">
            {pending.map((action) => (
              <div
                key={action.id}
                className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-sm font-bold text-gray-600">#{action.id}</span>
                      {action.payload?.source === "ocr" && (
                        <span className="px-2 py-1 bg-purple-100 text-purple-800 text-xs font-medium rounded">
                          OCR
                        </span>
                      )}
                      <span className="text-xs text-gray-500">
                        {new Date(action.created_at).toLocaleString()}
                      </span>
                    </div>
                    
                    <div className="space-y-2">
                      <p className="text-lg font-semibold text-gray-900">
                        {action.payload?.product || "Unknown Product"}
                      </p>
                      
                      <div className="text-sm text-gray-600 space-y-1">
                        <p>
                          <span className="font-medium">Quantity:</span> {action.payload?.quantity || "N/A"}
                        </p>
                        <p>
                          <span className="font-medium">Customer:</span> {action.payload?.customer || "N/A"}
                        </p>
                        <p>
                          <span className="font-medium">Amount:</span> ₹
                          {action.payload?.amount ? action.payload.amount.toFixed(2) : "0.00"}
                        </p>
                        
                        {action.payload?.ocr_detected_name && (
                          <p className="text-xs bg-gray-50 p-2 rounded">
                            <span className="font-medium">OCR Detected:</span> {action.payload.ocr_detected_name}
                          </p>
                        )}
                      </div>
                      
                      {action.explanation && (
                        <p className="text-xs text-gray-500 italic">{action.explanation}</p>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleApprove(action.id)}
                      disabled={approving === action.id}
                      className="px-4 py-2 bg-green-500 text-white text-sm font-medium rounded hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed transition"
                    >
                      {approving === action.id ? "..." : "✓ Approve"}
                    </button>
                    <button
                      onClick={() => handleReject(action.id)}
                      disabled={rejecting === action.id}
                      className="px-4 py-2 bg-red-500 text-white text-sm font-medium rounded hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed transition"
                    >
                      {rejecting === action.id ? "..." : "✗ Reject"}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm text-gray-600">
          <p>
            <strong>How it works:</strong>
          </p>
          <ul className="list-disc list-inside mt-2 space-y-1">
            <li>OCR orders are created from prescription images</li>
            <li>Manual orders are created from Telegram messages</li>
            <li>Review details carefully before approving</li>
            <li>Approved orders create invoices and update inventory</li>
          </ul>
        </div>
      </div>
    </OwnerShell>
  );
}
