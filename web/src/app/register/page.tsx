"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertCircle, Scale, WifiOff } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { ApiError } from "@/lib/api";

const inputCls = "w-full rounded-xl bg-[#1a1a1a] border border-white/10 px-4 py-2.5 text-sm text-white placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-[#3ecf8e]/50 focus:border-[#3ecf8e]/50 transition-colors";

type ErrorKind = "auth" | "server" | "network";

interface FormError {
  kind: ErrorKind;
  message: string;
}

function classifyError(err: unknown): FormError {
  if (err instanceof ApiError) {
    switch (err.status) {
      case 0:
        return err.message === "timeout"
          ? { kind: "network", message: "Request timed out — is the server running?" }
          : { kind: "network", message: "Cannot reach the server — is it running?" };
      case 409:
        return { kind: "auth", message: "This email is already registered" };
      case 422:
        return { kind: "auth", message: "Invalid format — check email and password (min 8 chars)" };
      case 429:
        return { kind: "server", message: "Too many attempts — wait a few minutes" };
      case 500:
      case 502:
      case 503:
        return { kind: "server", message: "Server error — try again later" };
      default:
        return { kind: "auth", message: err.message };
    }
  }
  return { kind: "network", message: "Unexpected error — try again" };
}

const ERROR_STYLE: Record<ErrorKind, string> = {
  auth:    "bg-red-500/10 border-red-500/25 text-red-400",
  server:  "bg-amber-500/10 border-amber-500/25 text-amber-400",
  network: "bg-amber-500/10 border-amber-500/25 text-amber-400",
};

const ERROR_ICON: Record<ErrorKind, React.ReactNode> = {
  auth:    <AlertCircle size={14} className="shrink-0 mt-0.5" />,
  server:  <AlertCircle size={14} className="shrink-0 mt-0.5" />,
  network: <WifiOff size={14} className="shrink-0 mt-0.5" />,
};

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<FormError | null>(null);
  const [stage, setStage] = useState<"submitting" | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setStage("submitting");
    try {
      await register(email, password);
      router.push("/dashboard");
    } catch (err) {
      setError(classifyError(err));
    } finally {
      setStage(null);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0c0c0c] px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="mb-3 flex justify-center">
            <Scale size={32} className="text-[#3ecf8e]" />
          </div>
          <h1 className="text-2xl font-bold text-white">Create account</h1>
          <p className="mt-1 text-sm text-zinc-500">Start fact-checking in seconds</p>
        </div>

        <form onSubmit={handleSubmit} className="rounded-xl bg-[#1a1a1a] border border-white/10 p-6 space-y-4">
          {error && (
            <div className={`flex items-start gap-2 rounded-xl border px-3 py-2.5 text-sm ${ERROR_STYLE[error.kind]}`}>
              {ERROR_ICON[error.kind]}
              <span>{error.message}</span>
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-1.5">Email</label>
            <input
              type="email" required value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={inputCls}
              placeholder="you@example.com"
              autoComplete="email"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-1.5">Password</label>
            <input
              type="password" required minLength={8} value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={inputCls}
              placeholder="Min 8 characters"
              autoComplete="new-password"
            />
          </div>
          <button
            type="submit" disabled={stage !== null}
            className="w-full rounded-xl bg-[#3ecf8e] px-4 py-2.5 text-sm font-semibold text-black hover:bg-[#2db37a] disabled:opacity-60 transition-colors"
          >
            {stage ? (
              <span className="flex items-center justify-center gap-2">
                <span className="inline-block w-3.5 h-3.5 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                Creating account…
              </span>
            ) : "Create account"}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-zinc-500">
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-[#3ecf8e] hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
