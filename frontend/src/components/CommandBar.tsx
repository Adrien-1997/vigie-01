import type { ReactElement } from "react";
import { CloseIcon, ListIcon, MapIcon, TableIcon, ThreadIcon } from "./Icons";
import { activeFilterChips, EMPTY_FILTERS, type Filters, type SortKey } from "../lib/filters";

export type View = "list" | "threads" | "map" | "table";

const VIEWS: { key: View; label: string; icon: () => ReactElement }[] = [
  { key: "list", label: "Liste", icon: ListIcon },
  { key: "threads", label: "Threads", icon: ThreadIcon },
  { key: "map", label: "Carte", icon: MapIcon },
  { key: "table", label: "Tableau", icon: TableIcon },
];

interface Props {
  view: View;
  onView: (v: View) => void;
  threadCount: number;
  visible: number;
  total: number;
  filters: Filters;
  onFilters: (f: Filters) => void;
  sort: SortKey;
  onSort: (s: SortKey) => void;
  sortLabels: Record<SortKey, string>;
  windowDays: number;
  maxWindowDays: number;
  windowChoices: number[];
  onWindow: (d: number) => void;
  windowLabel: (d: number) => string;
}

/** Barre de commande, solidaire de l'en-tête plutôt que posée en tête de colonne de contenu.
 *
 *  Le digest fait 224 items, soit une page d'une cinquantaine de milliers de pixels : tout ce qui
 *  ne colle pas au haut de l'écran est hors de portée dès le troisième article. Le sélecteur de
 *  vue, le décompte et les filtres actifs sont exactement ce dont on a besoin *pendant* la lecture,
 *  pas seulement avant — d'où leur remontée dans le bandeau collant.
 *
 *  Les pastilles de filtre actif dupliquent délibérément l'état du rail : le rail est le lieu où
 *  l'on compose un filtrage (il porte les compteurs de facette), les pastilles celui où on le lit
 *  et le défait. Sans elles, un digest filtré à trois items ne se distingue pas d'un digest vide. */
export function CommandBar(props: Props) {
  const {
    view,
    onView,
    threadCount,
    visible,
    total,
    filters,
    onFilters,
    sort,
    onSort,
    sortLabels,
    windowDays,
    maxWindowDays,
    windowChoices,
    onWindow,
    windowLabel,
  } = props;

  const chips = activeFilterChips(filters);
  const filtered = visible !== total;

  return (
    <div className="commandbar">
      <div className="commandbar-row">
        <div className="segmented" role="group" aria-label="Vue">
          {VIEWS.map(({ key, label, icon: Icon }) => (
            <button key={key} aria-pressed={view === key} onClick={() => onView(key)}>
              <Icon /> {label}
              {key === "threads" && threadCount > 0 && <span className="seg-count">{threadCount}</span>}
            </button>
          ))}
        </div>

        <span className="result-count" aria-live="polite">
          {/* Le dénominateur n'est répété que s'il diffère : « 224 sur 224 » invite à chercher un
              filtrage qui n'existe pas. */}
          <strong>{visible}</strong> item{visible > 1 ? "s" : ""}
          {filtered && <span className="result-of"> sur {total}</span>}
        </span>

        <div className="topbar-spacer" />

        <label className="sr-only" htmlFor="window">
          Profondeur du digest
        </label>
        <select id="window" value={windowDays} onChange={(e) => onWindow(Number(e.target.value))}>
          {windowChoices
            .filter((d) => d <= maxWindowDays)
            .map((d) => (
              <option key={d} value={d}>
                {windowLabel(d)}
              </option>
            ))}
        </select>

        <label className="sr-only" htmlFor="sort">
          Trier par
        </label>
        <select id="sort" value={sort} onChange={(e) => onSort(e.target.value as SortKey)}>
          {(Object.keys(sortLabels) as SortKey[]).map((key) => (
            <option key={key} value={key}>
              {sortLabels[key]}
            </option>
          ))}
        </select>
      </div>

      {chips.length > 0 && (
        <div className="chips">
          <span className="chips-label">Filtres actifs</span>
          {chips.map((chip) => (
            <button
              key={chip.id}
              className="chip"
              onClick={() => onFilters(chip.next)}
              title={`Retirer le filtre ${chip.facet.toLowerCase()} : ${chip.label}`}
            >
              <span className="chip-facet">{chip.facet}</span>
              {chip.label}
              <CloseIcon />
            </button>
          ))}
          <button className="link-btn chips-clear" onClick={() => onFilters(EMPTY_FILTERS)}>
            tout retirer
          </button>
        </div>
      )}
    </div>
  );
}
