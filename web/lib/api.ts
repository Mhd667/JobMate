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

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (!token) throw new ApiError(401, "Session expirée");
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...(init.headers ?? {}) },
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(res.status, typeof body.detail === "string" ? body.detail : `Erreur ${res.status}`);
  return body as T;
}

export const routeFor: Record<NextStep, string> = {
  choose_role: "/role",
  create_company: "/onboarding",
  create_profile: "/onboarding",
  employer_home: "/home",
  candidate_home: "/home",
};
