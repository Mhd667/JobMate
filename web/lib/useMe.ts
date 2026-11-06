"use client";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { api, ApiError, Me } from "./api";
import { supabase } from "./supabase";

/** Loads /auth/me; sends the visitor to /login when there is no session. */
export function useMe() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    const { data } = await supabase.auth.getSession();
    if (!data.session) {
      router.replace("/login");
      return null;
    }
    try {
      const m = await api<Me>("/auth/me");
      setMe(m);
      return m;
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) router.replace("/login");
      else setError(e instanceof Error ? e.message : "Erreur inconnue");
      return null;
    }
  }, [router]);

  useEffect(() => {
    reload();
  }, [reload]);

  return { me, error, reload };
}
