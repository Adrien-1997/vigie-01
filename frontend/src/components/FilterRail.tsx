import type { AnalyzedItem, Category } from "../types";
import { CATEGORIES, CATEGORY_LABEL, CATEGORY_VAR } from "../lib/taxonomy";
import { sourceCountryLabel } from "../lib/geo";
import { applyFilters, countBy, hasActiveFilters, type Filters, type Verification } from "../lib/filters";
import { SearchIcon } from "./Icons";

const VERIFICATION_ROWS: { key: Verification; label: string; hint: string }[] = [
  { key: "all", label: "Tous les items", hint: "Aucun filtre de vérification" },
  { key: "scored", label: "Vérifiés", hint: "Items passés par l'agent vérificateur" },
  { key: "corroborated", label: "Avec antécédent", hint: "Un article antérieur de l'historique 30 jours traite du même dossier" },
  {
    key: "review",
    label: "À arbitrer",
    hint: "Vérifiés mais non recoupés — la file de revue humaine",
  },
];

interface Props {
  items: AnalyzedItem[];
  filters: Filters;
  onChange: (next: Filters) => void;
}

export function FilterRail({ items, filters, onChange }: Props) {
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

  const total = categoryCounts.size ? [...categoryCounts.values()].reduce((a, b) => a + b, 0) : 0;

  return (
    <aside className="rail">
      <div className="search">
        <SearchIcon />
        <input
          type="search"
          value={filters.query}
          onChange={(e) => set("query", e.target.value)}
          placeholder="Titre, résumé, citation…"
          aria-label="Rechercher dans le digest"
        />
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
        <p className="note" style={{ marginTop: 8 }}>
          Le vérificateur ne couvre que le contrôle export et les contrats d'armement (V2, tranche 1).
          Les autres items sortent sans score plutôt qu'avec une valeur par défaut.
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

        <h2 className="panel-title" style={{ marginTop: 14 }}>
          Pays de la source
        </h2>
        {presentCountries.map((code) => {
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
      </section>

      {hasActiveFilters(filters) && (
        <button className="btn btn-ghost" onClick={() => onChange({ ...filters, ...RESET })}>
          Réinitialiser les filtres
        </button>
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
