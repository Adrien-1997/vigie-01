import type { Digest } from "./types";

const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8080";

export class NoDigestYet extends Error {}
export class ApiUnreachable extends Error {}
export class BudgetExceeded extends Error {}

export async function fetchDigest(): Promise<Digest> {
  let res: Response;
  try {
    res = await fetch(`${BASE}/events`);
  } catch {
    throw new ApiUnreachable(BASE);
  }
  if (res.status === 404) throw new NoDigestYet();
  if (!res.ok) throw new Error(`GET /events → ${res.status}`);
  return res.json();
}

export async function triggerRun(): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`${BASE}/run`, { method: "POST" });
  } catch {
    throw new ApiUnreachable(BASE);
  }
  if (res.ok) return;

  const detail = await res.json().then(
    (b) => b?.detail as string | undefined,
    () => undefined,
  );
  // 429 = plafond de budget LLM atteint (backend/guardrails.py), pas une panne serveur.
  if (res.status === 429) throw new BudgetExceeded(detail ?? "Plafond de budget LLM atteint.");
  throw new Error(detail ?? `POST /run → ${res.status}`);
}
