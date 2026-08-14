import type { AnalyzedItem } from "../types";
import { CATEGORY_LABEL, CATEGORY_VAR } from "../lib/taxonomy";
import { sourceCountryLabel } from "../lib/geo";

/** Vue tableau : canal d'accessibilité exigé par la palette (trois teintes catégorielles
 *  passent sous 3:1 en mode clair) et vue de travail pour comparer les scores en colonne. */
export function TableView({ items }: { items: AnalyzedItem[] }) {
  return (
    <div className="panel table-wrap">
      <table>
        <thead>
          <tr>
            <th scope="col">Catégorie</th>
            <th scope="col">Titre</th>
            <th scope="col">Source</th>
            <th scope="col">Lieu</th>
            <th scope="col">Confiance</th>
            <th scope="col">Recoupement</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.link}>
              <td>
                <i className="dot" style={{ ["--dot" as string]: CATEGORY_VAR[item.category] }} />{" "}
                {CATEGORY_LABEL[item.category]}
              </td>
              <td className="wrap">
                <a href={item.link} target="_blank" rel="noopener noreferrer">
                  {item.title_fr}
                </a>
              </td>
              <td>
                {item.source}
                {item.state_affiliated && " · média d'État"}
                <br />
                <span style={{ color: "var(--ink-muted)" }}>{sourceCountryLabel(item.country)}</span>
              </td>
              <td>{item.location || "—"}</td>
              <td className="num">{item.confidence_score?.toFixed(2) ?? "non vérifié"}</td>
              <td>
                {item.corroborated === null ? "—" : item.corroborated ? "recoupé" : "source unique"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
