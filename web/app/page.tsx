"use client";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { routeFor } from "@/lib/api";
import { useMe } from "@/lib/useMe";

export default function Index() {
  const router = useRouter();
  const { me, error } = useMe();
  useEffect(() => {
    if (me) router.replace(routeFor[me.next_step]);
  }, [me, router]);
  return (
    <main className="shell">
      <p className="muted">{error ?? "Chargement…"}</p>
    </main>
  );
}
