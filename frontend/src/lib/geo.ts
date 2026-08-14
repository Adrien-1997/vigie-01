import { feature } from "topojson-client";
import type { Feature, Geometry } from "geojson";
import topo from "world-atlas/countries-110m.json";

type CountryProps = { name: string };
export type CountryFeature = Feature<Geometry, CountryProps> & { id: string };

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const collection = feature(topo as any, (topo as any).objects.countries) as unknown as {
  features: CountryFeature[];
};

export const COUNTRIES: CountryFeature[] = collection.features;

/** Trois entités du jeu Natural Earth (Kosovo, Chypre du Nord, Somaliland) n'ont pas de code
 *  ISO numérique : sans repli sur le nom, elles partagent la clé `undefined`. */
export const countryKey = (f: CountryFeature) => f.id ?? f.properties.name;

const normalize = (s: string) =>
  s
    .toLowerCase()
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .replace(/[^a-z\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();

/** Noms français et variantes courantes → nom Natural Earth porté par le topojson.
 *  Le champ `location` est produit par le LLM en texte libre (backend/agents/analyst.py) :
 *  il n'est pas normalisé côté backend, la résolution se fait donc ici, en best-effort assumé. */
const ALIASES: Record<string, string> = {
  "etats unis": "United States of America",
  "etats unis d amerique": "United States of America",
  usa: "United States of America",
  "united states": "United States of America",
  us: "United States of America",
  amerique: "United States of America",
  "royaume uni": "United Kingdom",
  uk: "United Kingdom",
  angleterre: "United Kingdom",
  "grande bretagne": "United Kingdom",
  ecosse: "United Kingdom",
  allemagne: "Germany",
  russie: "Russia",
  "federation de russie": "Russia",
  chine: "China",
  "coree du nord": "North Korea",
  "coree du sud": "South Korea",
  coree: "South Korea",
  espagne: "Spain",
  italie: "Italy",
  israel: "Israel",
  iran: "Iran",
  france: "France",
  ukraine: "Ukraine",
  turquie: "Turkey",
  turkiye: "Turkey",
  japon: "Japan",
  inde: "India",
  bresil: "Brazil",
  "arabie saoudite": "Saudi Arabia",
  "emirats arabes unis": "United Arab Emirates",
  eau: "United Arab Emirates",
  uae: "United Arab Emirates",
  egypte: "Egypt",
  pologne: "Poland",
  suede: "Sweden",
  norvege: "Norway",
  finlande: "Finland",
  danemark: "Denmark",
  "pays bas": "Netherlands",
  hollande: "Netherlands",
  belgique: "Belgium",
  suisse: "Switzerland",
  autriche: "Austria",
  grece: "Greece",
  roumanie: "Romania",
  tchequie: "Czechia",
  "republique tcheque": "Czechia",
  taiwan: "Taiwan",
  syrie: "Syria",
  irak: "Iraq",
  liban: "Lebanon",
  jordanie: "Jordan",
  yemen: "Yemen",
  soudan: "Sudan",
  libye: "Libya",
  algerie: "Algeria",
  maroc: "Morocco",
  tunisie: "Tunisia",
  "afrique du sud": "South Africa",
  australie: "Australia",
  canada: "Canada",
  mexique: "Mexico",
  colombie: "Colombia",
  argentine: "Argentina",
  pakistan: "Pakistan",
  afghanistan: "Afghanistan",
  bielorussie: "Belarus",
  belarus: "Belarus",
  serbie: "Serbia",
  cisjordanie: "Palestine",
  "west bank": "Palestine",
  gaza: "Palestine",
  "bande de gaza": "Palestine",
  palestine: "Palestine",
  philippines: "Philippines",
  "viet nam": "Vietnam",
  vietnam: "Vietnam",
  thailande: "Thailand",
  indonesie: "Indonesia",
  malaisie: "Malaysia",
  nigeria: "Nigeria",
  ethiopie: "Ethiopia",
  kenya: "Kenya",
  tchad: "Chad",
  estonie: "Estonia",
  lettonie: "Latvia",
  lituanie: "Lithuania",
  moldavie: "Moldova",
  georgie: "Georgia",
  armenie: "Armenia",
  azerbaidjan: "Azerbaijan",
  portugal: "Portugal",
  irlande: "Ireland",
  hongrie: "Hungary",
  bulgarie: "Bulgaria",
  croatie: "Croatia",
  slovaquie: "Slovakia",
  slovenie: "Slovenia",
  "coree du sud republique de coree": "South Korea",
};

const BY_NAME = new Map<string, CountryFeature>();
for (const f of COUNTRIES) BY_NAME.set(normalize(f.properties.name), f);

/** Résout un `location` en texte libre vers un identifiant pays du topojson.
 *  Retourne null si le lieu est vide (item non localisé) ou non résolu (mer, région,
 *  organisation) — les deux cas sont comptés et affichés séparément par la carte plutôt
 *  que silencieusement écartés (cf. docs/cadrage.md §11). */
export function resolveLocation(location: string): CountryFeature | null {
  const key = normalize(location);
  if (!key) return null;

  const aliased = ALIASES[key];
  if (aliased) return BY_NAME.get(normalize(aliased)) ?? null;

  const direct = BY_NAME.get(key);
  if (direct) return direct;

  // « Taiwan Strait », « Northern Israel » : un nom de pays qualifié reste attribuable.
  // Seuil de 5 caractères des deux côtés : sans lui, « us » matcherait « Russia ».
  if (key.length >= 5) {
    for (const [name, f] of BY_NAME) {
      if (name.length >= 5 && (key.includes(name) || name.includes(key))) return f;
    }
  }
  return null;
}

/** Pays des sources (backend/config.py). "INT" = source multi-pays / institutionnelle UE. */
export const SOURCE_COUNTRY_LABEL: Record<string, string> = {
  US: "États-Unis",
  FR: "France",
  RU: "Russie",
  CN: "Chine",
  DE: "Allemagne",
  IT: "Italie",
  GB: "Royaume-Uni",
  IL: "Israël",
  ES: "Espagne",
  KR: "Corée du Sud",
  IR: "Iran",
  KP: "Corée du Nord",
  INT: "International / UE",
};

export const sourceCountryLabel = (code: string) => SOURCE_COUNTRY_LABEL[code] ?? code;
