/** Rampe séquentielle bleue : le score est une magnitude, pas un verdict. Volontairement pas
 *  de rouge/vert — docs/cadrage.md §9 avertit qu'un score de confiance lu comme une garantie
 *  (ou comme une alerte) invalide le garde-fou du non-objectif §3. `null` (item jamais escaladé
 *  au vérificateur) retombe sur un gris neutre plutôt qu'un point de la rampe. */
export function confidenceColor(score: number | null): string {
  if (score === null) return "var(--ink-muted)";
  if (score < 0.4) return "var(--seq-250)";
  if (score < 0.6) return "var(--seq-400)";
  if (score < 0.8) return "var(--seq-550)";
  return "var(--seq-700)";
}
