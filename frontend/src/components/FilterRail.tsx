import { useEffect, useState, type RefObject } from "react";
import type { AnalyzedItem, Category } from "../types";
import { CATEGORIES, CATEGORY_LABEL, CATEGORY_VAR } from "../lib/taxonomy";
import { sourceCountryLabel } from "../lib/geo";
import { applyFilters, countBy, hasActiveFilters, type Filters, type Verification } from "../lib/filters";
import { CloseIcon, FilterIcon, SearchIcon } from "./Icons";

const VERIFICATION_ROWS: { key: Verification; label: string; hint: string }[] = [
  { key: "all", label: "Tous les items", hint: "Aucun filtre de vérification" },
  { key: "scored", label: "Vérifiés", hint: "Items passés par l'agent vérificateur" },
  { key: "corroborated", label: "Avec antécédent", hint: "Un article antérieur de l'historique 7 jours traite du même dossier" },
  {
    key: "review",
    label: "À arbitrer",
    hint: "Vérifiés mais non recoupés — la file de revue humaine",
  },
];

/** Au-delà, la liste des pays de source pousse le bouton de réinitialisation hors du rail sur un
 *  écran d'ordinateur portable. Les pays sélectionnés restent affichés quoi qu'il arrive : un
 *  filtre actif ne doit jamais se cacher derrière un « voir plus ». */
const COUNTRIES_SHOWN = 8;

interface Props {
  items: AnalyzedItem[];
  filters: Filters;
  onChange: (next: Filters) => void;
  /** Cible du raccourci « / » — la recherche vit dans le rail, le raccourci est global. */
  searchRef?: RefObject<HTMLInputElement | null>;
}

