import type { Category } from "../types";
import { VERIFIER_CATEGORIES } from "../lib/taxonomy";
import { confidenceColor } from "../lib/confidence";

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
        <span className="conf-fill" style={{ width: `${pct}%`, ["--conf-color" as string]: confidenceColor(score) }} />
      </span>
      <span className="conf-value">{score.toFixed(2)}</span>
    </span>
  );
}
