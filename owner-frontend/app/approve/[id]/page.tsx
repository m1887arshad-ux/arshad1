"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { OwnerShell } from "@/components/OwnerShell";
import { PrimaryButton } from "@/components/PrimaryButton";
import {
  getActionById,
  approveAction,
  rejectAction,
  getCurrentOwner,
  type ActionDetail,
  type Owner,
} from "@/lib/api";

export default function ApproveActionPage() {
  const params = useParams();
  const router = useRouter();
  const id = String(params?.id ?? "");
  const [action, setAction] = useState<ActionDetail | null>(null);
  const [owner, setOwner] = useState<Owner | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [showConfirm, setShowConfirm] = useState<"approve" | "reject" | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [detail, ownerData] = await Promise.all([getActionById(id), getCurrentOwner()]);
        setAction(detail ?? null);
        setOwner(ownerData);
      } finally {
        setLoading(false);
      }
    }
    if (id) load();
  }, [id]);

  async function handleApprove() {
    if (!action || action.status !== "Pending" || submitting) return;
    setSubmitting(true);
    setError("");
    try {
      const res = await approveAction(action.id);
      if (res.ok) router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to approve action");
      setShowConfirm(null);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleReject() {
    if (!action || action.status !== "Pending" || submitting) return;
    setSubmitting(true);
    setError("");
    try {
      const res = await rejectAction(action.id);
      if (res.ok) router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reject action");
      setShowConfirm(null);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <OwnerShell title="Action Approval Details" ownerName={owner?.name ?? "Owner"}>
        <div className="flex items-center justify-center py-12">
          <div className="animate-pulse text-gray-500">Loading action details…</div>
        </div>
      </OwnerShell>
    );
  }

  if (!action) {
    return (
      <OwnerShell title="Action Approval Details" ownerName={owner?.name ?? "Owner"}>
        <div className="max-w-2xl mx-auto text-center py-12">
          <p className="text-gray-500">Action not found.</p>
          <Link href="/dashboard" className="text-primary hover:underline mt-4 inline-block">
            ← Back to dashboard
          </Link>
        </div>
      </OwnerShell>
    );
  }

  const detailItems = [
    { icon: DocIcon, label: "Action Type", value: action.actionType },
    { icon: UserIcon, label: "Customer Name", value: action.customerName },
    { icon: RupeeIcon, label: "Amount", value: action.amount },
    { icon: ChannelIcon, label: "Channel", value: action.channel },
  ];

  const isPending = action.status === "Pending";

  return (
    <OwnerShell title="Action Approval Details" ownerName={owner?.name ?? "Owner"}>
      <div className="max-w-2xl mx-auto space-y-6">
        <h2 className="text-2xl font-bold text-gray-900">Action Approval Details</h2>

        {/* Human approval required banner */}
        {isPending && (
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
            <p className="text-sm text-orange-800 font-medium">
              ⚠️ This action requires your approval before it can be executed.
            </p>
          </div>
        )}

        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="card-spacing space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">
                {isPending ? "Pending Task:" : "Task:"} {action.title}
              </h3>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                action.status === "Pending" ? "bg-pending text-white" :
                action.status === "Approved" || action.status === "Executed" ? "bg-approved text-white" :
                "bg-gray-500 text-white"
              }`}>
                {action.status}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-4">
              {detailItems.map(({ icon: Icon, label, value }) => (
                <div
                  key={label}
                  className="border border-gray-200 rounded-lg p-4 flex items-start gap-3"
                >
                  <Icon />
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                      {label}
                    </p>
                    <p className="text-sm font-semibold text-gray-900 mt-0.5">{value}</p>
                  </div>
                </div>
              ))}
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
              <SpeechIcon />
              <div>
                <p className="text-xs font-medium text-blue-800 uppercase tracking-wide">
                  Agent Explanation
                </p>
                <p className="text-sm text-gray-900 mt-0.5">{action.agentExplanation}</p>
              </div>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-600">
                {error}
              </div>
            )}

            {isPending && !showConfirm && (
              <div className="flex gap-4 pt-2">
                <PrimaryButton
                  variant="approve"
                  onClick={() => setShowConfirm("approve")}
                  disabled={submitting}
                  icon={<CheckIcon />}
                >
                  Approve
                </PrimaryButton>
                <PrimaryButton
                  variant="reject"
                  onClick={() => setShowConfirm("reject")}
                  disabled={submitting}
                  icon={<CrossIcon />}
                >
                  Reject
                </PrimaryButton>
              </div>
            )}

            {/* Confirmation dialog */}
            {showConfirm && (
              <div className="border-t border-gray-200 pt-4 mt-4">
                <p className="text-sm font-medium text-gray-900 mb-3">
                  {showConfirm === "approve"
                    ? "Are you sure you want to APPROVE this action? This will execute the invoice creation."
                    : "Are you sure you want to REJECT this action? This cannot be undone."}
                </p>
                <div className="flex gap-3">
                  <PrimaryButton
                    variant={showConfirm === "approve" ? "approve" : "reject"}
                    onClick={showConfirm === "approve" ? handleApprove : handleReject}
                    disabled={submitting}
                  >
                    {submitting ? "Processing…" : `Confirm ${showConfirm === "approve" ? "Approval" : "Rejection"}`}
                  </PrimaryButton>
                  <PrimaryButton
                    variant="secondary"
                    onClick={() => setShowConfirm(null)}
                    disabled={submitting}
                  >
                    Cancel
                  </PrimaryButton>
                </div>
              </div>
            )}

            {!isPending && (
              <div className="text-sm text-gray-500 pt-2">
                This action has already been {action.status.toLowerCase()}.
              </div>
            )}
          </div>
        </div>

        <p className="text-sm text-gray-500">
          <Link href="/dashboard" className="text-primary hover:underline">
            ← Back to dashboard
          </Link>
        </p>
      </div>
    </OwnerShell>
  );
}

function DocIcon() {
  return (
    <svg className="w-5 h-5 text-gray-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586L17 7.586V19a2 2 0 01-2 2z" />
    </svg>
  );
}

function UserIcon() {
  return (
    <svg className="w-5 h-5 text-gray-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
    </svg>
  );
}

function RupeeIcon() {
  return (
    <span className="w-5 h-5 flex items-center justify-center text-gray-500 font-semibold text-sm shrink-0">
      ₹
    </span>
  );
}

function ChannelIcon() {
  return (
    <svg className="w-5 h-5 text-gray-500 shrink-0" fill="currentColor" viewBox="0 0 24 24">
      <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z" />
    </svg>
  );
}

function SpeechIcon() {
  return (
    <svg className="w-5 h-5 text-blue-600 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  );
}

function CrossIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  );
}
