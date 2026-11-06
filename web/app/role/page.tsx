"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { landing, Me, post, Role, routeFor } from "@/lib/api";
import { useMe } from "@/lib/useMe";
import { Briefcase, Users } from "@/components/Icons";

/** Fallback when a signed-in account has no role yet (e.g. confirmed by e-mail on another device). */
export default function RoleChoice() {
  const router = useRouter();
  const { me, error } = useMe();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!me) return;
    if (me.next_step === "employer_home" || me.next_step === "candidate_home") router.replace("/home");
    else if (me.user.role) landing().then((to) => router.replace(to)).catch((e) => setErr(e.message));
  }, [me, router]);

  async function choose(role: Role) {
    setBusy(true);
    setErr(null);
    try {
      const m = await post<Me>("/auth/role", { role });
      router.replace(routeFor[m.next_step]);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erreur");
      setBusy(false);
    }
  }

  if (!me) return <main className="center-msg">{error ?? "Chargement…"}</main>;
  return (
    <main className="access">
      <div className="access-card glass">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img className="logo" src="/logo.png" alt="JobMate" />
        <h1>Qui êtes-vous ?</h1>
        <p className="lead">Ce choix oriente votre parcours. Il ne pourra pas être modifié ensuite.</p>
        <div className="roles">
          <button type="button" className="role-tile" disabled={busy} onClick={() => choose("employer")}>
            <span className="ico"><Briefcase /></span><strong>Employeur</strong><span>Je recrute pour mon entreprise</span>
          </button>
          <button type="button" className="role-tile" disabled={busy} onClick={() => choose("candidate")}>
            <span className="ico"><Users /></span><strong>Chercheur d&apos;emploi</strong><span>Je cherche un poste qui me correspond</span>
          </button>
        </div>
        {err && <p className="notice error" role="alert">{err}</p>}
      </div>
    </main>
  );
}
