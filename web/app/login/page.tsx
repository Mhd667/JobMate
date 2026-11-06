"use client";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { api, Me, routeFor } from "@/lib/api";
import { supabase } from "@/lib/supabase";

export default function Login() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  async function goNext() {
    const me = await api<Me>("/auth/me");
    router.replace(routeFor[me.next_step]);
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setInfo(null);
    try {
      if (mode === "login") {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        await goNext();
      } else {
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
          options: { emailRedirectTo: `${window.location.origin}/` },
        });
        if (error) throw error;
        if (data.session) await goNext();
        else setInfo("Compte créé. Confirme ton adresse via l'e-mail reçu, puis connecte-toi.");
      }
    } catch (err) {
      setError(translate(err instanceof Error ? err.message : String(err)));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="shell">
      <form className="card" onSubmit={submit}>
        <p className="brand">Job<span>Mate</span></p>
        <h1>{mode === "login" ? "Connexion" : "Créer un compte"}</h1>
        <p className="lead">
          {mode === "login"
            ? "Content de te revoir."
            : "Recruteur ou candidat : tu choisiras ton rôle à l'étape suivante."}
        </p>
        <label htmlFor="email">Adresse e-mail</label>
        <input id="email" type="email" autoComplete="email" required value={email}
               onChange={(e) => setEmail(e.target.value)} />
        <label htmlFor="password">Mot de passe</label>
        <input id="password" type="password" required minLength={8}
               autoComplete={mode === "login" ? "current-password" : "new-password"}
               value={password} onChange={(e) => setPassword(e.target.value)} />
        <button className="primary" disabled={busy}>
          {busy ? "…" : mode === "login" ? "Se connecter" : "Créer mon compte"}
        </button>
        {error && <p className="error">{error}</p>}
        {info && <p className="info">{info}</p>}
        <p className="switch">
          {mode === "login" ? "Pas encore de compte ? " : "Déjà un compte ? "}
          <button type="button" className="link" onClick={() => setMode(mode === "login" ? "signup" : "login")}>
            {mode === "login" ? "S'inscrire" : "Se connecter"}
          </button>
        </p>
      </form>
    </main>
  );
}

function translate(msg: string): string {
  if (/invalid login credentials/i.test(msg)) return "E-mail ou mot de passe incorrect.";
  if (/email not confirmed/i.test(msg)) return "Adresse e-mail pas encore confirmée : vérifie ta boîte mail.";
  if (/already registered/i.test(msg)) return "Un compte existe déjà avec cette adresse.";
  if (/password should be at least/i.test(msg)) return "Le mot de passe est trop court.";
  return msg;
}
