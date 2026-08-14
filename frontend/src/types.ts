export type Category =
  | "export_control"
  | "contrat_armement"
  | "mouvement_militaire"
  | "diplomatie_defense"
  | "programme_industriel"
  | "hors_perimetre";

/** Miroir de AnalyzedItem (backend/state.py). confidence_score et corroborated ne sont
 *  renseignés que pour les catégories couvertes par le vérificateur (VERIFIER_CATEGORIES). */
export interface AnalyzedItem {
  source: string;
  lang: string;
  country: string;
  state_affiliated: boolean;
  title: string;
  title_fr: string;
  link: string;
  published: string;
  category: Category;
  summary: string;
  citation: string;
  location: string;
  /** Pays déduit de `location` par le LLM, nom anglais — non vérifiable verbatim.
   *  Optionnel : les digests produits avant son introduction ne le portent pas. */
  location_country?: string;
  /** Aucun lieu nommé, mais le modèle juge l'événement situé dans le pays de la source
   *  (`country`). Rattachement présumé, plus faible que `location_country`. */
  domestic_to_source?: boolean;
  confidence_score: number | null;
  corroborated: boolean | null;
}

export interface Digest {
  generated_at: string;
  items: AnalyzedItem[];
}
