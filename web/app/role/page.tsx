"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, Me, Role, routeFor } from "@/lib/api";
import { useMe } from "@/lib/useMe";

const ROLES: { value: Role; title: string; text: string }[] = [
  { value: "employer", title: "Je recrute", text: "Décrivez votre entreprise et vos postes, JobMate vous aide à choisir." },
  { value: "candidate", title: "Je cherche un poste", text: "Construisez votre identité professionnelle et trouvez les bonnes opportunités." },
];

export default function RoleChoice() {
  const router = useRouter();
  const { me } = useMe();
  const [role, setRole] = useState<Role | null>(null);
  const [phone, setPhone] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (me && me.user.role) router.replace(routeFor[me.next_step]);
  }, [me, router]);

  async function confirm() {
    if (!role) return;
    setBusy(true);
    setError(null);
    try {
      const next = await api<Me>("/auth/role", {
        method: "POST",
        body: JSON.stringify({ role, phone_number: phone.trim() || null }),
      });
      router.replace(routeFor[next.next_step]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
      setBusy(false);
    }
  }

  return (
    <main className="shell">
      <div className="card">
        <p className="brand">Job<span>Mate</span></p>
        <h1>Comment veux-tu utiliser JobMate ?</h1>
        <p className="lead">Ce choix détermine ton espace. Il ne pourra pas être changé ensuite.</p>
        <div className="roles" role="group" aria-label="Rôle">
          {ROLES.map((r) => (
            <button key={r.value} type="button" className="role" aria-pressed={role === r.value}
                    onClick={() => setRole(r.value)}>
              <strong>{r.title}</strong>
              <span>{r.text}</span>
            </button>
          ))}
        </div>
        <label htmlFor="phone">Téléphone (facultatif)</label>
        <input id="phone" type="tel" autoComplete="tel" placeholder="+221 …" value={phone}
               onChange={(e) => setPhone(e.target.value)} />
        <button className="primary" disabled={!role || busy} onClick={confirm}>
          {busy ? "…" : "Continuer"}
        </button>
        {error && <p className="error">{error}</p>}
      </div>
    </main>
  );
}
