"use client";

/*
 * NOTE — backend dependency:
 * This page calls PATCH /api/v1/auth/me, which does NOT exist yet in v0.4.
 * Before this page works end-to-end you must add the route in
 * api/routers/auth.py.  Suggested contract:
 *
 *   PATCH /api/v1/auth/me
 *   Body: { email?: str, current_password?: str, new_password?: str }
 *   Returns: { id, email, is_admin, is_disabled }  (same shape as GET /me)
 *
 * Validate that `current_password` is correct before applying any change.
 * If only `email` is provided, no password verification is required (or add it
 * for extra safety — your call).
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Save } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { updateMe } from "@/lib/api";
import Navbar from "@/components/Navbar";

const inputCls =
  "w-full rounded-xl bg-[#111] border border-white/10 px-4 py-2.5 text-sm text-white placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-[#3ecf8e]/50 transition-colors";

const btnCls =
  "flex items-center gap-2 rounded-xl bg-[#3ecf8e] px-5 py-2 text-sm font-semibold text-black hover:bg-[#2db37a] disabled:opacity-50 transition-colors";

export default function ProfilePage() {
  const { isAuthenticated, isLoading, user, refreshUser } = useAuth();
  const router = useRouter();

  // ----- Email form -----
  const [email, setEmail] = useState("");
  const [emailSaving, setEmailSaving] = useState(false);
  const [emailSuccess, setEmailSuccess] = useState("");
  const [emailError, setEmailError] = useState("");

  // ----- Password form -----
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [pwSaving, setPwSaving] = useState(false);
  const [pwSuccess, setPwSuccess] = useState("");
  const [pwError, setPwError] = useState("");

  // Redirect if not authenticated
  useEffect(() => {
    if (!isLoading && !isAuthenticated) router.push("/login");
  }, [isAuthenticated, isLoading, router]);

  // Pre-fill email from current user
  useEffect(() => {
    if (user?.email) setEmail(user.email);
  }, [user]);

  async function handleEmailSubmit(e: React.FormEvent) {
    e.preventDefault();
    setEmailError("");
    setEmailSuccess("");
    if (!email.trim()) { setEmailError("Email cannot be empty"); return; }
    setEmailSaving(true);
    try {
      await updateMe({ email: email.trim() });
      await refreshUser();
      setEmailSuccess("Email updated successfully.");
    } catch (err: unknown) {
      setEmailError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setEmailSaving(false);
    }
  }

  async function handlePasswordSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPwError("");
    setPwSuccess("");
    if (!currentPassword) { setPwError("Enter your current password"); return; }
    if (newPassword.length < 8) { setPwError("New password must be at least 8 characters"); return; }
    if (newPassword !== confirmPassword) { setPwError("Passwords do not match"); return; }
    setPwSaving(true);
    try {
      await updateMe({ current_password: currentPassword, new_password: newPassword });
      setPwSuccess("Password changed successfully.");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err: unknown) {
      setPwError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setPwSaving(false);
    }
  }

  if (isLoading) return null;

  return (
    <div className="min-h-screen bg-[#0c0c0c]">
      <Navbar />
      <main className="mx-auto max-w-xl px-4 py-8 space-y-6">
        <h1 className="text-xl font-semibold text-white">Profile</h1>

        {/* Current account info */}
        <div className="rounded-xl bg-[#1a1a1a] border border-white/10 px-5 py-4 flex items-center gap-3">
          <div className="size-9 rounded-full bg-[#3ecf8e]/20 flex items-center justify-center text-[#3ecf8e] font-semibold text-sm select-none">
            {user?.email?.[0]?.toUpperCase() ?? "?"}
          </div>
          <div>
            <p className="text-sm font-medium text-white">{user?.email}</p>
            <p className="text-xs text-zinc-500 mt-0.5">
              {user?.is_admin ? "Administrator" : "Standard user"}
              {user?.is_disabled && " · disabled"}
            </p>
          </div>
        </div>

        {/* Change email */}
        <section className="rounded-xl bg-[#1a1a1a] border border-white/10 p-6 space-y-4">
          <h2 className="text-base font-semibold text-white">Change email</h2>
          <form onSubmit={handleEmailSubmit} className="space-y-4">
            {emailError && (
              <p className="rounded-xl bg-red-500/10 border border-red-500/20 px-3 py-2 text-sm text-red-400">
                {emailError}
              </p>
            )}
            {emailSuccess && (
              <p className="rounded-xl bg-[#3ecf8e]/10 border border-[#3ecf8e]/20 px-3 py-2 text-sm text-[#3ecf8e]">
                {emailSuccess}
              </p>
            )}
            <div>
              <label className="block text-xs font-medium text-zinc-500 mb-1">New email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className={inputCls}
              />
            </div>
            <button type="submit" disabled={emailSaving} className={btnCls}>
              {emailSaving ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />}
              {emailSaving ? "Saving…" : "Save email"}
            </button>
          </form>
        </section>

        {/* Change password */}
        <section className="rounded-xl bg-[#1a1a1a] border border-white/10 p-6 space-y-4">
          <h2 className="text-base font-semibold text-white">Change password</h2>
          <form onSubmit={handlePasswordSubmit} className="space-y-4">
            {pwError && (
              <p className="rounded-xl bg-red-500/10 border border-red-500/20 px-3 py-2 text-sm text-red-400">
                {pwError}
              </p>
            )}
            {pwSuccess && (
              <p className="rounded-xl bg-[#3ecf8e]/10 border border-[#3ecf8e]/20 px-3 py-2 text-sm text-[#3ecf8e]">
                {pwSuccess}
              </p>
            )}
            <div>
              <label className="block text-xs font-medium text-zinc-500 mb-1">Current password</label>
              <input
                type="password"
                required
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="••••••••"
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-zinc-500 mb-1">New password</label>
              <input
                type="password"
                required
                minLength={8}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="••••••••"
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-zinc-500 mb-1">Confirm new password</label>
              <input
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                className={inputCls}
              />
            </div>
            <button type="submit" disabled={pwSaving} className={btnCls}>
              {pwSaving ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />}
              {pwSaving ? "Saving…" : "Change password"}
            </button>
          </form>
        </section>
      </main>
    </div>
  );
}
