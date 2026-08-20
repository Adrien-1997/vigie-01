/** Logos des médias, collectés hors ligne par `python -m scripts.fetch_logos` et versionnés dans
 *  `src/assets/logos/`. Rien n'est chargé depuis les sites d'origine à l'affichage : dix-sept
 *  requêtes vers des tiers à chaque ouverture du digest leur donneraient l'IP du lecteur, et
 *  l'interface se dégraderait dès qu'un site tombe.
 *
 *  Aucun manifeste à tenir synchrone : le nom de fichier est le slug du nom de source, et le lot
 *  est relevé au build. Une source sans fichier — trois l'étaient à la collecte, leurs sites
 *  refusant la requête — retombe sur son monogramme, jamais sur une image cassée. */
const FILES = import.meta.glob("../assets/logos/*", {
  eager: true,
  query: "?url",
  import: "default",
}) as Record<string, string>;

const BY_SLUG = new Map<string, string>();
for (const [path, url] of Object.entries(FILES)) {
  const file = path.split("/").pop() ?? "";
  BY_SLUG.set(file.replace(/\.[^.]+$/, ""), url);
}

/** Miroir exact de `slugify` dans scripts/fetch_logos.py — les deux nomment le même fichier. */
function slugify(name: string): string {
  return name
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

export const sourceLogo = (source: string): string | null => BY_SLUG.get(slugify(source)) ?? null;

/** Repli lisible quand le logo manque : initiales des deux premiers mots, ou les deux premières
 *  lettres d'un nom d'un seul mot. Le nom complet reste porté par le titre de l'élément — le
 *  monogramme est un repère de balayage, pas une identification. */
export function monogram(source: string): string {
  const words = source.split(/[^\p{L}\p{N}]+/u).filter(Boolean);
  if (words.length === 0) return "?";
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[1][0]).toUpperCase();
}
