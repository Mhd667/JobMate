"use client";
import { ReactNode, useRef, useState } from "react";
import { api, Card } from "@/lib/api";
import * as I from "./Icons";

export type Act = (card: Card, action: string, payload?: Record<string, unknown>) => Promise<boolean>;
interface Props { card: Card; act: Act; busy: boolean; decisions: Record<string, string> }

const STATUS_FR: Record<string, string> = { passed: "Écarté", interview: "Entretien demandé", hired: "Retenu" };

function Unknown({ children = "À préciser" }: { children?: string }) {
  return <span className="unknown">{children}</span>;
}

function Done({ text }: { text: string }) {
  return <p className="done-note"><I.Check /> {text}</p>;
}

export function CardView(p: Props) {
  switch (p.card.type) {
    case "missions": return <Missions {...p} />;
    case "role_summary": return <RoleSummary {...p} />;
    case "success_model": return <SuccessModel {...p} />;
    case "candidates": return <Candidates {...p} />;
    case "next_steps": return <NextSteps {...p} />;
    case "confrontation": return <Confrontation {...p} />;
    case "recommendation": return <Recommendation {...p} />;
    case "sources": return <Sources {...p} />;
    case "offer": return <Offer {...p} />;
    case "assessment": return <Assessment {...p} />;
    default: return null;
  }
}

// ------------------------------------------------------------------ employer
function Missions({ card, act, busy }: Props) {
  const done = card.status === "done";
  const chosen = (card.result?.selected as string[] | undefined) ?? [];
  const [sel, setSel] = useState<string[]>(chosen);
  const [other, setOther] = useState("");
  const options: string[] = card.data.options ?? [];
  const toggle = (o: string) => setSel((s) => (s.includes(o) ? s.filter((x) => x !== o) : [...s, o]));
  return (
    <section className="card" aria-label="Missions du poste">
      <div className="card-head">
        <span className="card-ico"><I.Phone /></span>
        <div>
          <h3>{card.data.question}</h3>
          <p className="sub">Sélectionnez tout ce qui s&apos;applique.</p>
        </div>
      </div>
      <div className="options">
        {[...options, ...chosen.filter((c) => !options.includes(c))].map((o) => {
          const on = done ? chosen.includes(o) : sel.includes(o);
          return (
            <label key={o} className={`option${on ? " on" : ""}`}>
              <input type="checkbox" checked={on} disabled={done || busy} onChange={() => toggle(o)} />
              {o}
            </label>
          );
        })}
        {!done && card.data.allow_other && (
          <input className="input" placeholder="Autre mission (facultatif)" value={other} disabled={busy}
                 aria-label="Autre mission" onChange={(e) => setOther(e.target.value)} />
        )}
      </div>
      {!done && (
        <div className="card-actions">
          <button className="btn primary" disabled={busy || (!sel.length && !other.trim())}
                  onClick={() => act(card, "missions.submit", { selected: sel, other: other.trim() || undefined })}>
            Continuer
          </button>
        </div>
      )}
    </section>
  );
}

function RoleSummary({ card, act, busy }: Props) {
  const d = card.data;
  const [searching, setSearching] = useState(false);
  const join = (xs: string[]) => (xs?.length ? xs.join(" · ") : null);
  const result = card.result?.action as string | undefined;
  return (
    <>
      <section className="card" aria-label="Synthèse du poste">
        <div className="card-head">
          <span className="card-ico"><I.Briefcase /></span>
          <div>
            <h3>{d.title}</h3>
            {d.contract && <div style={{ marginTop: 6 }}><span className="badge">{d.contract}</span></div>}
          </div>
        </div>
        <dl className="rows" style={{ margin: 0 }}>
          <div className="kv"><dt><I.Target />Missions</dt><dd>{join(d.missions) ?? <Unknown />}</dd></div>
          <div className="kv"><dt><I.Languages />Langues</dt><dd>{join(d.languages) ?? <Unknown />}</dd></div>
          <div className="kv"><dt><I.Star />Critères clés</dt>
            <dd>{d.criteria?.length ? <div className="chips">{d.criteria.map((c: string) => <span key={c} className="chip">{c}</span>)}</div> : <Unknown />}</dd></div>
          <div className="kv"><dt><I.Calendar />Disponibilité</dt><dd>{d.availability ?? <Unknown />}</dd></div>
          <div className="kv"><dt><I.Bolt />Priorité</dt><dd>{d.priority ? <span className="badge">{d.priority}</span> : <Unknown />}</dd></div>
        </dl>
        {card.status === "open" && !searching && (
          <div className="card-actions">
            <button className="btn" disabled={busy} onClick={() => act(card, "role_summary.edit")}>Modifier</button>
            <button className="btn primary" disabled={busy} onClick={async () => {
              setSearching(true);
              await act(card, "role_summary.confirm");
              setSearching(false);
            }}>Lancer la recherche</button>
          </div>
        )}
        {card.status === "open" && !searching && (
          <p className="sub" style={{ marginTop: 10 }}>Vous pouvez aussi corriger la synthèse en me répondant dans le chat.</p>
        )}
        {result === "role_summary.confirm" && <Done text="Synthèse validée" />}
        {result === "role_summary.edit" && <Done text="Modification demandée" />}
      </section>
      {searching && (
        <div className="loading-pill" role="status"><span className="spinner" aria-hidden /> Recherche des meilleurs profils…</div>
      )}
    </>
  );
}

