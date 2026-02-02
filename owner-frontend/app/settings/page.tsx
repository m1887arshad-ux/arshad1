"use client";

import { useEffect, useState } from "react";
import { OwnerShell } from "@/components/OwnerShell";
import { getCurrentOwner, getSettings, updateSettings, type OwnerSettings } from "@/lib/api";

const LANGUAGES = ["Hindi", "English", "Hinglish", "Marathi", "Tamil", "Gujarati"];

export default function SettingsPage() {
  const [ownerName, setOwnerName] = useState("Owner");
  const [settings, setSettings] = useState<OwnerSettings | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [owner, s] = await Promise.all([getCurrentOwner(), getSettings()]);
        setOwnerName(owner.name);
        setSettings(s);
      } catch (err) {
        const msg = err instanceof Error ? err.message : "";
        if (msg.includes("not set up") || msg.includes("404")) window.location.href = "/setup";
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function toggle(key: keyof OwnerSettings, value: boolean) {
    if (!settings) return;
    const next = { ...settings, [key]: value };
    setSettings(next);
    await updateSettings(next);
  }

  async function setLanguage(lang: string) {
    if (!settings) return;
    const next = { ...settings, preferredLanguage: lang };
    setSettings(next);
    await updateSettings(next);
  }

  if (loading || !settings) {
    return (
      <OwnerShell title="Control Settings" ownerName={ownerName}>
        <p className="text-gray-500 py-8">Loading…</p>
      </OwnerShell>
    );
  }

  return (
    <OwnerShell title="Control Settings" ownerName={ownerName}>
      <div className="max-w-2xl space-y-8">
        <h2 className="text-2xl font-bold text-gray-900">Owner Control Panel</h2>

        {/* Trust & Safety notice */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-sm text-blue-800">
            <strong>Your Control:</strong> These settings determine how the agent operates. All changes are logged for audit purposes.
          </p>
        </div>

        <section>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Safety Controls</h3>
          <div className="space-y-4">
            <ToggleCard
              label="Require approval for all invoices"
              description="When enabled, all invoices require your explicit approval before being sent."
              checked={settings.requireApprovalForInvoices}
              onToggle={(v) => toggle("requireApprovalForInvoices", v)}
              icon={<DocIcon />}
              warning={!settings.requireApprovalForInvoices}
            />
            <ToggleCard
              label="WhatsApp notifications"
              description="Receive notifications when actions need your attention."
              checked={settings.whatsAppNotifications}
              onToggle={(v) => toggle("whatsAppNotifications", v)}
              icon={<WhatsAppIcon />}
            />
            <ToggleCard
              label="Enable Agent Actions"
              description="Allow the agent to process incoming requests and create drafts."
              checked={settings.agentActionsEnabled}
              onToggle={(v) => toggle("agentActionsEnabled", v)}
              icon={<AgentIcon />}
            />
          </div>
        </section>

        <section>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Language Preferences</h3>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Preferred Language
            </label>
            <select
              value={settings.preferredLanguage}
              onChange={(e) => setLanguage(e.target.value)}
              className="w-full px-4 py-3 border border-gray-200 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            >
              {LANGUAGES.map((lang) => (
                <option key={lang} value={lang}>
                  {lang}
                </option>
              ))}
            </select>
          </div>
        </section>

        {/* Audit log notice */}
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <p className="text-xs text-gray-500">
            All setting changes are logged. For audit logs, contact support.
          </p>
        </div>
      </div>
    </OwnerShell>
  );
}

function ToggleCard({
  label,
  description,
  checked,
  onToggle,
  icon,
  warning,
}: {
  label: string;
  description?: string;
  checked: boolean;
  onToggle: (v: boolean) => void;
  icon: React.ReactNode;
  warning?: boolean;
}) {
  return (
    <div className={`bg-white rounded-xl border p-4 flex items-center justify-between gap-4 ${warning ? "border-orange-300 bg-orange-50" : "border-gray-200"}`}>
      <div className="flex items-center gap-3 flex-1">
        <button
          type="button"
          role="switch"
          aria-checked={checked}
          onClick={() => onToggle(!checked)}
          className={`relative inline-flex h-7 w-12 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 ${
            checked ? "bg-primary" : "bg-gray-200"
          }`}
        >
          <span
            className={`pointer-events-none inline-block h-6 w-6 transform rounded-full bg-white shadow ring-0 transition-transform ${
              checked ? "translate-x-5" : "translate-x-1"
            }`}
          />
        </button>
        <div>
          <span className="text-sm font-medium text-gray-900">{label}</span>
          {description && <p className="text-xs text-gray-500 mt-0.5">{description}</p>}
          {warning && <p className="text-xs text-orange-600 mt-0.5 font-medium">⚠️ Disabling this reduces safety controls</p>}
        </div>
      </div>
      <div className="text-gray-400">{icon}</div>
    </div>
  );
}

function DocIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586L17 7.586V19a2 2 0 01-2 2z" />
    </svg>
  );
}

function WhatsAppIcon() {
  return (
    <svg className="w-5 h-5 text-green-500" viewBox="0 0 24 24" fill="currentColor">
      <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z" />
    </svg>
  );
}

function AgentIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
    </svg>
  );
}
