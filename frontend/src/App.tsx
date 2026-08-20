import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiUnreachable, NoDigestYet, fetchDigest, triggerRun } from "./api";
import type { AnalyzedItem, Digest } from "./types";
import {
  EMPTY_FILTERS,
  applyFilters,
  hasActiveFilters,
  sortItems,
  type Filters,
  type SortKey,
} from "./lib/filters";
import { buildThread, groupThreads } from "./lib/threads";
import { FilterRail } from "./components/FilterRail";
import { CommandBar, type View } from "./components/CommandBar";
import { KpiStrip } from "./components/KpiStrip";
import { ItemCard } from "./components/ItemCard";
import { ThreadGroupCard } from "./components/ThreadGroup";
import { ThreadDetail } from "./components/ThreadDetail";
import { WorldMap } from "./components/WorldMap";
import { TableView } from "./components/TableView";
import { ArrowUpIcon, MoonIcon, RefreshIcon, SunIcon } from "./components/Icons";

type Status =
  | { kind: "loading" }
  | { kind: "ready"; digest: Digest }
  | { kind: "empty" }
  | { kind: "error"; message: string };

// Référence stable : un littéral `[]` recréé à chaque rendu invaliderait les mémos en aval.
const NO_ITEMS: AnalyzedItem[] = [];

// Bornées à l'exécution par `max_window_days` : la rétention est décidée côté backend.
const WINDOW_CHOICES = [1, 3, 7];

const SORT_LABEL: Record<SortKey, string> = {
  recent: "Plus récents",
  confidence: "Confiance décroissante",
  review: "Ordre de revue humaine",
  category: "Par catégorie",
};

