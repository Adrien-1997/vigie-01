import type { AnalyzedItem, Category } from "../types";

/** Catégories que le vérificateur escaladait jusqu'au 2026-08-20, jour où le portillon d'escalade
 *  (VERIFIER_GATE_MIN_SCORE, backend/config.py) a remplacé la restriction par catégorie et ouvert
 *  tout le périmètre MECE. Ne sert plus qu'à lire les enregistrements écrits avant ce jour, qui ne
 *  portent pas `has_antecedent_candidate` — la rétention étant de 7 jours, ils seront sortis du
 *  digest le 2026-08-27 et ce repli pourra partir avec eux. */
const LEGACY_VERIFIER_CATEGORIES: ReadonlySet<Category> = new Set<Category>([
  "export_control",
  "contrat_armement",
]);

/** Pourquoi un item ne porte pas de score. Ces silences ne se lisent pas de la même façon :
 *  « rien d'assez proche à recouper dans la fenêtre » est une mesure, « le plafond du run a coupé
 *  avant d'y arriver » est une absence de mesure. Les confondre laisserait croire à un manque
 *  là où le système a bel et bien regardé. */
export type UnscoredReason = "no-antecedent" | "capped" | "legacy-out-of-scope";

/** À n'appeler que sur un item dont `confidence_score` est nul — sur un item scoré, la question
 *  n'a pas de sens. */
export function unscoredReason(item: AnalyzedItem): UnscoredReason {
  if (item.has_antecedent_candidate === false) return "no-antecedent";
  if (item.has_antecedent_candidate === true) return "capped";
  return LEGACY_VERIFIER_CATEGORIES.has(item.category) ? "capped" : "legacy-out-of-scope";
}

/** Un item que le vérificateur pouvait scorer : le dénominateur honnête d'un taux de vérification.
 *  Depuis le portillon, ce n'est plus la catégorie qui en décide mais la présence d'un antécédent
 *  candidat dans l'historique. */
export function isEscalatable(item: AnalyzedItem): boolean {
  if (item.has_antecedent_candidate === true) return true;
  if (item.has_antecedent_candidate === false) return false;
  return LEGACY_VERIFIER_CATEGORIES.has(item.category);
}
