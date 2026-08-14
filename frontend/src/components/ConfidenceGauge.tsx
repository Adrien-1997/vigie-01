import type { Category } from "../types";
import { VERIFIER_CATEGORIES } from "../lib/taxonomy";

/** Rampe séquentielle bleue : le score est une magnitude, pas un verdict. Volontairement pas
 *  de rouge/vert — docs/cadrage.md §9 avertit qu'un score de confiance lu comme une garantie
 *  (ou comme une alerte) invalide le garde-fou du non-objectif §3. */
function rampStep(score: number): string {
  if (score < 0.4) return "var(--seq-250)";
  if (score < 0.6) return "var(--seq-400)";
  if (score < 0.8) return "var(--seq-550)";
  return "var(--seq-700)";
}

export function ConfidenceGauge({ score, category }: { score: number | null; category: Category }) {
  if (score === null) {
    const inScope = VERIFIER_CATEGORIES.has(category);
    return (
      <span
        className="badge quiet"
        title={
          inScope
            ? "Catégorie couverte par le vérificateur, mais le plafond d'escalade de ce run était atteint (MAX_VERIFIER_ESCALATIONS_PER_RUN)."
            : "Catégorie hors du périmètre actuel du vérificateur (V2 : contrôle export et contrats d'armement uniquement)."
        }
      >
        {inScope ? "Non vérifié · plafond du run" : "Non vérifié · hors périmètre V2"}
      </span>
    );
  }

  const pct = Math.round(score * 100);
  return (
    <span className="conf" title="Score de confiance du vérificateur — aide à la priorisation, pas une garantie de véracité.">
      <span>Confiance</span>
      <span className="conf-track" role="img" aria-label={`Score de confiance ${pct} sur 100`}>
        <span className="conf-fill" style={{ width: `${pct}%`, ["--conf-color" as string]: rampStep(score) }} />
      </span>
      <span className="conf-value">{score.toFixed(2)}</span>
    </span>
  );
}
