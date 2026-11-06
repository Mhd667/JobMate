"use client";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { landing, Role, savePendingRole } from "@/lib/api";
import { supabase } from "@/lib/supabase";
import { Briefcase, Users } from "@/components/Icons";

export default function Access() {
  const router = useRouter();
  const [role, setRole] = useState<Role | null>(null);
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) landing().then((to) => router.replace(to)).catch(() => undefined);
    });
  }, [router]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!role) {
      setError("Choisissez d'abord votre profil : Employeur ou Chercheur d'emploi.");
      return;
    }
    setBusy(true);
    setError(null);
    setInfo(null);
    try {
      savePendingRole({ role, full_name: fullName.trim() || undefined, phone_number: phone.trim() || undefined });
      if (mode === "login") {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
      } else {
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
          options: { emailRedirectTo: `${window.location.origin}/`, data: { jobmate_role: role } },
        });
        if (error) throw error;
        if (!data.session) {
          setInfo("Compte créé. Confirmez votre adresse grâce à l'e-mail reçu, puis connectez-vous ici.");
          setMode("login");
          return;
        }
      }
      router.replace(await landing());
    } catch (err) {
      setError(translate(err instanceof Error ? err.message : String(err)));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="access">
      <form className="access-card glass" onSubmit={submit} noValidate={false}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img className="logo" src="/logo.png" alt="JobMate" />
        <h1>Bienvenue</h1>
        <p className="lead">Qui êtes-vous ?</p>

        <div className="roles" role="group" aria-label="Votre profil">
          <button type="button" className="role-tile" aria-pressed={role === "employer"} onClick={() => setRole("employer")}>
            <span className="ico"><Briefcase /></span>
            <strong>Employeur</strong>
            <span>Je recrute pour mon entreprise</span>
          </button>
          <button type="button" className="role-tile" aria-pressed={role === "candidate"} onClick={() => setRole("candidate")}>
            <span className="ico"><Users /></span>
            <strong>Chercheur d&apos;emploi</strong>
            <span>Je cherche un poste qui me correspond</span>
          </button>
        </div>

        {role && (
          <>
            <div className="tabs" role="tablist" aria-label="Connexion ou inscription">
              <button type="button" role="tab" aria-selected={mode === "login"} onClick={() => setMode("login")}>Se connecter</button>
              <button type="button" role="tab" aria-selected={mode === "signup"} onClick={() => setMode("signup")}>Créer un compte</button>
            </div>

            {mode === "signup" && role === "candidate" && (
              <div className="field">
                <label htmlFor="name">Nom complet</label>
                <input id="name" className="input" autoComplete="name" required value={fullName}
                       onChange={(e) => setFullName(e.target.value)} />
                <span className="hint">C&apos;est le nom que verront les recruteurs.</span>
              </div>
            )}
            <div className="field">
              <label htmlFor="email">Adresse e-mail</label>
              <input id="email" className="input" type="email" autoComplete="email" required value={email}
                     onChange={(e) => setEmail(e.target.value)} />
            </div>
            {mode === "signup" && (
              <div className="field">
                <label htmlFor="phone">Téléphone <span className="hint">(facultatif)</span></label>
                <input id="phone" className="input" type="tel" autoComplete="tel" placeholder="+221 …" value={phone}
                       onChange={(e) => setPhone(e.target.value)} />
              </div>
            )}
            <div className="field">
              <label htmlFor="password">Mot de passe</label>
              <input id="password" className="input" type="password" required minLength={8}
                     autoComplete={mode === "login" ? "current-password" : "new-password"}
                     value={password} onChange={(e) => setPassword(e.target.value)} />
              {mode === "signup" && <span className="hint">8 caractères minimum.</span>}
            </div>
            <button className="btn primary block" disabled={busy}>
              {busy ? "Un instant…" : mode === "login" ? "Se connecter" : "Créer mon compte"}
            </button>
          </>
        )}
        {error && <p className="notice error" role="alert">{error}</p>}
        {info && <p className="notice info" role="status">{info}</p>}
      </form>
    </main>
  );
}

function translate(msg: string): string {
  if (/invalid login credentials/i.test(msg)) return "E-mail ou mot de passe incorrect.";
  if (/email not confirmed/i.test(msg)) return "Adresse e-mail pas encore confirmée : vérifiez votre boîte mail.";
  if (/already registered/i.test(msg)) return "Un compte existe déjà avec cette adresse. Connectez-vous.";
  if (/password should be at least/i.test(msg)) return "Le mot de passe est trop court (8 caractères minimum).";
  if (/rate limit/i.test(msg)) return "Trop de tentatives. Patientez quelques minutes.";
  return msg;
}
