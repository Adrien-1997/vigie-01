import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiUnreachable, BudgetExceeded, NoDigestYet, fetchDigest, triggerRun } from "./api";
import type { AnalyzedItem, Digest } from "./types";
import { EMPTY_FILTERS, applyFilters, sortItems, type Filters, type SortKey } from "./lib/filters";
import { FilterRail } from "./components/FilterRail";
import { KpiStrip } from "./components/KpiStrip";
import { ItemCard } from "./components/ItemCard";
import { WorldMap } from "./components/WorldMap";
import { TableView } from "./components/TableView";
import { ListIcon, MapIcon, MoonIcon, RefreshIcon, SunIcon, TableIcon } from "./components/Icons";

type Status =
  | { kind: "loading" }
  | { kind: "ready"; digest: Digest }
  | { kind: "empty" }
  | { kind: "error"; message: string };

type View = "list" | "map" | "table";

// Référence stable : un littéral `[]` recréé à chaque rendu invaliderait les mémos en aval.
const NO_ITEMS: AnalyzedItem[] = [];

const SORT_LABEL: Record<SortKey, string> = {
  recent: "Plus récents",
  confidence: "Confiance décroissante",
  review: "Ordre de revue humaine",
  category: "Par catégorie",
};

function relativeStamp(iso: string): string {
  const then = new Date(iso);
  if (Number.isNaN(then.getTime())) return iso;
  const minutes = Math.round((Date.now() - then.getTime()) / 60000);
  if (minutes < 1) return "à l'instant";
  if (minutes < 60) return `il y a ${minutes} min`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `il y a ${hours} h`;
  return then.toLocaleDateString("fr-FR", { day: "2-digit", month: "long", hour: "2-digit", minute: "2-digit" });
}

