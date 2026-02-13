"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { PrimaryButton } from "@/components/PrimaryButton";
import { setupBusiness, getCurrentUser } from "@/lib/api";

const STEPS = [
  { id: 1, title: "Basic Information" },
  { id: 2, title: "Business Details" },
  { id: 3, title: "Confirm & Finish" },
];

const LANGUAGES = ["Hindi", "English", "Hinglish", "Marathi", "Tamil", "Gujarati"];

export default function SetupPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [businessName, setBusinessName] = useState("");
  const [ownerName, setOwnerName] = useState("");
  const [language, setLanguage] = useState("");
  const [languageOpen, setLanguageOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function checkAuth() {
      try {
        await getCurrentUser();
        // User is logged in, allow setup
      } catch (err) {
        // Not logged in, redirect to login
        router.replace("/login");
      }
    }
    checkAuth();
  }, []);

  async function handleNext() {
    if (step < 3) {
      setStep(step + 1);
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      await setupBusiness(businessName.trim() || "My Business", ownerName.trim() || "Owner", language || "English");
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Setup failed");
    } finally {
      setSubmitting(false);
    }
  }

  const currentStepInfo = STEPS[step - 1];

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-lg bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="card-spacing flex flex-col gap-8">
          {/* Step indicator */}
          <div className="flex flex-col items-center gap-2">
            <div className="flex items-center gap-0">
              {STEPS.map((s, i) => (
                <div key={s.id} className="flex items-center">
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold ${
                      step >= s.id ? "bg-primary text-white" : "bg-gray-200 text-gray-500"
                    }`}
                  >
                    {s.id}
                  </div>
                  {i < STEPS.length - 1 && (
                    <div
                      className={`w-12 h-0.5 ${step > s.id ? "bg-primary" : "bg-gray-200"}`}
                    />
                  )}
                </div>
              ))}
            </div>
            <p className="text-sm text-gray-500">
              Step {step} of 3: {currentStepInfo.title}
            </p>
          </div>

          <h2 className="text-xl font-bold text-primary">Business Setup Wizard</h2>
          <p className="text-gray-600 text-sm">
            Welcome to Bharat Biz-Agent. Let&apos;s get your business set up for success, starting
            with the basics. Your trusted AI assistant is here to help.
          </p>

          {step === 1 && (
            <div className="flex flex-col gap-5">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Business Name
                </label>
                <input
                  type="text"
                  placeholder="Enter your business name"
                  value={businessName}
                  onChange={(e) => setBusinessName(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Owner Name</label>
                <input
                  type="text"
                  placeholder="Enter your full name"
                  value={ownerName}
                  onChange={(e) => setOwnerName(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                />
              </div>
              <div className="relative">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Preferred Language
                </label>
                <button
                  type="button"
                  onClick={() => setLanguageOpen(!languageOpen)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg text-left text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary flex items-center justify-between"
                >
                  <span className={language ? "text-gray-900" : "text-gray-400"}>
                    {language || "Select language (e.g., Hindi, English, Hinglish)"}
                  </span>
                  <ChevronDown className={languageOpen ? "rotate-180" : ""} />
                </button>
                {languageOpen && (
                  <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                    {LANGUAGES.map((lang) => (
                      <button
                        key={lang}
                        type="button"
                        onClick={() => {
                          setLanguage(lang);
                          setLanguageOpen(false);
                        }}
                        className="w-full px-4 py-2.5 text-left text-gray-900 hover:bg-gray-50 text-sm"
                      >
                        {lang}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="flex flex-col gap-5">
              <p className="text-gray-600 text-sm">
                Add business type, address, and GST if applicable. (Mock step — local state only.)
              </p>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Business Type</label>
                <input
                  type="text"
                  placeholder="e.g. Retail, Services"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                />
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="flex flex-col gap-3">
              <p className="text-gray-600 text-sm">Review and confirm. (Mock — no API call.)</p>
              <dl className="bg-gray-50 rounded-lg p-4 space-y-2 text-sm">
                <div>
                  <dt className="text-gray-500">Business</dt>
                  <dd className="font-medium text-gray-900">{businessName || "—"}</dd>
                </div>
                <div>
                  <dt className="text-gray-500">Owner</dt>
                  <dd className="font-medium text-gray-900">{ownerName || "—"}</dd>
                </div>
                <div>
                  <dt className="text-gray-500">Language</dt>
                  <dd className="font-medium text-gray-900">{language || "—"}</dd>
                </div>
              </dl>
            </div>
          )}

          {error && <p className="text-sm text-red-600">{error}</p>}
          <PrimaryButton onClick={handleNext} disabled={submitting}>
            {step < 3 ? "Next" : submitting ? "Saving…" : "Finish"}
          </PrimaryButton>
        </div>
      </div>
    </div>
  );
}

function ChevronDown({ className = "" }: { className?: string }) {
  return (
    <svg
      className={`w-5 h-5 text-gray-400 transition-transform ${className}`}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
    </svg>
  );
}
