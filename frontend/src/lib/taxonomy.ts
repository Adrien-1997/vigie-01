import type { Category } from "../types";

/** Ordre d'affichage = ordre des slots catégoriels de la palette. Il est fixe : une catégorie
 *  garde sa teinte quels que soient les filtres actifs (la couleur suit l'entité, pas son rang).
 *  `hors_perimetre` prend un gris neutre plutôt qu'un slot catégoriel : c'est l'absence de
 *  catégorie, pas une catégorie de plus. */
export const CATEGORIES: Category[] = [
  "export_control",
  "contrat_armement",
  "mouvement_militaire",
  "diplomatie_defense",
  "programme_industriel",
  "hors_perimetre",
];

export const CATEGORY_LABEL: Record<Category, string> = {
  export_control: "Contrôle export",
  contrat_armement: "Contrat d'armement",
  mouvement_militaire: "Mouvement militaire",
  diplomatie_defense: "Diplomatie défense",
  programme_industriel: "Programme industriel",
  hors_perimetre: "Hors périmètre",
};

/** Rendu via var(--cat-*), définies en clair et en sombre dans styles.css. */
export const CATEGORY_VAR: Record<Category, string> = {
  export_control: "var(--cat-1)",
  contrat_armement: "var(--cat-2)",
  mouvement_militaire: "var(--cat-3)",
  diplomatie_defense: "var(--cat-4)",
  programme_industriel: "var(--cat-5)",
  hors_perimetre: "var(--cat-none)",
};

export const LANG_LABEL: Record<string, string> = {
  fr: "Français",
  en: "Anglais",
  de: "Allemand",
  it: "Italien",
  es: "Espagnol",
};