export function FilterRail({ items, filters, onChange, searchRef }: Props) {
  const [showAllCountries, setShowAllCountries] = useState(false);
  // Sous 900 px le rail passe en pleine largeur au-dessus du contenu : déplié, il repoussait le
  // premier article à un millier de pixels sous la barre. Il devient donc un tiroir, ouvert à la
  // demande — et toujours ouvert dès qu'il y a la place de l'afficher en colonne.
  const [narrow, setNarrow] = useState(() => matchMedia("(max-width: 900px)").matches);
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    const query = matchMedia("(max-width: 900px)");
    const onChangeQuery = (e: MediaQueryListEvent) => setNarrow(e.matches);
    query.addEventListener("change", onChangeQuery);
    return () => query.removeEventListener("change", onChangeQuery);
  }, []);

  const set = <K extends keyof Filters>(key: K, value: Filters[K]) => onChange({ ...filters, [key]: value });

  const toggleIn = <T,>(source: Set<T>, value: T): Set<T> => {
    const next = new Set(source);
    if (!next.delete(value)) next.add(value);
    return next;
  };

  const categoryCounts = countBy(applyFilters(items, filters, "categories"), (i) => i.category);
  const countryCounts = countBy(applyFilters(items, filters, "countries"), (i) => i.country);
  const stateCount = applyFilters(items, filters, "stateAffiliated").filter((i) => i.state_affiliated).length;

  const presentCategories = CATEGORIES.filter((c) => (categoryCounts.get(c) ?? 0) > 0 || filters.categories.has(c));
  const presentCountries = [...countryCounts.keys()].sort((a, b) =>
    sourceCountryLabel(a).localeCompare(sourceCountryLabel(b), "fr"),
  );
  const shownCountries =
    showAllCountries || presentCountries.length <= COUNTRIES_SHOWN
      ? presentCountries
      : presentCountries.filter((code, i) => i < COUNTRIES_SHOWN || filters.countries.has(code));
  const hiddenCountries = presentCountries.length - shownCountries.length;

  const total = categoryCounts.size ? [...categoryCounts.values()].reduce((a, b) => a + b, 0) : 0;
  const open = !narrow || drawerOpen;

  return (
    <aside className="rail">
      {narrow && (
        <button
          className="rail-toggle"
          aria-expanded={drawerOpen}
          onClick={() => setDrawerOpen((v) => !v)}
        >
          <FilterIcon />
          Filtres
          {hasActiveFilters(filters) && <span className="seg-count">actifs</span>}
          <span className="topbar-spacer" />
          <span aria-hidden>{drawerOpen ? "▲" : "▼"}</span>
        </button>
      )}

      {open && (
        <>
          <div className="search">
            <SearchIcon />
            <input
              ref={searchRef}
              type="search"
              value={filters.query}
              onChange={(e) => set("query", e.target.value)}
              placeholder="Titre, résumé, citation…"
              aria-label="Rechercher dans le digest"
            />
            {filters.query === "" ? (
              <kbd className="search-kbd" aria-hidden>
                /
              </kbd>
            ) : (
              <button className="search-clear" onClick={() => set("query", "")} aria-label="Effacer la recherche">
                <CloseIcon />
              </button>
            )}
          </div>

          <section className="panel panel-pad">
            <div className="panel-head">
              <h2 className="panel-title">Catégorie</h2>
              {filters.categories.size > 0 && (
                <button className="link-btn" onClick={() => set("categories", new Set())}>
                  tout
                </button>
              )}
            </div>

            {total > 0 && (
              <div className="stack" role="img" aria-label="Répartition des items par catégorie">
                {presentCategories.map((c) => {
                  const n = categoryCounts.get(c) ?? 0;
                  if (n === 0) return null;
                  return (
                    <span
                      key={c}
                      style={{ flex: n, background: CATEGORY_VAR[c] }}
                      title={`${CATEGORY_LABEL[c]} — ${n}`}
                    />
                  );
                })}
              </div>
            )}

            {presentCategories.map((c) => {
              const n = categoryCounts.get(c) ?? 0;
              const on = filters.categories.has(c);
              return (
                <button
                  key={c}
                  className="filter-row"
                  aria-pressed={on}
                  disabled={n === 0 && !on}
                  onClick={() => set("categories", toggleIn(filters.categories, c))}
                >
                  <i className="dot" style={{ ["--dot" as string]: CATEGORY_VAR[c] }} />
                  {CATEGORY_LABEL[c]}
                  <span className="count">{n}</span>
                </button>
              );
            })}
          </section>

          <section className="panel panel-pad">
            <h2 className="panel-title">Vérification</h2>
            {VERIFICATION_ROWS.map((row) => (
              <button
                key={row.key}
                className="filter-row"
                aria-pressed={filters.verification === row.key}
                title={row.hint}
                onClick={() => set("verification", row.key)}
              >
                <span className="check">{filters.verification === row.key ? "✓" : ""}</span>
                {row.label}
              </button>
            ))}
            {/* Quatre lignes d'explication en permanence dans le rail, c'est autant de filtres
                repoussés sous le pli : le fond passe en infobulle, la ligne visible ne garde que
                ce qui se lit d'un coup d'œil. Depuis le 2026-08-20 le vérificateur couvre les cinq
                catégories du périmètre — ce qui borne son coût est le portillon d'escalade, pas la
                catégorie (VERIFIER_GATE_MIN_SCORE, backend/config.py). */}
            <p
              className="note"
              style={{ marginTop: 6 }}
              title="Un item n'est escaladé au vérificateur que si l'historique porte un antécédent assez proche pour être recoupé. Les autres sortent sans score plutôt qu'avec une valeur par défaut, et la carte d'item donne laquelle des trois raisons s'applique."
            >
              Escaladé seulement si l'historique a un antécédent à recouper.
            </p>
          </section>

          <section className="panel panel-pad">
            <h2 className="panel-title">Provenance</h2>
            <button
              className="filter-row"
              aria-pressed={filters.stateAffiliated}
              title="Chine, Russie, Iran, Corée du Nord : aucune source gratuite indépendante identifiée."
              onClick={() => set("stateAffiliated", !filters.stateAffiliated)}
            >
              <span className="check">{filters.stateAffiliated ? "✓" : ""}</span>
              Médias d'État seulement
              <span className="count">{stateCount}</span>
            </button>

            <div className="panel-head" style={{ marginTop: 14 }}>
              <h2 className="panel-title">Pays de la source</h2>
              {filters.countries.size > 0 && (
                <button className="link-btn" onClick={() => set("countries", new Set())}>
                  tout
                </button>
              )}
            </div>
            {shownCountries.map((code) => {
              const on = filters.countries.has(code);
              return (
                <button
                  key={code}
                  className="filter-row"
                  aria-pressed={on}
                  onClick={() => set("countries", toggleIn(filters.countries, code))}
                >
                  <span className="check">{on ? "✓" : ""}</span>
                  {sourceCountryLabel(code)}
                  <span className="count">{countryCounts.get(code)}</span>
                </button>
              );
            })}
            {hiddenCountries > 0 && (
              <button className="link-btn rail-more" onClick={() => setShowAllCountries(true)}>
                voir les {hiddenCountries} autres pays
              </button>
            )}
            {showAllCountries && presentCountries.length > COUNTRIES_SHOWN && (
              <button className="link-btn rail-more" onClick={() => setShowAllCountries(false)}>
                réduire
              </button>
            )}
          </section>

          {hasActiveFilters(filters) && (
            <button className="btn btn-ghost" onClick={() => onChange({ ...filters, ...RESET })}>
              Réinitialiser les filtres
            </button>
          )}
        </>
      )}
    </aside>
  );
}

const RESET: Partial<Filters> = {
  query: "",
  categories: new Set<Category>(),
  countries: new Set<string>(),
  verification: "all",
  stateAffiliated: false,
  mapCountry: null,
};
