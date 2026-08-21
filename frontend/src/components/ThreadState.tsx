import type { AnalyzedItem } from "../types";
import { unthreadedReason } from "../lib/threading";

/** Quatre silences distincts derrière un `thread_id` absent — pendant exact de ConfidenceGauge pour
 *  le vérificateur. Sans cette mention, un item que le plafond du run a écarté se lit exactement
 *  comme un item dont on a vérifié qu'il n'appartenait à aucun dossier : c'est la seule des quatre
 *  situations où l'affichage affirmerait quelque chose que le système n'a pas mesuré. */
const UNTHREADED = {
  "no-candidate": {
    label: "Sans thread · aucun candidat",
    title:
      "Le portillon d'escalade du threader n'a trouvé, dans la fenêtre d'historique, aucun article dont le chevauchement atteigne le seuil : il n'y avait aucun rapprochement à tenter. C'est une mesure, pas un manque.",
  },
  examined: {
    label: "Sans thread · examiné",
    title:
      "Un candidat existait, le modèle l'a examiné et a conclu qu'aucun article de la fenêtre ne couvre le même dossier. C'est le plus solide des quatre états : un jugement rendu, pas un silence.",
  },
  capped: {
    label: "Sans thread · non cherché",
    title:
      "Un candidat existait, mais le plafond d'escalade du run (MAX_THREAD_ESCALATIONS_PER_RUN) ou le budget quotidien a coupé avant cet article : le rapprochement n'a jamais été tenté. Absence de mesure, pas mesure d'absence.",
  },
  "legacy-untracked": {
    label: "Sans thread · avant instrumentation",
    title:
      "Article analysé avant le 2026-08-21, quand le nœud de threading ne consignait pas ce qu'il avait fait de chaque item. Rien ne permet de dire s'il a été examiné ou écarté faute de budget.",
  },
} as const;

export function ThreadState({ item }: { item: AnalyzedItem }) {
  // Un item rattaché n'a rien à déclarer ici : son thread parle pour lui, dans le flux comme dans
  // l'onglet Threads.
  if (item.thread_id) return null;

  const { label, title } = UNTHREADED[unthreadedReason(item)];
  return (
    <span className="badge quiet" title={title}>
      {label}
    </span>
  );
}