function SuccessModel({ card }: Props) {
  const caps: { key: string; name: string; importance: string }[] = card.data.capabilities ?? [];
  return (
    <section className="card" aria-label="Ce qui fera réussir">
      <div className="panel-title"><I.Sparkle /><h3>Ce qui fera réussir dans ce poste</h3></div>
      <div className="chips">
        {caps.map((c) => <span key={c.key} className="chip">{c.name} <span style={{ color: "var(--text-2)" }}>· {c.importance}</span></span>)}
      </div>
    </section>
  );
}

function Candidates({ card, act, busy, decisions }: Props) {
  const list: CandidateData[] = card.data.candidates ?? [];
  const [open, setOpen] = useState<string | null>(null);
  if (!list.length) return null;
  return (
    <div className="cand-list">
      {list.map((c) => (
        <CandidateCard key={c.candidate_id} c={c} open={open === c.candidate_id} busy={busy}
                       status={decisions[c.candidate_id] ?? c.employer_status}
                       toggle={() => setOpen(open === c.candidate_id ? null : c.candidate_id)}
                       decide={(a) => act(card, a, { candidate_id: c.candidate_id })} />
      ))}
    </div>
  );
}

interface CandidateData {
  candidate_id: string; name: string; initials: string; headline: string | null; city: string | null;
  years_experience: number | null; match_score: number | null; why: string | null; skills: string[];
  employer_status: string | null;
}

function CandidateCard({ c, open, toggle, decide, busy, status }: {
  c: CandidateData; open: boolean; toggle: () => void; decide: (a: string) => void; busy: boolean; status?: string | null;
}) {
  const id = `cand-${c.candidate_id}`;
  return (
    <article className={`card cand${open ? " open" : ""}`}>
      <button className="cand-top" aria-expanded={open} aria-controls={id} onClick={toggle}>
        <span className="portrait" aria-hidden>{c.initials}</span>
        <span className="cand-main">
          <span className="cand-name">
            <strong>{c.name}</strong>
            {c.match_score != null && <span className="badge green"><I.Sparkle />Match {c.match_score}%</span>}
          </span>
          {c.headline && <span className="cand-role" style={{ display: "block" }}>{c.headline}</span>}
          <span className="meta">
            {c.years_experience != null && <span><I.Briefcase />{c.years_experience} an{c.years_experience > 1 ? "s" : ""} d&apos;exp.</span>}
            {c.city && <span><I.Pin />{c.city}</span>}
            {status && <span className="badge grey">{STATUS_FR[status] ?? status}</span>}
          </span>
        </span>
        <span className="chev" aria-hidden><I.Chevron /></span>
        <span className="sr-only">{open ? "Replier" : "Voir le détail"}</span>
      </button>
      <div className="cand-body" id={id}>
        <div>
          {c.why && (
            <div className="why"><I.Sparkle />
              <div><strong>Pourquoi ce profil correspond ?</strong><p>{c.why}</p></div>
            </div>
          )}
          {!!c.skills?.length && <div className="chips">{c.skills.map((s) => <span key={s} className="chip">{s}</span>)}</div>}
          <div className="decide">
            <button className="btn pass" disabled={busy} tabIndex={open ? 0 : -1} onClick={() => decide("candidate.pass")}><I.X />Passer</button>
            <button className="btn meet" disabled={busy} tabIndex={open ? 0 : -1} onClick={() => decide("candidate.interview")}><I.Calendar />Entretien</button>
            <button className="btn primary" disabled={busy} tabIndex={open ? 0 : -1} onClick={() => decide("candidate.hire")}><I.Check />Hire</button>
          </div>
        </div>
      </div>
    </article>
  );
}

const NEXT_ICONS: Record<string, ReactNode> = {
  "next.hire": <I.FileUser />, "next.interviews": <I.Calendar />, "next.refine": <I.Sliders />,
};

