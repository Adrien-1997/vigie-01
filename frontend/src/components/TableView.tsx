import type { AnalyzedItem } from "../types";
import { CATEGORY_LABEL, CATEGORY_VAR } from "../lib/taxonomy";
import { countryLabel, resolveLocation, sourceCountryLabel, type LocationMatch } from "../lib/geo";

const PROVENANCE_SUFFIX = {
  cited: "",
  deduced: " (déduit)",
  presumed: " (présumé domestique)",
} as const;

/** Seconde ligne de la colonne Lieu : où l'item atterrit sur la carte, en français.
 *
 *  `location` est un extrait verbatim, donc dans la langue de la source (garde-fou §8) : une
 *  source allemande produit « Großbritannien », qu'on ne peut pas traduire dans la donnée sans
 *  casser la vérification. Le pays résolu est donc affiché à côté de l'extrait, et non à sa
 *  place — sauf quand les deux coïncident, où répéter « Ukraine → Ukraine » n'apprend rien.
 *
 *  Un lieu extrait mais rattachable à aucun pays est dit tel quel : sans cette mention, la carte
 *  le compte dans sa légende alors que le tableau n'en dit rien, et l'analyste ne peut pas savoir
 *  pourquoi son item manque. */
function resolutionLabel(item: AnalyzedItem, match: LocationMatch | null): string | null {
  if (!match) return item.location.trim() ? "non rattaché à un pays" : null;

  const label = countryLabel(match.feature);
  const suffix = PROVENANCE_SUFFIX[match.provenance];
  if (match.provenance === "cited" && label === item.location.trim()) return null;
  return `→ ${label}${suffix}`;
}

/** Vue tableau : canal d'accessibilité exigé par la palette (trois teintes catégorielles
 *  passent sous 3:1 en mode clair) et vue de travail pour comparer les scores en colonne. */
export function TableView({ items }: { items: AnalyzedItem[] }) {
  // Ne jamais fusionner silencieusement : un thread reste visible ligne par ligne, avec un
  // compteur pour signaler le regroupement.
  const threadCounts = new Map<string, number>();
  for (const item of items) {
    if (item.thread_id) threadCounts.set(item.thread_id, (threadCounts.get(item.thread_id) ?? 0) + 1);
  }

  return (
    <div className="panel table-wrap">
      <table>
        <thead>
          <tr>
            <th scope="col">Catégorie</th>
            <th scope="col">Titre</th>
            <th scope="col">Source</th>
            <th scope="col">Lieu</th>
            <th scope="col" title="Score de confiance du vérificateur — aide à la priorisation, pas une garantie de véracité.">
              Confiance
            </th>
            <th scope="col">Antécédent</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const match = resolveLocation(item);
            const resolution = resolutionLabel(item, match);
            return (
              <tr key={item.link}>
                <td>
                  <i className="dot" style={{ ["--dot" as string]: CATEGORY_VAR[item.category] }} />{" "}
                  {CATEGORY_LABEL[item.category]}
                </td>
                <td className="wrap">
                  <a href={item.link} target="_blank" rel="noopener noreferrer">
                    {item.title_fr}
                  </a>
                  {item.thread_id && (threadCounts.get(item.thread_id) ?? 0) > 1 && (
                    <>
                      {" "}
                      <span className="badge quiet" title="Plusieurs articles rattachés au même dossier">
                        Thread · {threadCounts.get(item.thread_id)}
                      </span>
                    </>
                  )}
                </td>
                <td>
                  {item.source}
                  {item.state_affiliated && " · média d'État"}
                  <br />
                  <span style={{ color: "var(--ink-muted)" }}>{sourceCountryLabel(item.country)}</span>
                </td>
                <td className="wrap">
                  {item.location || "—"}
                  {resolution && (
                    <>
                      <br />
                      <span style={{ color: "var(--ink-muted)" }}>{resolution}</span>
                    </>
                  )}
                </td>
                <td className="num">{item.confidence_score?.toFixed(2) ?? "non vérifié"}</td>
                <td>
                  {item.corroborated === null ? "—" : item.corroborated ? "avec antécédent" : "sans antécédent"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
