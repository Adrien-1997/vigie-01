import type { Digest } from "./types";

const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8080";

export class NoDigestYet extends Error {}
export class ApiUnreachable extends Error {}

/** Résultat de `POST /run`. `truncated` : le plafond de budget LLM quotidien
 *  (backend/guardrails.py) a arrêté le run avant la fin du lot. Ce n'est pas une erreur — les items
 *  déjà analysés sont enregistrés et servis — mais le digest ne porte qu'une partie de la collecte. */
export type RunResult = { item_count: number; truncated: boolean };

/** `days` : profondeur de la fenêtre glissante servie par l'API. Omis, le backend applique sa
 *  valeur par défaut (DIGEST_WINDOW_DAYS) — le front n'a pas à dupliquer ce choix produit. */
export async function fetchDigest(days?: number): Promise<Digest> {
  const url = days === undefined ? `${BASE}/events` : `${BASE}/events?days=${days}`;
  let res: Response;
  try {
    res = await fetch(url);
  } catch {
    throw new ApiUnreachable(BASE);
  }
  if (res.status === 404) throw new NoDigestYet();
  if (!res.ok) throw new Error(`GET /events → ${res.status}`);
  return res.json();
}

export async function triggerRun(): Promise<RunResult> {
  let res: Response;
  try {
    res = await fetch(`${BASE}/run`, { method: "POST" });
  } catch {
    throw new ApiUnreachable(BASE);
  }
  if (res.ok) return res.json();

  const detail = await res.json().then(
    (b) => b?.detail as string | undefined,
    () => undefined,
  );
  throw new Error(detail ?? `POST /run → ${res.status}`);
}
