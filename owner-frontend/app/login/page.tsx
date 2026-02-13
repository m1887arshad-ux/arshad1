"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { PrimaryButton } from "@/components/PrimaryButton";
import { login, register, getCurrentUser, APIError } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [isRegister, setIsRegister] = useState(false);
  const [checkingAuth, setCheckingAuth] = useState(true);

  // Check if already logged in (via httpOnly cookie)
  useEffect(() => {
    async function checkAuth() {
      try {
        await getCurrentUser();
        // If successful, user is already logged in
        router.replace("/dashboard");
      } catch (err) {
        // Not logged in (expected), allow login form
        setCheckingAuth(false);
      }
    }
    checkAuth();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setMessage("");
    if (!email.trim() || !password) {
      setMessage("Email and password required");
      return;
    }
    if (isRegister && password.length < 12) {
      setMessage("Password must be at least 12 characters");
      return;
    }
    setLoading(true);
    try {
      if (isRegister) {
        await register(email.trim(), password);
        setMessage("Registered. Please log in.");
        setIsRegister(false);
        setEmail("");
        setPassword("");
      } else {
        await login(email.trim(), password);
        // Login successful, httpOnly cookie is set by backend
        router.push("/dashboard");
        return;
      }
    } catch (err) {
      const errMsg = err instanceof APIError ? err.message : (err instanceof Error ? err.message : "Something went wrong");
      setMessage(errMsg);
    } finally {
      setLoading(false);
    }
  }

  if (checkingAuth) {
    return (
      <div className="min-h-screen bg-white dark:bg-gray-950 flex items-center justify-center">
        <p className="text-gray-600 dark:text-gray-400">Loading...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white dark:bg-gray-950 flex flex-col items-center justify-center px-4 py-12 transition-colors duration-200">
      <div className="w-full max-w-sm flex flex-col items-center gap-8">
        <div className="text-center">
          <div className="flex items-center justify-center gap-2 mb-2">
            <span className="text-2xl font-bold text-primary">Bharat</span>
            <span className="text-2xl font-normal text-gray-500 dark:text-gray-400">Biz-Agent</span>
          </div>
          <p className="text-gray-700 dark:text-gray-300 font-semibold text-sm">Your business, your control.</p>
        </div>

        <form onSubmit={handleSubmit} className="w-full flex flex-col gap-5">
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-4 py-3 border border-blue-200 dark:border-blue-900 rounded-lg text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-800 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            disabled={loading}
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-4 py-3 border border-blue-200 dark:border-blue-900 rounded-lg text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-800 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            disabled={loading}
          />
          <PrimaryButton type="submit" disabled={loading}>
            {isRegister ? "Register" : "Log in"}
          </PrimaryButton>
        </form>

        {message && <p className="text-sm text-red-600 dark:text-red-400 text-center">{message}</p>}

        <button
          type="button"
          onClick={() => { setIsRegister(!isRegister); setMessage(""); }}
          className="text-primary dark:text-blue-400 hover:underline dark:hover:text-blue-300 text-sm font-medium transition-colors"
        >
          {isRegister ? "Already have an account? Log in" : "Create account"}
        </button>
      </div>
    </div>
  );
}
