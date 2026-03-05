"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { List, LogOut, Scale, Shield, User, Webhook } from "lucide-react";
import { useAuth } from "@/lib/auth-context";

export default function Navbar() {
  const { logout, user, isAuthenticated } = useAuth();
  const router = useRouter();

  async function handleLogout() {
    await logout();
    router.push("/login");
  }

  return (
    <header className="border-b border-white/10 bg-[#0c0c0c]">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3.5">
        <Link href="/dashboard" className="flex items-center gap-2 font-semibold text-white">
          <Scale size={18} className="text-[#3ecf8e]" />
          FakeNews Tribunal
        </Link>
        <div className="flex items-center gap-4">
          {isAuthenticated && (
            <Link
              href="/batch"
              className="flex items-center gap-1.5 text-sm text-zinc-400 hover:text-white transition-colors"
            >
              <List size={14} />
              Batch
            </Link>
          )}
          {isAuthenticated && (
            <Link
              href="/webhooks"
              className="flex items-center gap-1.5 text-sm text-zinc-400 hover:text-white transition-colors"
            >
              <Webhook size={14} />
              Webhooks
            </Link>
          )}
          {user?.is_admin && (
            <Link
              href="/admin/users"
              className="flex items-center gap-1.5 text-sm text-[#3ecf8e] hover:text-white transition-colors"
            >
              <Shield size={14} />
              Admin
            </Link>
          )}
          {isAuthenticated && (
            <Link
              href="/profile"
              className="flex items-center gap-1.5 text-sm text-zinc-400 hover:text-white transition-colors"
            >
              <User size={14} />
              Profilo
            </Link>
          )}
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 text-sm text-zinc-400 hover:text-white transition-colors"
          >
            <LogOut size={14} />
            Logout
          </button>
        </div>
      </div>
    </header>
  );
}