function NextSteps({ card, act, busy }: Props) {
  return (
    <section className="card" aria-label="Étapes suivantes">
      <div className="panel-title"><I.Sparkle /><h3>{card.data.question}</h3></div>
      <div className="next-list">
        {card.actions.map((a) => (
          <button key={a.id} className="next-item" disabled={busy} onClick={() => act(card, a.id)}>
            {NEXT_ICONS[a.id]}<span className="lbl">{a.label}</span><I.Arrow />
          </button>
        ))}
      </div>
    </section>
  );
}

function List({ title, items }: { title: string; items?: string[] }) {
  if (!items?.length) return null;
  return <div className="block"><h4>{title}</h4><ul>{items.map((x, i) => <li key={i}>{x}</li>)}</ul></div>;
}

function stripName(text: string, name?: string): string {
  if (!name || !text) return text;
  return text.replace(new RegExp(`^${name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\s*[:—-]\\s*`), "");
}

function Confrontation({ card, act, busy }: Props) {
  const d = card.data;
  const tradeoffs: { if_priority: string; prefer_candidate_id: string; explanation: string }[] = d.tradeoffs ?? [];
  const names: Record<string, string> = Object.fromEntries((d.profiles ?? []).map((p: { candidate_id: string; name: string }) => [p.candidate_id, p.name]));
  return (
    <section className="card" aria-label="Confrontation des finalistes">
      <div className="card-head">
        <span className="card-ico"><I.Scale /></span>
        <div><h3>Confrontation des finalistes</h3><p className="sub">{d.question}</p></div>
      </div>
      <div className="block"><h4>Profils</h4>
        <ul>{(d.profiles ?? []).map((p: { candidate_id: string; name: string; headline: string }) => (
          <li key={p.candidate_id}><strong>{p.name}</strong> : {stripName(p.headline, p.name)}</li>))}</ul>
      </div>
      {!!tradeoffs.length && (
        <div className="block"><h4>Arbitrages</h4>
          <ul>{tradeoffs.map((t, i) => (
            <li key={i}>{t.explanation || `Priorité « ${t.if_priority} » : ${names[t.prefer_candidate_id] ?? "?"}`}</li>))}</ul>
        </div>
      )}
      {d.reasoning && <div className="block"><h4>Raisonnement</h4><p>{d.reasoning}</p></div>}
      <List title="Incertitudes" items={d.uncertainties} />
      {card.actions.length > 0 && (
        <div className="card-actions">
          <button className="btn primary" disabled={busy} onClick={() => act(card, "recommend")}>Obtenir une recommandation</button>
        </div>
      )}
    </section>
  );
}

function Recommendation({ card, act, busy, decisions }: Props) {
  const d = card.data;
  const status = d.candidate_id ? decisions[d.candidate_id] : undefined;
  return (
    <section className="card" aria-label="Recommandation">
      <div className="card-head">
        <span className="card-ico"><I.Sparkle /></span>
        <div>
          <h3>{d.name ? `Recommandation : ${d.name}` : "Pas de recommandation tranchée"}</h3>
          {d.confidence != null && <p className="sub">Confiance : {Math.round(d.confidence * 100)} %. La décision vous revient.</p>}
        </div>
      </div>
      <p style={{ margin: 0 }}>{d.summary}</p>
      <List title="Preuves clés" items={d.key_evidence} />
      <List title="Arbitrages" items={d.tradeoffs} />
      <List title="Incertitudes" items={d.uncertainties} />
      <List title="Prochaines étapes" items={d.next_steps} />
      {status && <div className="status"><span className="badge grey">{STATUS_FR[status] ?? status}</span></div>}
      {d.candidate_id && (
        <div className="card-actions">
          <button className="btn soft" disabled={busy} onClick={() => act(card, "candidate.interview", { candidate_id: d.candidate_id })}>Entretien</button>
          <button className="btn primary" disabled={busy} onClick={() => act(card, "candidate.hire", { candidate_id: d.candidate_id })}>Hire</button>
        </div>
      )}
    </section>
  );
}

