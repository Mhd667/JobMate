"use client";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, ApiError, Card, Conversation, ConversationDetail, Message, post, Turn } from "@/lib/api";
import { supabase } from "@/lib/supabase";
import { useMe } from "@/lib/useMe";
import { Act, CardView } from "@/components/Cards";
import Composer from "@/components/Composer";
import * as I from "@/components/Icons";

const HELLO_SUB = {
  employer: "Votre agence de recrutement IA. Dites-moi qui vous cherchez, et je m'occupe du reste.",
  candidate: "Parlez-moi de vous et de ce que vous cherchez. Je vous préviens ici dès qu'une offre vous correspond.",
};

interface Failure { text: string; retry?: () => void }

export default function Chat() {
  const router = useRouter();
  const { me, error: meError } = useMe();
  const kind = me?.user.role ?? null;
  const [conv, setConv] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<Failure | null>(null);
  const [draft, setDraft] = useState<string | undefined>();
  const [sidebar, setSidebar] = useState(false);
  const [menu, setMenu] = useState(false);
  const scroller = useRef<HTMLDivElement>(null);

  // ------------------------------------------------------------------ loading
  useEffect(() => {
    if (!me) return;
    if (me.next_step !== "employer_home" && me.next_step !== "candidate_home") {
      router.replace("/role");
      return;
    }
    setSidebar(window.matchMedia("(min-width: 861px)").matches);
    (async () => {
      try {
        const list = await api<Conversation[]>("/conversations");
        const latest = list.find((c) => c.kind === me.user.role);
        if (latest) {
          const d = await api<ConversationDetail>(`/conversations/${latest.id}`);
          setConv(d);
          setMessages(d.messages);
        }
      } catch (e) {
        setFailure({ text: e instanceof Error ? e.message : "Erreur de chargement" });
      } finally {
        setLoaded(true);
      }
    })();
  }, [me, router]);

  // Offers and employer decisions arrive in the candidate's chat: refresh it quietly.
  useEffect(() => {
    if (kind !== "candidate" || !conv) return;
    const t = setInterval(async () => {
      if (busy || document.hidden) return;
      try {
        const d = await api<ConversationDetail>(`/conversations/${conv.id}`);
        setMessages((cur) => (d.messages.length !== cur.length ? d.messages : cur));
      } catch { /* next tick */ }
    }, 20000);
    return () => clearInterval(t);
  }, [kind, conv, busy]);

  useEffect(() => {
    const el = scroller.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, busy, failure]);

  const decisions = useMemo(() => {
    const out: Record<string, string> = {};
    for (const m of messages) if (m.meta?.decision) out[m.meta.decision.candidate_id] = m.meta.decision.status;
    return out;
  }, [messages]);

  const showHello = loaded && !messages.some((m) => m.sender === "user" || (m.meta?.cards?.length ?? 0) > 0);

  // ------------------------------------------------------------------ actions
  const ensureConversation = useCallback(async (): Promise<Conversation> => {
    if (conv) return conv;
    const d = await post<ConversationDetail>("/conversations", { kind });
    setConv(d);
    setMessages((cur) => [...d.messages, ...cur.filter((m) => m.id.startsWith("tmp-"))]);
    return d;
  }, [conv, kind]);

  function applyTurn(t: Turn, tempId?: string) {
    setMessages((cur) => [...cur.filter((m) => m.id !== tempId), t.user_message, t.assistant_message]);
  }

  function fail(e: unknown, retry?: () => void) {
    if (e instanceof ApiError && e.status === 401) {
      router.replace("/login");
      return;
    }
    setFailure({ text: e instanceof Error ? e.message : "Erreur", retry });
  }

  async function send(text: string) {
    setFailure(null);
    setBusy(true);
    const tempId = `tmp-${Date.now()}`;
    setMessages((cur) => [...cur, { id: tempId, sender: "user", content: text, meta: {}, created_at: "" }]);
    try {
      const c = await ensureConversation();
      applyTurn(await post<Turn>(`/conversations/${c.id}/messages`, { content: text }), tempId);
    } catch (e) {
      setMessages((cur) => cur.filter((m) => m.id !== tempId));
      setDraft(text);
      fail(e, () => send(text));
    } finally {
      setBusy(false);
    }
  }

  const act: Act = async (card: Card, action: string, payload = {}) => {
    if (!conv) return false;
    setFailure(null);
    setBusy(true);
    try {
      const t = await post<Turn>(`/conversations/${conv.id}/actions`, { card_id: card.id, action, payload });
      // Re-read the thread so the answered card shows its final state.
      const d = await api<ConversationDetail>(`/conversations/${conv.id}`).catch(() => null);
      if (d) setMessages(d.messages);
      else applyTurn(t);
      return true;
    } catch (e) {
      fail(e, () => act(card, action, payload));
      return false;
    } finally {
      setBusy(false);
    }
  };

  async function attachCv(file: File) {
    if (!me?.candidate_id) return;
    setFailure(null);
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      await api("/candidates/me/cv", { method: "POST", body: fd });
      await post(`/candidates/${me.candidate_id}/analyze`, {});
      await send(`J'ai ajouté mon CV (${file.name}).`);
    } catch (e) {
      fail(e);
    } finally {
      setBusy(false);
    }
  }

  function newRecruitment() {
    setConv(null);
    setMessages([]);
    setFailure(null);
    if (!window.matchMedia("(min-width: 861px)").matches) setSidebar(false);
  }

  async function logout() {
    await supabase.auth.signOut();
    router.replace("/login");
  }

  // ------------------------------------------------------------------ render
  if (!me || !loaded) return <main className="center-msg">{meError ?? failure?.text ?? "Chargement…"}</main>;
  const isEmployer = kind === "employer";
  const initial = (me.user.email?.[0] ?? "?").toUpperCase();

  return (
    <div className="app">
      {isEmployer && (
        <>
          <aside className={`sidebar${sidebar ? "" : " collapsed"}`} aria-label="Navigation" aria-hidden={!sidebar}>
            <div className="sidebar-head">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/logo.png" alt="JobMate" />
              <button className="icon-btn" aria-label="Replier la barre latérale" onClick={() => setSidebar(false)}
                      tabIndex={sidebar ? 0 : -1}><I.ChevronLeft /></button>
            </div>
            <button className="new-btn" onClick={newRecruitment} tabIndex={sidebar ? 0 : -1}>
              <I.Plus /> Nouveau recrutement
            </button>
          </aside>
          {sidebar && <div className="scrim" onClick={() => setSidebar(false)} aria-hidden />}
        </>
      )}

      <main className="main">
        <header className="topbar">
          {isEmployer && !sidebar ? (
            <button className="icon-btn" aria-label="Ouvrir la barre latérale" onClick={() => setSidebar(true)}><I.Menu /></button>
          ) : <span style={{ width: 40 }} />}
          <div className="title">
            {(!isEmployer || !sidebar) && (
              // eslint-disable-next-line @next/next/no-img-element
              <img src="/logo.png" alt="JobMate" />
            )}
          </div>
          <div className="menu">
            <button className="avatar" style={{ border: 0 }} aria-haspopup="menu" aria-expanded={menu}
                    aria-label="Mon compte" onClick={() => setMenu(!menu)}>{initial}</button>
            {menu && (
              <div className="menu-pop glass" role="menu">
                <div className="who">{me.user.email}</div>
                <button role="menuitem" onClick={logout}><I.Logout /> Se déconnecter</button>
              </div>
            )}
          </div>
        </header>

        {showHello ? (
          <Hello sub={HELLO_SUB[kind ?? "employer"]} />
        ) : (
          <div className="scroll" ref={scroller} onClick={() => setMenu(false)}>
            <div className="thread" aria-live="polite">
              {messages.map((m) => (
                <MessageView key={m.id} m={m} act={act} busy={busy} decisions={decisions} initial={initial} />
              ))}
              {busy && (
                <div className="row assistant">
                  <BotAvatar />
                  <div className="bubble typing" aria-label="JobMate réfléchit"><i /><i /><i /></div>
                </div>
              )}
              {failure && (
                <div className="error-row">
                  <p className="notice error" role="alert">{failure.text}</p>
                  {failure.retry && <button className="btn" onClick={failure.retry}>Réessayer</button>}
                </div>
              )}
            </div>
          </div>
        )}
        {showHello && failure && (
          <div className="error-row" style={{ justifyContent: "center", margin: "0 16px 8px" }}>
            <p className="notice error" role="alert">{failure.text}</p>
          </div>
        )}

        <Composer
          disabled={busy}
          draft={draft}
          onSend={send}
          placeholder={showHello
            ? (isEmployer ? "Dites-moi votre besoin de recrutement…" : "Présentez-vous en quelques mots…")
            : "Répondez à JobMate…"}
          onAttach={!isEmployer ? attachCv : undefined}
          attachLabel={!isEmployer ? "Ajouter mon CV" : undefined}
        />
      </main>
    </div>
  );
}

