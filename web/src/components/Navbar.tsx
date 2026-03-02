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
    <header className="bg-white shadow-sm">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <Link href="/dashboard" className="flex items-center gap-2 font-bold text-slate-900">
          <Scale size={20} className="text-blue-600" />
          FakeNews Tribunal
        </Link>
        <button
          onClick={handleLogout}
          className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-900 transition-colors"
        >
          <LogOut size={15} />
          Logout
        </button>
      </div>
    </header>
  );
}
