"use client";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { api, routeFor } from "@/lib/api";
import { useMe } from "@/lib/useMe";

export default function Onboarding() {
  const router = useRouter();
  const { me } = useMe();
  const [form, setForm] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (me && me.next_step !== "create_company" && me.next_step !== "create_profile") {
      router.replace(routeFor[me.next_step]);
    }
  }, [me, router]);

  if (!me) return <main className="shell"><p className="muted">Chargement…</p></main>;
  const employer = me.user.role === "employer";
  const set = (k: string) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value });

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const v = (k: string) => form[k]?.trim() || null;
    try {
      if (employer) {
        await api("/companies", { method: "POST", body: JSON.stringify({
          name: v("name"), city: v("city"), country: v("country"), website: v("website"), description: v("description"),
        }) });
      } else {
        await api("/candidates", { method: "POST", body: JSON.stringify({
          full_name: v("full_name"), headline: v("headline"), location: v("location"),
          availability: v("available_from") ? { available_from: v("available_from") } : {},
        }) });
      }
      router.replace("/home");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
      setBusy(false);
    }
  }

  return (
    <main className="shell">
      <form className="card" onSubmit={submit}>
        <p className="brand">Job<span>Mate</span></p>
        <h1>{employer ? "Ton entreprise" : "Ton profil"}</h1>
        <p className="lead">
          {employer
            ? "L'essentiel suffit : JobMate comprendra le reste en discutant avec toi."
            : "Juste de quoi commencer : ton identité professionnelle se construira en conversation."}
        </p>
        {employer ? (
          <>
            <label htmlFor="name">Nom de l'entreprise</label>
            <input id="name" required onChange={set("name")} />
            <label htmlFor="city">Ville</label>
            <input id="city" onChange={set("city")} />
            <label htmlFor="country">Pays</label>
            <input id="country" onChange={set("country")} />
            <label htmlFor="website">Site web</label>
            <input id="website" type="url" placeholder="https://" onChange={set("website")} />
            <label htmlFor="description">En une phrase, que fait l'entreprise ?</label>
            <textarea id="description" rows={3} onChange={set("description")} />
          </>
        ) : (
          <>
            <label htmlFor="full_name">Nom complet</label>
            <input id="full_name" required autoComplete="name" onChange={set("full_name")} />
            <label htmlFor="headline">Ce que tu fais aujourd'hui</label>
            <input id="headline" placeholder="Ex. commerciale terrain B2B" onChange={set("headline")} />
            <label htmlFor="location">Ville</label>
            <input id="location" onChange={set("location")} />
            <label htmlFor="available_from">Disponible à partir du</label>
            <input id="available_from" type="date" onChange={set("available_from")} />
          </>
        )}
        <button className="primary" disabled={busy}>{busy ? "…" : "Continuer"}</button>
        {error && <p className="error">{error}</p>}
      </form>
    </main>
  );
}
