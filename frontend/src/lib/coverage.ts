import type { AnalyzedItem, Category } from "../types";
import { countryKey, countryLabel, resolveLocation } from "./geo";

export interface CountryBucket {
  /** Libellé français du pays (cf. countryLabel). */
  name: string;
  total: number;
  /** Parts du total rattachées autrement que par citation de la source (cf. Provenance). */
  deduced: number;
  actor: number;
  presumed: number;
  byCategory: Map<Category, number>;
}

export interface Coverage {
  byCountry: Map<string, CountryBucket>;
  /** Items rattachés à un pays, toutes provenances confondues. */
  placed: number;
  /** Deux échecs distincts : aucun lieu extrait du texte, ou lieu extrait mais qui n'est
   *  dans aucun pays (haute mer, détroit international, commandement militaire). Les
   *  confondre masquerait lequel est en cause. */
  unlocated: number;
  unresolved: number;
  deduced: number;
  actor: number;
  presumed: number;
  /** Plus grand nombre d'items sur un même pays, pour calibrer la rampe de la carte. */
  max: number;
}

/** Ventilation de la couverture géographique d'un digest.
 *
 *  Calcul unique et partagé par la carte et la bande de KPI. Ces deux panneaux décrivaient la
 *  même chose chacun de son côté et ont fini par se contredire à l'écran : le KPI annonçait
 *  « le reste n'a pas de lieu exploitable » quand la légende comptait, pour le même digest,
 *  « 0 sans lieu extrait · 1 lieu non rattaché à un pays ». Deux calculs, deux vocabulaires,
 *  aucune contrainte de cohérence — d'où cette fonction. */
export function computeCoverage(items: AnalyzedItem[]): Coverage {
  const byCountry = new Map<string, CountryBucket>();
  let placed = 0;
  let unlocated = 0;
  let unresolved = 0;
  let deduced = 0;
  let actor = 0;
  let presumed = 0;

  for (const item of items) {
    const match = resolveLocation(item);
    if (!match) {
      if (item.location.trim()) unresolved += 1;
      else unlocated += 1;
      continue;
    }

    placed += 1;
    const key = countryKey(match.feature);
    let bucket = byCountry.get(key);
    if (!bucket) {
      bucket = {
        name: countryLabel(match.feature),
        total: 0,
        deduced: 0,
        actor: 0,
        presumed: 0,
        byCategory: new Map(),
      };
      byCountry.set(key, bucket);
    }
    bucket.total += 1;
    if (match.provenance === "deduced") {
      bucket.deduced += 1;
      deduced += 1;
    } else if (match.provenance === "actor") {
      bucket.actor += 1;
      actor += 1;
    } else if (match.provenance === "presumed") {
      bucket.presumed += 1;
      presumed += 1;
    }
    bucket.byCategory.set(item.category, (bucket.byCategory.get(item.category) ?? 0) + 1);
  }

  const max = Math.max(0, ...[...byCountry.values()].map((b) => b.total));
  return { byCountry, placed, unlocated, unresolved, deduced, actor, presumed, max };
}

/** Ce que la couverture ne place pas, énoncé par cause et jamais agrégé en un « reste » muet.
 *  Retourne une liste vide quand tout est placé, pour que l'appelant n'affiche rien. */
export function unplacedReasons(coverage: Coverage): string[] {
  const reasons: string[] = [];
  if (coverage.unlocated > 0) {
    reasons.push(`${coverage.unlocated} sans lieu extrait`);
  }
  if (coverage.unresolved > 0) {
    // Même formulation que la légende de la carte : deux vocabulaires pour un même décompte,
    // c'est précisément ce qui a laissé les deux panneaux diverger.
    const plural = coverage.unresolved > 1;
    reasons.push(`${coverage.unresolved} lieu${plural ? "x" : ""} non rattaché${plural ? "s" : ""} à un pays`);
  }
  return reasons;
}
