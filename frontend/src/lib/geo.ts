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

// Lettres que NFD ne décompose pas : ce ne sont pas des voyelles accentuées mais des caractères
// à part entière. Sans translittération explicite elles tombent dans le filtre [^a-z\s] et
// « Großbritannien » devient « gro britannien », « Tromsø » devient « troms », « Łódź » devient
// « odz » — aucun ne matche plus rien.
const TRANSLIT: Record<string, string> = {
  ß: "ss",
  ø: "o",
  æ: "ae",
  œ: "oe",
  ł: "l",
  đ: "d",
  ð: "d",
  þ: "th",
  ı: "i",
};

const normalize = (s: string) =>
  s
    .toLowerCase()
    .replace(/[ßøæœłđðþı]/g, (c) => TRANSLIT[c])
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .replace(/[^a-z\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();

/** Noms de pays dans les langues du périmètre (fr, en, de, it, es — cf. docs/cadrage.md §4) et
 *  variantes courantes → nom Natural Earth porté par le topojson.
 *
 *  Le champ `location` est un extrait VERBATIM du texte source (garde-fou §8) : il sort donc dans
 *  la langue de la source, pas en français. Sur un run réel, « Großbritannien » et « Vereinigten
 *  Staaten » ressortaient non rattachés faute d'entrée allemande — d'où ce référentiel multilingue.
 *  Traduire un nom de pays vers l'index de la carte n'est pas une déduction : le pays est nommé
 *  explicitement dans la source. Le rattachement d'une localité à son pays en est une : il passe
 *  par `location_country`, produit par le LLM et signalé comme déduit jusque dans la légende. */
const ALIASES: Record<string, string> = {
  // Allemand
  "vereinigte staaten": "United States of America",
  "vereinigten staaten": "United States of America",
  "vereinigte staaten von amerika": "United States of America",
  grossbritannien: "United Kingdom",
  deutschland: "Germany",
  frankreich: "France",
  russland: "Russia",
  spanien: "Spain",
  italien: "Italy",
  polen: "Poland",
  niederlande: "Netherlands",
  belgien: "Belgium",
  schweiz: "Switzerland",
  osterreich: "Austria",
  schweden: "Sweden",
  norwegen: "Norway",
  finnland: "Finland",
  griechenland: "Greece",
  turkei: "Turkey",
  agypten: "Egypt",
  indien: "India",
  japan: "Japan",
  sudkorea: "South Korea",
  nordkorea: "North Korea",
  "vereinigte arabische emirate": "United Arab Emirates",
  "saudi arabien": "Saudi Arabia",
  litauen: "Lithuania",
  lettland: "Latvia",
  estland: "Estonia",
  // Italien (grecia/polonia/russia/china couvrent aussi l'espagnol ou l'index anglais)
  "stati uniti": "United States of America",
  "stati uniti d america": "United States of America",
  "regno unito": "United Kingdom",
  germania: "Germany",
  francia: "France",
  spagna: "Spain",
  cina: "China",
  giappone: "Japan",
  turchia: "Turkey",
  grecia: "Greece",
  polonia: "Poland",
  ucraina: "Ukraine",
  israele: "Israel",
  "corea del sud": "South Korea",
  "corea del nord": "North Korea",
  "arabia saudita": "Saudi Arabia",
  // Espagnol
  "estados unidos": "United States of America",
  "reino unido": "United Kingdom",
  alemania: "Germany",
  espana: "Spain",
  rusia: "Russia",
  ucrania: "Ukraine",
  turquia: "Turkey",
  "corea del sur": "South Korea",
  "arabia saudi": "Saudi Arabia",
  "emiratos arabes unidos": "United Arab Emirates",
  "paises bajos": "Netherlands",
  "islas malvinas": "Falkland Is.",
  malvinas: "Falkland Is.",
  // Français et anglais
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
  // Formes anglaises longues ou officielles que le topojson abrège. Le champ `location_country`
  // est produit en anglais par le LLM : sans ces entrées, « Czech Republic » ou « Democratic
  // Republic of the Congo » seraient rejetés alors que le pays visé existe bien sur la carte.
  "czech republic": "Czechia",
  "democratic republic of the congo": "Dem. Rep. Congo",
  "dr congo": "Dem. Rep. Congo",
  drc: "Dem. Rep. Congo",
  "republic of the congo": "Congo",
  "bosnia and herzegovina": "Bosnia and Herz.",
  "north macedonia": "Macedonia",
  "south sudan": "S. Sudan",
  "central african republic": "Central African Rep.",
  "dominican republic": "Dominican Rep.",
  "equatorial guinea": "Eq. Guinea",
  "falkland islands": "Falkland Is.",
  "solomon islands": "Solomon Is.",
  "east timor": "Timor-Leste",
  "timor leste": "Timor-Leste",
  "western sahara": "W. Sahara",
  swaziland: "eSwatini",
  eswatini: "eSwatini",
  burma: "Myanmar",
  "ivory coast": "Côte d'Ivoire",
  "northern cyprus": "N. Cyprus",
  "russian federation": "Russia",
  "republic of korea": "South Korea",
  dprk: "North Korea",
  "state of palestine": "Palestine",
};

/** Libellés français des entités du topojson. L'interface est en français : sans cette table,
 *  la carte affiche « United States of America » et « Germany » dans une UI qui ne l'est pas.
 *
 *  Table d'exceptions : une entité absente d'ici s'affiche sous son nom Natural Earth, ce qui
 *  n'est correct que si ce nom est déjà le nom français (Angola, Canada, Mali, Qatar…). Toute
 *  entité dont le nom français diffère, ne serait-ce que d'un accent, doit donc figurer ici. */
const COUNTRY_FR: Record<string, string> = {
  Albania: "Albanie", Algeria: "Algérie", Antarctica: "Antarctique", Argentina: "Argentine",
  Armenia: "Arménie", Australia: "Australie", Austria: "Autriche", Azerbaijan: "Azerbaïdjan",
  Belarus: "Biélorussie", Belgium: "Belgique", Benin: "Bénin", Bhutan: "Bhoutan",
  Bolivia: "Bolivie", "Bosnia and Herz.": "Bosnie-Herzégovine", Brazil: "Brésil",
  Bulgaria: "Bulgarie", Cambodia: "Cambodge", Cameroon: "Cameroun",
  "Central African Rep.": "République centrafricaine", Chad: "Tchad", Chile: "Chili",
  China: "Chine", Colombia: "Colombie", Croatia: "Croatie", Cyprus: "Chypre",
  Czechia: "Tchéquie", "Dem. Rep. Congo": "République démocratique du Congo",
  Denmark: "Danemark", "Dominican Rep.": "République dominicaine", Ecuador: "Équateur",
  Egypt: "Égypte", "El Salvador": "Salvador", "Eq. Guinea": "Guinée équatoriale",
  Eritrea: "Érythrée", Estonia: "Estonie", Ethiopia: "Éthiopie",
  "Falkland Is.": "Îles Malouines", Fiji: "Fidji", Finland: "Finlande",
  "Fr. S. Antarctic Lands": "Terres australes françaises", Gambia: "Gambie",
  Georgia: "Géorgie", Germany: "Allemagne", Greece: "Grèce", Greenland: "Groenland",
  Guinea: "Guinée", "Guinea-Bissau": "Guinée-Bissau", Haiti: "Haïti", Hungary: "Hongrie",
  Iceland: "Islande", India: "Inde", Indonesia: "Indonésie", Iraq: "Irak", Ireland: "Irlande",
  Israel: "Israël", Italy: "Italie", Jamaica: "Jamaïque", Japan: "Japon", Jordan: "Jordanie",
  Kuwait: "Koweït", Kyrgyzstan: "Kirghizistan", Latvia: "Lettonie", Lebanon: "Liban",
  Liberia: "Libéria", Libya: "Libye", Lithuania: "Lituanie", Macedonia: "Macédoine du Nord",
  Malaysia: "Malaisie", Mauritania: "Mauritanie", Mexico: "Mexique", Moldova: "Moldavie",
  Mongolia: "Mongolie", Montenegro: "Monténégro", Morocco: "Maroc", Myanmar: "Birmanie",
  "N. Cyprus": "Chypre du Nord", Namibia: "Namibie", Nepal: "Népal", Netherlands: "Pays-Bas",
  "New Caledonia": "Nouvelle-Calédonie", "New Zealand": "Nouvelle-Zélande",
  "North Korea": "Corée du Nord", Norway: "Norvège", "Papua New Guinea": "Papouasie-Nouvelle-Guinée",
  Peru: "Pérou", Poland: "Pologne", "Puerto Rico": "Porto Rico", Romania: "Roumanie",
  Russia: "Russie", "S. Sudan": "Soudan du Sud", "Saudi Arabia": "Arabie saoudite",
  Senegal: "Sénégal", Serbia: "Serbie", Slovakia: "Slovaquie", Slovenia: "Slovénie",
  "Solomon Is.": "Îles Salomon", Somalia: "Somalie", "South Africa": "Afrique du Sud",
  "South Korea": "Corée du Sud", Spain: "Espagne", Sudan: "Soudan", Sweden: "Suède",
  Switzerland: "Suisse", Syria: "Syrie", Taiwan: "Taïwan", Tajikistan: "Tadjikistan",
  Tanzania: "Tanzanie", Thailand: "Thaïlande", "Timor-Leste": "Timor oriental",
  "Trinidad and Tobago": "Trinité-et-Tobago", Tunisia: "Tunisie", Turkey: "Turquie",
  Turkmenistan: "Turkménistan", Uganda: "Ouganda",
  "United Arab Emirates": "Émirats arabes unis", "United Kingdom": "Royaume-Uni",
  "United States of America": "États-Unis", Uzbekistan: "Ouzbékistan",
  "W. Sahara": "Sahara occidental", Yemen: "Yémen", Zambia: "Zambie", eSwatini: "Eswatini",
};

/** Nom d'un pays tel qu'affiché dans l'interface (français). */
export const countryLabel = (f: CountryFeature) => COUNTRY_FR[f.properties.name] ?? f.properties.name;

const BY_KEY = new Map<string, CountryFeature>();
for (const f of COUNTRIES) BY_KEY.set(countryKey(f), f);

/** Chemin inverse de `countryKey` : de l'identifiant porté par un filtre de carte au libellé
 *  français. La sélection de carte ne transporte que la clé, et l'afficher telle quelle ferait
 *  remonter un code numérique dans une interface en français. */
export const countryLabelByKey = (key: string) => {
  const f = BY_KEY.get(key);
  return f ? countryLabel(f) : key;
};

const BY_NAME = new Map<string, CountryFeature>();
for (const f of COUNTRIES) BY_NAME.set(normalize(f.properties.name), f);

/** Correspondance certaine : le texte EST un nom de pays, à un alias ou une langue près. */
function matchExact(name: string): CountryFeature | null {
  const key = normalize(name);
  if (!key) return null;

  const aliased = ALIASES[key];
  if (aliased) return BY_NAME.get(normalize(aliased)) ?? null;

  return BY_NAME.get(key) ?? null;
}

/** Correspondance approchée : « Taiwan Strait », « Northern Israel » — un nom de pays qualifié
 *  reste attribuable. Seuil de 5 caractères des deux côtés : sans lui, « us » matcherait « Russia ».
 *
 *  Retourne null dès que plusieurs pays correspondent, au lieu du premier trouvé. Mesuré sur un
 *  run réel : « Korea » est contenu dans « South Korea » ET dans « North Korea », et un article
 *  nord-coréen était placé sur la Corée du Sud — l'ordre d'itération du topojson tranchait un
 *  choix qu'il n'a aucun titre à trancher. Un repli qui a deux candidats n'est pas une
 *  approximation, c'est un tirage au sort : mieux vaut échouer et laisser la main au pays déduit. */
function matchLoose(name: string): CountryFeature | null {
  const key = normalize(name);
  if (key.length < 5) return null;

  let found: CountryFeature | null = null;
  for (const [n, f] of BY_NAME) {
    if (n.length >= 5 && (key.includes(n) || n.includes(key))) {
      if (found && found !== f) return null;
      found = f;
    }
  }
  return found;
}

/** Sur quoi repose le rattachement d'un item à un pays. Quatre niveaux, du plus fort au plus faible :
 *
 *  - `cited` : la source nomme le pays. Vérifié verbatim.
 *  - `deduced` : la source nomme un lieu, le modèle en déduit le pays (« Darwin » → Australie).
 *    Pas d'ancrage verbatim sur le pays, mais un lieu réel et vérifié en dessous.
 *  - `actor` : la source ne nomme aucun lieu rattachable, mais nomme le protagoniste, dont le
 *    modèle déduit le pays (« Houthis » → Yémen). Un cran sous `deduced` et pas une variante de
 *    celui-ci : les deux déduisent un pays, mais `deduced` répond « où », `actor` répond « qui ».
 *    Une frappe houthie en Mer Rouge n'a pas lieu au Yémen — la carte montre alors d'où vient
 *    l'action, pas où elle se produit, et doit le dire.
 *  - `presumed` : la source ne nomme ni lieu ni acteur rattachable ; le modèle juge sur le contenu
 *    que l'événement se situe dans le pays du média. Rien n'est nommé, seul le sujet est interprété.
 *
 *  Les quatre placent l'item sur la carte, mais n'engagent pas la même chose. Les confondre dans un
 *  total unique ferait lire une couverture présumée comme une couverture citée — la distinction
 *  disparaîtrait exactement au moment où elle compte. */
export type Provenance = "cited" | "deduced" | "actor" | "presumed";

export interface LocationMatch {
  feature: CountryFeature;
  provenance: Provenance;
}

/** Pays des sources (codes de backend/config.py) → entité du topojson, pour le rattachement
 *  présumé. "INT" est absent volontairement : une source multi-pays ou institutionnelle UE n'a
 *  pas de pays d'origine à présumer, et le backend refuse déjà le repli pour ces sources. */
const SOURCE_COUNTRY_NE: Record<string, string> = {
  US: "United States of America",
  FR: "France",
  RU: "Russia",
  CN: "China",
  DE: "Germany",
  IT: "Italy",
  GB: "United Kingdom",
  IL: "Israel",
  ES: "Spain",
  KR: "South Korea",
  IR: "Iran",
  KP: "North Korea",
};

/** Ce dont la résolution a besoin : une forme, pas le type complet, pour rester testable. */
export interface Locatable {
  location: string;
  location_country?: string;
  actor_country?: string;
  domestic_to_source?: boolean;
  country: string;
}

/** Résout un item vers un pays du topojson, du plus sûr au moins sûr.
 *
 *  1. `location` nomme exactement un pays : c'est la source qui parle, rien à déduire.
 *  2. `location` contient sans ambiguïté un nom de pays (« Northern Israel ») : la source parle
 *     encore, approximativement mais sans arbitrage.
 *  3. `location_country`, déduit par le LLM (« Darwin » → « Australia »), n'est retenu que s'il
 *     désigne exactement une entité du topojson — pas de repli approché sur ce champ, c'est le
 *     seul qui n'a aucun ancrage dans le texte, donc celui qu'on valide le plus strictement.
 *     Le vocabulaire étant fermé, un pays inventé retombe en « non rattaché » plutôt que de
 *     peindre le mauvais pays.
 *  4. `actor_country`, déduit du protagoniste (« Houthis » → « Yemen »), validé aussi strictement
 *     que `location_country`. Il intervient dans deux cas distincts : aucun lieu n'est nommé, ou
 *     un lieu est nommé mais n'appartient à aucun pays (« Strait of Hormuz »). Dans les deux, la
 *     source nomme quelqu'un — le laisser tomber perdrait une information écrite noir sur blanc.
 *     Il passe APRÈS le déduit : quand le théâtre est rattachable, c'est lui qui répond à « où ».
 *  5. À défaut de tout lieu ET de tout acteur rattachables, le pays de la source — mais seulement
 *     si le modèle a jugé l'événement domestique sur le contenu de l'article. Le pays du média ne
 *     suffit jamais seul : appliqué sans ce jugement, il ferait peindre en Russie une dépêche TASS
 *     sur le Yémen.
 *
 *  L'ordre compte : le déduit passe après l'approché pour ne pas effacer une provenance réelle,
 *  mais avant l'échec, pour rattraper les localités (« Darwin ») et les cas où l'approché refuse
 *  de trancher (« Korea »).
 *
 *  Retourne null si rien de tout cela ne s'applique — item sans lieu et non domestique, ou lieu non
 *  rattachable (haute mer, région transnationale, organisation). Ces cas sont comptés et affichés
 *  par la carte plutôt que silencieusement écartés (cf. docs/cadrage.md §11). */
export function resolveLocation(item: Locatable): LocationMatch | null {
  // Déduit de l'acteur, résolu ici parce que les deux branches ci-dessous s'en servent : sans lieu
  // du tout, et avec un lieu que rien ne rattache. Validé aussi strictement que `location_country`
  // — vocabulaire fermé du topojson, pas de repli approché.
  const byActor = item.actor_country ? matchExact(item.actor_country) : null;

  if (!item.location.trim()) {
    // Sans lieu nommé, `location_country` n'a plus rien à quoi se rattacher — le backend le vide
    // déjà, l'invariant est réaffirmé ici pour que les appelants n'aient pas à le connaître.
    // Restent l'acteur, qui ne dépend d'aucun lieu, puis le présumé.
    if (byActor) return { feature: byActor, provenance: "actor" };
    if (!item.domestic_to_source) return null;
    const origin = SOURCE_COUNTRY_NE[item.country];
    const f = origin ? BY_NAME.get(normalize(origin)) : null;
    return f ? { feature: f, provenance: "presumed" } : null;
  }

  const exact = matchExact(item.location);
  if (exact) return { feature: exact, provenance: "cited" };

  const loose = matchLoose(item.location);
  if (loose) return { feature: loose, provenance: "cited" };

  const deduced = item.location_country ? matchExact(item.location_country) : null;
  if (deduced) return { feature: deduced, provenance: "deduced" };

  // Un lieu est nommé mais n'appartient à aucun pays (« Strait of Hormuz », « Red Sea ») : le
  // backend a laissé `location_country` vide à dessein, c'est une réponse et non un manque. On ne
  // force pas ce lieu dans un pays — on rattache l'item à l'acteur, en le disant.
  return byActor ? { feature: byActor, provenance: "actor" } : null;
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