function windowLabel(days: number): string {
  if (days === 1) return "dernières 24 h";
  return `${days} derniers jours`;
}

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
  // Distinct de `runError` : un run tronqué a produit et enregistré des items.
  const [runNotice, setRunNotice] = useState<string | null>(null);
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [view, setView] = useState<View>("list");
  const [sort, setSort] = useState<SortKey>("recent");
  // `null` = laisser le backend appliquer sa fenêtre par défaut.
  const [windowDays, setWindowDays] = useState<number | null>(null);
  // Trois états : pas de choix explicite (on suit le système), clair, sombre. Le bouton propose
  // l'inverse du thème *effectif*, sans quoi le premier clic ne changerait rien à l'écran.
  const [theme, setTheme] = useState<"light" | "dark" | null>(
    () => (localStorage.getItem("vigie-theme") as "light" | "dark" | null) ?? null,
  );
  const [systemDark, setSystemDark] = useState(() => matchMedia("(prefers-color-scheme: dark)").matches);
  const effectiveTheme = theme ?? (systemDark ? "dark" : "light");

  const chromeRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const [scrolled, setScrolled] = useState(false);

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

  // Hauteur réelle de l'en-tête collant, publiée en variable CSS. Le rail et les tableaux s'y
  // calent : une constante en dur se décale dès que la barre passe sur deux lignes (fenêtre
  // étroite) ou qu'un bandeau de run s'y ajoute, et le décalage se paie en contenu inatteignable
  // sous le rail — précisément le défaut que cette version corrige.
  useEffect(() => {
    const node = chromeRef.current;
    if (!node) return;
    const publish = () =>
      document.documentElement.style.setProperty("--chrome-h", `${Math.round(node.getBoundingClientRect().height)}px`);
    publish();
    const observer = new ResizeObserver(publish);
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 900);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Raccourcis de dépouillement : « / » pour chercher sans quitter le clavier, Échap pour
  // ressortir du champ. Ignorés quand la frappe vise déjà un champ de saisie.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const typing = target instanceof HTMLInputElement || target instanceof HTMLSelectElement;
      if (e.key === "/" && !typing && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        searchRef.current?.focus();
        searchRef.current?.select();
      } else if (e.key === "Escape" && typing) {
        searchRef.current?.blur();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const load = useCallback(async () => {
    try {
      setStatus({ kind: "ready", digest: await fetchDigest(windowDays ?? undefined) });
    } catch (e) {
      if (e instanceof NoDigestYet) setStatus({ kind: "empty" });
      else if (e instanceof ApiUnreachable)
        setStatus({ kind: "error", message: `API injoignable sur ${e.message}. Le serveur uvicorn tourne-t-il ?` });
      else setStatus({ kind: "error", message: (e as Error).message });
    }
  }, [windowDays]);

  useEffect(() => {
    void load();
  }, [load]);

  const run = async () => {
    setRunning(true);
    setRunError(null);
    setRunNotice(null);
    try {
      const result = await triggerRun();
      await load();
      if (result.truncated)
        setRunNotice(
          `Plafond de budget LLM atteint : la collecte s'est arrêtée avant la fin du lot. ` +
            `${result.item_count} item${result.item_count > 1 ? "s" : ""} analysé${result.item_count > 1 ? "s" : ""} ` +
            `et conservé${result.item_count > 1 ? "s" : ""} ; les articles non traités restent collectables à la prochaine collecte.`,
        );
    } catch (e) {
      if (e instanceof ApiUnreachable) setRunError(`API injoignable sur ${e.message}.`);
      else setRunError((e as Error).message);
    } finally {
      setRunning(false);
    }
  };

  const items = status.kind === "ready" ? status.digest.items : NO_ITEMS;
  const visible = useMemo(() => sortItems(applyFilters(items, filters), sort), [items, filters, sort]);
  // Construits sur les items *filtrés* : un filtre peut ramener un thread sous les deux articles
  // qui le définissent, auquel cas il disparaît de l'onglet — d'où la mention affichée plus bas.
  const threads = useMemo(
    () => groupThreads(visible).filter((group) => group.length > 1).map(buildThread),
    [visible],
  );

  return (
    <div className="app">
      {/* Un seul bloc collant plutôt que trois empilés au même décalage : les bandeaux de run
          partagent la position de la barre de titre et se recouvraient au défilement. */}
      <div className="chrome" ref={chromeRef}>
        <header className="topbar">
          <div className="brand">
            <strong>VIGIE</strong>
            <span>veille défense &amp; contrôle export</span>
          </div>

          <div className="topbar-spacer" />

          {status.kind === "ready" && status.digest.generated_at && (
            <span className="stamp">
              Dernière collecte {relativeStamp(status.digest.generated_at)} ·{" "}
              {windowLabel(status.digest.window_days)}
            </span>
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
          <div className="notice notice-error" role="alert">
            {runError}
          </div>
        )}

        {runNotice && (
          <div className="notice notice-warn" role="status">
            {runNotice}
          </div>
        )}

        {status.kind === "ready" && (
          <CommandBar
            view={view}
            onView={setView}
            threadCount={threads.length}
            visible={visible.length}
            total={items.length}
            filters={filters}
            onFilters={setFilters}
            sort={sort}
            onSort={setSort}
            sortLabels={SORT_LABEL}
            windowDays={status.digest.window_days}
            maxWindowDays={status.digest.max_window_days}
            windowChoices={WINDOW_CHOICES}
            onWindow={setWindowDays}
            windowLabel={windowLabel}
          />
        )}
      </div>

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
          <FilterRail items={items} filters={filters} onChange={setFilters} searchRef={searchRef} />

          <main className="content">
            <KpiStrip items={items} filtered={visible.length !== items.length} />

            {view === "map" && (
              <WorldMap
                items={applyFilters(items, filters, "mapCountry")}
                selected={filters.mapCountry}
                onSelect={(id) => setFilters({ ...filters, mapCountry: id })}
              />
            )}

            {items.length === 0 ? (
              // Fenêtre vide sur un historique non vide : c'est la profondeur qu'il faut élargir,
              // pas les filtres.
              <div className="state">
                <h2>Aucun item sur cette période</h2>
                <p>
                  Rien n'a été collecté sur les {status.digest.window_days} derniers jours. Élargir
                  la période, ou lancer une collecte.
                </p>
                {status.digest.window_days < status.digest.max_window_days && (
                  <button className="btn btn-ghost" onClick={() => setWindowDays(status.digest.max_window_days)}>
                    Voir {windowLabel(status.digest.max_window_days)}
                  </button>
                )}
              </div>
            ) : visible.length === 0 ? (
              <div className="state">
                <h2>Aucun item ne correspond</h2>
                <p>Les filtres actifs excluent tous les items de ce digest.</p>
                <button className="btn btn-ghost" onClick={() => setFilters(EMPTY_FILTERS)}>
                  Réinitialiser les filtres
                </button>
              </div>
            ) : view === "table" ? (
              <TableView items={visible} />
            ) : view === "threads" ? (
              threads.length === 0 ? (
                <div className="state">
                  <h2>Aucun thread sur cette période</h2>
                  <p>
                    Un thread naît du rapprochement d'au moins deux articles traitant du même
                    dossier. La plupart des items restent isolés : c'est l'état normal d'une veille,
                    pas une anomalie. Les threads apparaîtront ici à mesure que l'historique
                    s'accumule.
                  </p>
                  {hasActiveFilters(filters) && (
                    <button className="btn btn-ghost" onClick={() => setFilters(EMPTY_FILTERS)}>
                      Réinitialiser les filtres
                    </button>
                  )}
                </div>
              ) : (
                <div className="list">
                  {hasActiveFilters(filters) && (
                    <p className="note">
                      Les threads sont reconstruits sur les items filtrés : un article exclu par
                      un filtre est absent de sa chronologie, et un thread réduit à un seul article
                      n'est plus affiché ici.
                    </p>
                  )}
                  {threads.map((thread) => (
                    <ThreadDetail key={thread.id} thread={thread} />
                  ))}
                </div>
              )
            ) : (
              <div className="list">
                {groupThreads(visible).map((group) =>
                  group.length > 1 ? (
                    <ThreadGroupCard
                      key={group[0].thread_id}
                      items={group}
                      onOpen={() => setView("threads")}
                    />
                  ) : (
                    <ItemCard key={group[0].link} item={group[0]} />
                  ),
                )}
              </div>
            )}
          </main>
        </div>
      )}

      {/* Retour en tête : une page de digest dépasse les 50 000 pixels, le défilement inverse
          n'est pas une option de navigation praticable. */}
      {scrolled && (
        <button
          className="to-top"
          onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
          title="Revenir en haut"
        >
          <ArrowUpIcon />
          Haut de page
        </button>
      )}
    </div>
  );
}