// ------------------------------------------------------------------ candidate
function Sources({ card, act, busy }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [linkedin, setLinkedin] = useState("");
  const [portfolio, setPortfolio] = useState("");
  const [xProfile, setXProfile] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const done = card.status === "done";

  async function submit() {
    setErr(null);
    setSaving(true);
    try {
      if (file) {
        const fd = new FormData();
        fd.append("file", file);
        await api("/candidates/me/cv", { method: "POST", body: fd });
      }
      for (const [kind, url] of [["linkedin", linkedin], ["portfolio", portfolio], ["x", xProfile]] as const) {
        if (url.trim()) {
          const u = /^https?:\/\//.test(url.trim()) ? url.trim() : `https://${url.trim()}`;
          await api("/candidates/me/sources", { method: "POST", body: JSON.stringify({ kind, url: u }) });
        }
      }
      await act(card, "sources.submit");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erreur");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="card" aria-label="Compléter mon profil">
      <div className="card-head">
        <span className="card-ico"><I.FileUser /></span>
        <div><h3>Compléter mon profil</h3><p className="sub">{card.data.question}</p></div>
      </div>
      {done ? (
        <Done text={card.result?.action === "sources.skip" ? "Vous pourrez les ajouter plus tard" : "Informations ajoutées"} />
      ) : (
        <>
          <div className="field">
            <span style={{ fontSize: 13.5, fontWeight: 500 }}>CV (PDF, DOCX ou TXT)</span>
            <label className="file-pick">
              <I.Upload />{file ? file.name : "Choisir un fichier"}
              <input ref={fileRef} type="file" className="sr-only" accept=".pdf,.docx,.txt"
                     onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
            </label>
          </div>
          <div className="field">
            <label htmlFor={`li-${card.id}`}>Profil LinkedIn</label>
            <input id={`li-${card.id}`} className="input" type="url" inputMode="url" placeholder="linkedin.com/in/…"
                   value={linkedin} onChange={(e) => setLinkedin(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor={`pf-${card.id}`}>Portfolio</label>
            <input id={`pf-${card.id}`} className="input" type="url" inputMode="url" placeholder="https://…"
                   value={portfolio} onChange={(e) => setPortfolio(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor={`x-${card.id}`}>Profil X (Twitter)</label>
            <input id={`x-${card.id}`} className="input" type="url" inputMode="url" placeholder="x.com/…"
                   value={xProfile} onChange={(e) => setXProfile(e.target.value)} />
          </div>
          {err && <p className="notice error" role="alert">{err}</p>}
          <div className="card-actions">
            <button className="btn" disabled={busy || saving} onClick={() => act(card, "sources.skip")}>Plus tard</button>
            <button className="btn primary" disabled={busy || saving || (!file && !linkedin.trim() && !portfolio.trim() && !xProfile.trim())}
                    onClick={submit}>{saving ? "Envoi…" : "Ajouter"}</button>
          </div>
        </>
      )}
    </section>
  );
}

function Offer({ card, act, busy }: Props) {
  const d = card.data;
  const contract = [d.contract, d.duration].filter(Boolean).join(" · ");
  const result = card.result?.action as string | undefined;
  return (
    <section className="card" aria-label="Offre" id={`offer-${d.match_id}`}>
      <div className="card-head">
        <span className="card-ico"><I.Briefcase /></span>
        <div style={{ flex: 1 }}>
          <div className="cand-name">
            <h3>{d.title}</h3>
            {d.match_score != null && <span className="badge green"><I.Sparkle />Match {d.match_score}%</span>}
          </div>
          <p className="sub">{d.company}</p>
        </div>
      </div>
      <div className="meta" style={{ marginTop: 0 }}>
        {contract && <span><I.Calendar />{contract}</span>}
        {d.location && <span><I.Pin />{d.location}</span>}
      </div>
      {!!d.missions?.length && <div className="block"><h4>Missions</h4><div className="chips">{d.missions.map((m: string) => <span key={m} className="chip">{m}</span>)}</div></div>}
      {d.explanation && (
        <div className="why"><I.Sparkle /><div><strong>Pourquoi cette offre pour vous ?</strong><p>{d.explanation}</p></div></div>
      )}
      {card.status === "open" ? (
        <div className="card-actions">
          <button className="btn" disabled={busy} onClick={() => act(card, "offer.decline")}>Pas disponible</button>
          <button className="btn primary" disabled={busy} onClick={() => act(card, "offer.interested")}>Ça m&apos;intéresse</button>
        </div>
      ) : (
        <Done text={result === "offer.interested" ? "Vous êtes intéressé(e)" : "Vous avez décliné cette offre"} />
      )}
    </section>
  );
}

function Assessment({ card }: Props) {
  const d = card.data;
  return (
    <section className="card" aria-label="Évaluation">
      <div className="card-head" style={{ marginBottom: 10 }}>
        <span className="card-ico"><I.Target /></span>
        <div>
          <span className="badge">Question {d.index}/{d.total} · {d.theme}</span>
        </div>
      </div>
      <p className="question">{d.question}</p>
      <p className="sub" style={{ marginTop: 10 }}>Répondez dans le chat, avec vos mots.</p>
    </section>
  );
}
