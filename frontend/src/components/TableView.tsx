import { useMemo, useState } from "react";
import type { AnalyzedItem } from "../types";
import { CATEGORY_LABEL, CATEGORY_VAR } from "../lib/taxonomy";
import { publishedMs } from "../lib/filters";
import { dateOrigin } from "../lib/threads";
import { countryLabel, resolveLocation, sourceCountryLabel, type LocationMatch } from "../lib/geo";
import { SortIcon } from "./Icons";

const PROVENANCE_SUFFIX = {
  cited: "",
  deduced: " (déduit)",
  actor: " (acteur)",
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
 *  pourquoi son item manque. Quand c'est l'acteur qui a placé l'item, l'extrait affiché reste le
 *  lieu quand il y en avait un — « Strait of Hormuz → Iran (acteur) » dit exactement ce qui s'est
 *  passé : le détroit n'est d'aucun pays, c'est le protagoniste qui porte le rattachement. */
function resolutionLabel(item: AnalyzedItem, match: LocationMatch | null): string | null {
  if (!match) return item.location.trim() ? "non rattaché à un pays" : null;

  const label = countryLabel(match.feature);
  const suffix = PROVENANCE_SUFFIX[match.provenance];
  if (match.provenance === "cited" && label === item.location.trim()) return null;
  return `→ ${label}${suffix}`;
}

/** Clés de tri propres au tableau. Elles ne remplacent pas le tri global de la barre de commande :
 *  `null` rend l'ordre reçu, qui est celui-là. Un clic trie sur la colonne, un second l'inverse, un
 *  troisième rend la main au tri du digest — sans quoi le tableau imposerait silencieusement un
 *  ordre différent de celui que le sélecteur affiche. */
type Column = "category" | "title" | "source" | "place" | "confidence" | "corroborated" | "date";
type Sorting = { column: Column; dir: "asc" | "desc" } | null;

const COLUMNS: { key: Column; label: string; title?: string; align?: "num" }[] = [
  { key: "category", label: "Catégorie" },
  { key: "title", label: "Titre" },
  { key: "source", label: "Source" },
  { key: "place", label: "Lieu" },
  { key: "date", label: "Date", title: "Date de parution ; à défaut, l'entrée en base, signalée « collecté »." },
  {
    key: "confidence",
    label: "Confiance",
    title: "Score de confiance du vérificateur — aide à la priorisation, pas une garantie de véracité.",
    align: "num",
  },
  { key: "corroborated", label: "Antécédent" },
];

const compare = (column: Column) => (a: AnalyzedItem, b: AnalyzedItem) => {
  const text = (x: string, y: string) => x.localeCompare(y, "fr");
  switch (column) {
    case "category":
      return text(CATEGORY_LABEL[a.category], CATEGORY_LABEL[b.category]);
    case "title":
      return text(a.title_fr, b.title_fr);
    case "source":
      return text(a.source, b.source);
    case "place":
      return text(a.location, b.location);
    case "date":
      return publishedMs(a) - publishedMs(b);
    case "confidence":
      return (a.confidence_score ?? 0) - (b.confidence_score ?? 0);
    case "corroborated":
      return (a.corroborated === true ? 0 : 1) - (b.corroborated === true ? 0 : 1);
  }
};

/** Ce que la colonne ne mesure pas, et qui doit rester en queue *dans les deux sens* : un item non
 *  vérifié n'est pas un item à score nul, et le sens décroissant le remonterait en tête si le
 *  vide était traité comme une valeur. Le prédicat est donc appliqué hors du produit par le sens
 *  du tri, pas à l'intérieur du comparateur. */
const isBlank: Record<Column, (i: AnalyzedItem) => boolean> = {
  category: () => false,
  title: () => false,
  source: () => false,
  place: (i) => i.location.trim() === "",
  date: (i) => publishedMs(i) === 0,
  confidence: (i) => i.confidence_score === null,
  corroborated: (i) => i.corroborated === null,
};

function formatDate(item: AnalyzedItem): { label: string; collected: boolean } | null {
  const ms = publishedMs(item);
  if (ms === 0) return null;
  return {
    label: new Date(ms).toLocaleDateString("fr-FR", {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    }),
    collected: dateOrigin(item) === "first_seen",
  };
}

/** Vue tableau : canal d'accessibilité exigé par la palette (trois teintes catégorielles
 *  passent sous 3:1 en mode clair) et vue de travail pour comparer les scores en colonne. */
export function TableView({ items }: { items: AnalyzedItem[] }) {
  const [sorting, setSorting] = useState<Sorting>(null);

  const rows = useMemo(() => {
    if (!sorting) return items;
    const sign = sorting.dir === "asc" ? 1 : -1;
    const cmp = compare(sorting.column);
    const blank = isBlank[sorting.column];
    // Tri stable : à égalité sur la colonne, l'ordre du digest est conservé.
    return [...items].sort((a, b) => {
      const [ba, bb] = [blank(a), blank(b)];
      if (ba !== bb) return ba ? 1 : -1;
      return sign * cmp(a, b);
    });
  }, [items, sorting]);

  const toggle = (column: Column) =>
    setSorting((current) => {
      if (!current || current.column !== column) return { column, dir: "asc" };
      if (current.dir === "asc") return { column, dir: "desc" };
      return null;
    });

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
            {COLUMNS.map(({ key, label, title, align }) => {
              const active = sorting?.column === key ? sorting.dir : null;
              return (
                <th
                  key={key}
                  scope="col"
                  className={align === "num" ? "num" : undefined}
                  aria-sort={active === "asc" ? "ascending" : active === "desc" ? "descending" : "none"}
                >
                  <button
                    className="th-sort"
                    onClick={() => toggle(key)}
                    title={title ?? `Trier par ${label.toLowerCase()}`}
                  >
                    {label}
                    <SortIcon dir={active} />
                  </button>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {rows.map((item) => {
            const match = resolveLocation(item);
            const resolution = resolutionLabel(item, match);
            const date = formatDate(item);
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
                  <span className="td-sub">{sourceCountryLabel(item.country)}</span>
                </td>
                <td className="wrap-sm">
                  {item.location || "—"}
                  {resolution && (
                    <>
                      <br />
                      <span className="td-sub">{resolution}</span>
                    </>
                  )}
                </td>
                {/* `first_seen` est un horodatage de lot, jamais présenté comme une parution. */}
                <td>
                  {date ? date.label : "—"}
                  {date?.collected && (
                    <>
                      <br />
                      <span className="td-sub" title="Le flux ne date pas cet article : date d'entrée en base.">
                        collecté
                      </span>
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
