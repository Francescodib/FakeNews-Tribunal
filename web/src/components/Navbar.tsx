"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogOut, Scale } from "lucide-react";
import { useAuth } from "@/lib/auth-context";

export default function Navbar() {
  const { logout } = useAuth();
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
        <button
          onClick={handleLogout}
          className="flex items-center gap-1.5 text-sm text-zinc-400 hover:text-white transition-colors"
        >
          <LogOut size={14} />
          Logout
        </button>
      </div>
    </header>
  );
}
