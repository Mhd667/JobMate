"use client";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { routeFor } from "@/lib/api";
import { supabase } from "@/lib/supabase";
import { useMe } from "@/lib/useMe";

export default function Home() {
  const router = useRouter();
  const { me, error } = useMe();

  useEffect(() => {
    if (me && me.next_step !== "employer_home" && me.next_step !== "candidate_home") {
      router.replace(routeFor[me.next_step]);
    }
  }, [me, router]);

  async function logout() {
    await supabase.auth.signOut();
    router.replace("/login");
  }

  if (!me) return <main className="shell"><p className="muted">{error ?? "Chargement…"}</p></main>;
  const employer = me.user.role === "employer";
  return (
    <main className="shell">
      <div className="card wide">
        <div className="row">
          <p className="brand">Job<span>Mate</span></p>
          <button className="link" onClick={logout}>Se déconnecter</button>
        </div>
        <h1>{employer ? "Espace recruteur" : "Espace candidat"}</h1>
        <p className="lead">Connecté en tant que {me.user.email}.</p>
        <p className="muted">
          {employer
            ? "Prochaine étape : décrire un poste en conversation avec JobMate."
            : "Prochaine étape : construire ton identité professionnelle en conversation avec JobMate."}
        </p>
      </div>
    </main>
  );
}