function BotAvatar() {
  // eslint-disable-next-line @next/next/no-img-element
  return <span className="bot-avatar" aria-hidden><img src="/mark.png" alt="" /></span>;
}

function MessageView({ m, act, busy, decisions, initial }: {
  m: Message; act: Act; busy: boolean; decisions: Record<string, string>; initial: string;
}) {
  if (m.sender === "user") {
    return (
      <div className="row user">
        <div className={`bubble${m.id.startsWith("tmp-") ? " pending" : ""}`}>{m.content}</div>
        <span className="avatar" aria-hidden>{initial}</span>
      </div>
    );
  }
  const cards = m.meta?.cards ?? [];
  return (
    <>
      <div className="row assistant">
        <BotAvatar />
        <div className="bubble">{m.content}</div>
      </div>
      {cards.length > 0 && (
        <div className="cards">
          {cards.map((c) => <CardView key={c.id} card={c} act={act} busy={busy} decisions={decisions} />)}
        </div>
      )}
    </>
  );
}

/** Centered logo and "Bonjour, je suis JobMate", written progressively ("JobMate" in blue). */
function Hello({ sub }: { sub: string }) {
  const A = "Bonjour, je suis ";
  const B = "JobMate";
  const [n, setN] = useState(0);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setN(A.length + B.length);
      return;
    }
    const t = setInterval(() => setN((x) => (x >= A.length + B.length ? x : x + 1)), 55);
    return () => clearInterval(t);
  }, []);
  const done = n >= A.length + B.length;
  return (
    <section className="hello">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <div className="mark"><img src="/mark.png" alt="" /></div>
      <h1 aria-label={A + B}>
        <span aria-hidden>
          {A.slice(0, n)}
          <span className="brand">{B.slice(0, Math.max(0, n - A.length))}</span>
          {!done && <span className="caret" />}
        </span>
      </h1>
      <p className={done ? "shown" : ""}>{sub}</p>
    </section>
  );
}