export default function App() {
  const [status, setStatus] = useState<Status>({ kind: "loading" });
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [view, setView] = useState<View>("list");
  const [sort, setSort] = useState<SortKey>("recent");
  // Trois états : pas de choix explicite (on suit le système), clair, sombre. Le bouton doit
  // proposer l'inverse du thème *effectif*, pas de la préférence stockée — sinon, sous un système
  // en sombre et sans choix stocké, le premier clic ne change rien à l'écran.
  const [theme, setTheme] = useState<"light" | "dark" | null>(
    () => (localStorage.getItem("vigie-theme") as "light" | "dark" | null) ?? null,
  );
  const [systemDark, setSystemDark] = useState(() => matchMedia("(prefers-color-scheme: dark)").matches);
  const effectiveTheme = theme ?? (systemDark ? "dark" : "light");

  useEffect(() => {
    const query = matchMedia("(prefers-color-scheme: dark)");
    const onChange = (e: MediaQueryListEvent) => setSystemDark(e.matches);
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);

  useEffect(() => {
    if (theme) {
      document.documentElement.dataset.theme = theme;
      localStorage.setItem("vigie-theme", theme);
    } else {
      delete document.documentElement.dataset.theme;
    }
  }, [theme]);

  const load = useCallback(async () => {
    try {
      setStatus({ kind: "ready", digest: await fetchDigest() });
    } catch (e) {
      if (e instanceof NoDigestYet) setStatus({ kind: "empty" });
      else if (e instanceof ApiUnreachable)
        setStatus({ kind: "error", message: `API injoignable sur ${e.message}. Le serveur uvicorn tourne-t-il ?` });
      else setStatus({ kind: "error", message: (e as Error).message });
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const run = async () => {
    setRunning(true);
    setRunError(null);
    try {
      await triggerRun();
      await load();
    } catch (e) {
      if (e instanceof BudgetExceeded) setRunError(`Plafond de budget atteint — ${e.message}`);
      else if (e instanceof ApiUnreachable) setRunError(`API injoignable sur ${e.message}.`);
      else setRunError((e as Error).message);
    } finally {
      setRunning(false);
    }
  };

  const items = status.kind === "ready" ? status.digest.items : NO_ITEMS;
  const visible = useMemo(() => sortItems(applyFilters(items, filters), sort), [items, filters, sort]);

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <strong>VIGIE</strong>
          <span>veille défense &amp; contrôle export</span>
        </div>

        <div className="topbar-spacer" />

        {status.kind === "ready" && (
          <span className="stamp">Digest généré {relativeStamp(status.digest.generated_at)}</span>
        )}

        <button
          className="icon-btn"
          onClick={() => setTheme(effectiveTheme === "dark" ? "light" : "dark")}
          aria-label={effectiveTheme === "dark" ? "Passer en thème clair" : "Passer en thème sombre"}
          title={effectiveTheme === "dark" ? "Thème clair" : "Thème sombre"}
        >
          {effectiveTheme === "dark" ? <SunIcon /> : <MoonIcon />}
        </button>

        <button className="btn" onClick={run} disabled={running}>
          <RefreshIcon />
          {running ? "Collecte en cours…" : "Lancer la collecte"}
        </button>
      </header>

      {running && (
        <div className="running-bar" role="status" aria-label="Collecte en cours">
          <i />
        </div>
      )}

      {runError && (
        <div className="topbar" style={{ borderTop: "none", color: "var(--status-critical)", fontSize: 13 }}>
          {runError}
        </div>
      )}

      {status.kind === "loading" && (
        <div className="body">
          <div className="skeleton" style={{ height: 320 }} />
          <div className="content">
            <div className="skeleton" style={{ height: 88 }} />
            <div className="skeleton" style={{ height: 150 }} />
            <div className="skeleton" style={{ height: 150 }} />
          </div>
        </div>
      )}

      {status.kind === "empty" && (
        <div className="state">
          <h2>Aucun digest généré</h2>
          <p>
            Le pipeline n'a pas encore tourné. « Lancer la collecte » déclenche la collecte RSS,
            le dédoublonnage, la classification et la vérification — comptez quelques minutes.
          </p>
        </div>
      )}

      {status.kind === "error" && (
        <div className="state error">
          <h2>Digest indisponible</h2>
          <p>{status.message}</p>
          <button className="btn btn-ghost" onClick={() => void load()}>
            Réessayer
          </button>
        </div>
      )}

      {status.kind === "ready" && (
        <div className="body">
          <FilterRail items={items} filters={filters} onChange={setFilters} />

          <main className="content">
            <KpiStrip items={items} />

            <div className="toolbar">
              <div className="segmented">
                <button aria-pressed={view === "list"} onClick={() => setView("list")}>
                  <ListIcon /> Liste
                </button>
                <button aria-pressed={view === "map"} onClick={() => setView("map")}>
                  <MapIcon /> Carte
                </button>
                <button aria-pressed={view === "table"} onClick={() => setView("table")}>
                  <TableIcon /> Tableau
                </button>
              </div>

              <span className="result-count">
                {visible.length} affiché{visible.length > 1 ? "s" : ""} sur {items.length}
              </span>

              <div className="topbar-spacer" />

              <label className="sr-only" htmlFor="sort">
                Trier par
              </label>
              <select id="sort" value={sort} onChange={(e) => setSort(e.target.value as SortKey)}>
                {(Object.keys(SORT_LABEL) as SortKey[]).map((key) => (
                  <option key={key} value={key}>
                    {SORT_LABEL[key]}
                  </option>
                ))}
              </select>
            </div>

            {view === "map" && (
              <WorldMap
                items={applyFilters(items, filters, "mapCountry")}
                selected={filters.mapCountry}
                onSelect={(id) => setFilters({ ...filters, mapCountry: id })}
              />
            )}

            {visible.length === 0 ? (
              <div className="state">
                <h2>Aucun item ne correspond</h2>
                <p>Les filtres actifs excluent tous les items de ce digest.</p>
                <button className="btn btn-ghost" onClick={() => setFilters(EMPTY_FILTERS)}>
                  Réinitialiser les filtres
                </button>
              </div>
            ) : view === "table" ? (
              <TableView items={visible} />
            ) : (
              <div className="list">
                {visible.map((item) => (
                  <ItemCard key={item.link} item={item} />
                ))}
              </div>
            )}
          </main>
        </div>
      )}
    </div>
  );
}
