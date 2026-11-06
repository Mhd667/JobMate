"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { landing } from "@/lib/api";
import { supabase } from "@/lib/supabase";

export default function Index() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (!data.session) router.replace("/login");
      else landing().then((to) => router.replace(to)).catch((e) => setError(e.message));
    });
  }, [router]);
  return <main className="center-msg">{error ?? "Chargement…"}</main>;
}
