"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogOut, Scale, Shield, Webhook } from "lucide-react";
import { useAuth } from "@/lib/auth-context";

export default function Navbar() {
  const { logout, user } = useAuth();
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
          <Link
            href="/webhooks"
            className="flex items-center gap-1.5 text-sm text-zinc-400 hover:text-white transition-colors"
          >
            <Webhook size={14} />
            Webhooks
          </Link>
          {user?.is_admin && (
            <Link
              href="/admin/users"
              className="flex items-center gap-1.5 text-sm text-[#3ecf8e] hover:text-white transition-colors"
            >
              <Shield size={14} />
              Admin
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
