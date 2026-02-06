"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { PrimaryButton } from "@/components/PrimaryButton";
import { login, register } from "@/lib/api";

function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("bharat_owner_token");
}

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [isRegister, setIsRegister] = useState(false);

  useEffect(() => {
    if (getStoredToken()) router.replace("/dashboard");
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setMessage("");
    if (!email.trim() || !password) {
      setMessage("Email and password required");
      return;
    }
    if (isRegister && password.length < 6) {
      setMessage("Password must be at least 6 characters");
      return;
    }
    setLoading(true);
    try {
      if (isRegister) {
        await register(email.trim(), password);
        setMessage("Registered. Please log in.");
        setIsRegister(false);
      } else {
        await login(email.trim(), password);
        router.push("/dashboard");
        return;
      }
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-white flex flex-col items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm flex flex-col items-center gap-8">
        <div className="text-center">
          <div className="flex items-center justify-center gap-2 mb-2">
            <span className="text-2xl font-bold text-primary">Bharat</span>
            <span className="text-2xl font-normal text-gray-500">Biz-Agent</span>
          </div>
          <p className="text-gray-700 font-semibold text-sm">Your business, your control.</p>
        </div>

        <form onSubmit={handleSubmit} className="w-full flex flex-col gap-5">
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-4 py-3 border border-blue-200 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            disabled={loading}
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-4 py-3 border border-blue-200 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            disabled={loading}
          />
          <PrimaryButton type="submit" disabled={loading}>
            {isRegister ? "Register" : "Log in"}
          </PrimaryButton>
        </form>

        {message && <p className="text-sm text-red-600 text-center">{message}</p>}

        <button
          type="button"
          onClick={() => { setIsRegister(!isRegister); setMessage(""); }}
          className="text-primary hover:underline text-sm font-medium"
        >
          {isRegister ? "Already have an account? Log in" : "Create account"}
        </button>
      </div>
    </div>
  );
}
