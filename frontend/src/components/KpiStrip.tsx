import type { AnalyzedItem } from "../types";
import { VERIFIER_CATEGORIES } from "../lib/taxonomy";
import { resolveLocation } from "../lib/geo";

const pct = (n: number, d: number) => (d === 0 ? "—" : `${Math.round((n / d) * 100)} %`);

export function KpiStrip({ items }: { items: AnalyzedItem[] }) {
  const inScope = items.filter((i) => i.category !== "hors_perimetre");
  const verifiable = items.filter((i) => VERIFIER_CATEGORIES.has(i.category));
  const scored = items.filter((i) => i.confidence_score !== null);
  const corroborated = items.filter((i) => i.corroborated === true);
  const stateAffiliated = items.filter((i) => i.state_affiliated);
  const located = new Set(items.map((i) => resolveLocation(i.location)?.id).filter(Boolean));

  return (
    <div className="kpis">
      <div className="kpi">
        <span className="kpi-value">{inScope.length}</span>
        <span className="kpi-label">Items dans le périmètre</span>
        <span className="kpi-note">
          {items.length - inScope.length} classés hors périmètre sur {items.length} collectés
        </span>
      </div>

      <div className="kpi">
        <span className="kpi-value">
          {scored.length}
          <small>/ {verifiable.length}</small>
        </span>
        <span className="kpi-label">Vérifiés</span>
        <span className="kpi-note">{pct(scored.length, verifiable.length)} des catégories escaladables</span>
      </div>

      <div className="kpi">
        <span className="kpi-value">{corroborated.length}</span>
        <span className="kpi-label">Recoupés par l'historique</span>
        <span className="kpi-note">
          {pct(corroborated.length, scored.length)} des items vérifiés · indicateur suivi, pas maximisé
        </span>
      </div>

      <div className="kpi">
        <span className="kpi-value">{stateAffiliated.length}</span>
        <span className="kpi-label">Issus d'un média d'État</span>
        <span className="kpi-note">{pct(stateAffiliated.length, items.length)} du digest · à lire comme revendications</span>
      </div>

      <div className="kpi">
        <span className="kpi-value">{located.size}</span>
        <span className="kpi-label">Pays couverts</span>
        <span className="kpi-note">lieux d'événement résolus depuis le texte source</span>
      </div>
    </div>
  );
}
