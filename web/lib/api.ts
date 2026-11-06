import { supabase } from "./supabase";

const API = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");

export type Role = "employer" | "candidate";
export type NextStep = "choose_role" | "create_company" | "employer_home" | "create_profile" | "candidate_home";
export interface Me {
  user: { id: string; email: string; phone_number: string | null; role: Role | null; created_at: string };
  company_id: string | null;
  candidate_id: string | null;
  next_step: NextStep;
}

export interface CardAction { id: string; label: string; style: "primary" | "secondary" | string }
export interface Card {
  id: string;
  type: "missions" | "role_summary" | "success_model" | "candidates" | "next_steps" | "confrontation"
    | "recommendation" | "sources" | "offer" | "assessment";
  status: "open" | "done";
  data: any; // eslint-disable-line @typescript-eslint/no-explicit-any
  actions: CardAction[];
  result?: Record<string, unknown> | null;
}
export interface Message {
  id: string;
  sender: "user" | "assistant" | string;
  content: string;
  meta: { cards?: Card[]; intent?: string; decision?: { candidate_id: string; status: string } } & Record<string, unknown>;
  created_at: string;
}
export interface Conversation {
  id: string;
  kind: Role;
  title: string | null;
  role_id: string | null;
  candidate_id: string | null;
  state: { flow?: string } & Record<string, unknown>;
  created_at: string;
}
export interface ConversationDetail extends Conversation { messages: Message[] }
export interface Turn {
  user_message: Message;
  assistant_message: Message;
  intent: string;
  cards: Card[];
  flow_state: string | null;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function token(): Promise<string> {
  const { data } = await supabase.auth.getSession();
  const t = data.session?.access_token;
  if (!t) throw new ApiError(401, "Session expirée");
  return t;
}

function explain(status: number, detail: unknown): string {
  if (status === 503) return "JobMate est momentanément indisponible (le service d'IA ne répond pas). Réessayez dans un instant.";
  if (status === 502) return "JobMate n'a pas réussi à formuler une réponse fiable. Réessayez.";
  if (typeof detail === "string") return detail;
  return `Erreur ${status}`;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const isForm = init.body instanceof FormData;
  let res: Response;
  try {
    res = await fetch(`${API}${path}`, {
      ...init,
      headers: {
        ...(isForm ? {} : { "Content-Type": "application/json" }),
        Authorization: `Bearer ${await token()}`,
        ...(init.headers ?? {}),
      },
    });
  } catch (e) {
    if (e instanceof ApiError) throw e;
    throw new ApiError(0, "Impossible de joindre le serveur JobMate. Vérifiez votre connexion.");
  }
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(res.status, explain(res.status, body.detail));
  return body as T;
}

export const post = <T,>(path: string, body: unknown) => api<T>(path, { method: "POST", body: JSON.stringify(body) });

export const routeFor: Record<NextStep, string> = {
  choose_role: "/role",
  create_company: "/role",
  create_profile: "/role",
  employer_home: "/home",
  candidate_home: "/home",
};

/** Role chosen on the access screen before the account exists (applied after the first sign-in). */
const PENDING = "jobmate.pending_role";
export interface PendingRole { role: Role; full_name?: string; phone_number?: string }
export function savePendingRole(p: PendingRole) {
  try { localStorage.setItem(PENDING, JSON.stringify(p)); } catch { /* private mode */ }
}
export function takePendingRole(): PendingRole | null {
  try {
    const raw = localStorage.getItem(PENDING);
    localStorage.removeItem(PENDING);
    return raw ? (JSON.parse(raw) as PendingRole) : null;
  } catch {
    return null;
  }
}

/** After sign-in: apply the pending role if needed and return where to go. */
export async function landing(): Promise<string> {
  let me = await api<Me>("/auth/me");
  if (me.next_step !== "employer_home" && me.next_step !== "candidate_home") {
    const pending = takePendingRole();
    const role = me.user.role ?? pending?.role;
    if (role) me = await post<Me>("/auth/role", { role, full_name: pending?.full_name, phone_number: pending?.phone_number });
  }
  return routeFor[me.next_step];
}
