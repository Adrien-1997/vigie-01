import type { AnalyzedItem } from "../types";
import { CATEGORY_LABEL, CATEGORY_VAR, LANG_LABEL } from "../lib/taxonomy";
import { countryLabel, resolveLocation, sourceCountryLabel } from "../lib/geo";
import { ConfidenceGauge } from "./ConfidenceGauge";
import { AlertIcon, CheckIcon, PinIcon } from "./Icons";

function formatDate(published: string): string | null {
  const d = new Date(published);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

export function ItemCard({ item }: { item: AnalyzedItem }) {
  const date = formatDate(item.published);

  // Le pays en français plutôt que l'extrait brut, qui ressort dans la langue de la source
  // (« Großbritannien ») ; l'extrait reste consultable en infobulle. Un lieu non rattachable à un
  // pays n'a pas d'équivalent français : il s'affiche tel quel.
  const match = resolveLocation(item);
  const place = match ? countryLabel(match.feature) : item.location;
  const placeTitle = match && place !== item.location.trim() ? `Lieu extrait de la source : ${item.location}` : undefined;

  return (
    <article className="card" style={{ ["--cat" as string]: CATEGORY_VAR[item.category] }}>
      <div className="card-top">
        <span className="badge">
          <i className="dot" style={{ ["--dot" as string]: CATEGORY_VAR[item.category] }} />
          {CATEGORY_LABEL[item.category]}
        </span>

        <ConfidenceGauge item={item} />

        {/* « Antécédent » et non « recoupé » : le vérificateur ne recoupe jamais entre eux les
            articles affichés, `exclude_links` excluant tout le lot en cours. */}
        {item.corroborated === true && (
          <span className="badge good" title="Au moins un article antérieur de l'historique traite du même dossier.">
            <CheckIcon />
            Avec antécédent
          </span>
        )}
        {item.corroborated === false && (
          <span
            className="badge quiet"
            title="Aucun article antérieur trouvé sur ce dossier dans l'historique (7 jours glissants), et les items du même lot de collecte ne comptent pas. Un signal isolé n'est pas pour autant faux — c'est précisément ce que la veille cherche à détecter."
          >
            Sans antécédent
          </span>
        )}

        {item.state_affiliated && (
          <span
            className="badge warn"
            title="Média d'État ou d'agence semi-officielle : à lire comme une revendication, pas comme un fait établi (docs/cadrage.md §4, §11)."
          >
            <AlertIcon />
            Média d'État
          </span>
        )}
      </div>

      <h3>
        <a href={item.link} target="_blank" rel="noopener noreferrer">
          {item.title_fr}
        </a>
      </h3>

      <p className="summary">{item.summary}</p>

      {item.citation && (
        <blockquote className="citation">
          <span className="citation-tag">
            Citation vérifiée · {(LANG_LABEL[item.lang] ?? item.lang).toLowerCase()} d'origine
          </span>
          {item.citation}
        </blockquote>
      )}

      <footer className="card-foot">
        <span>{item.source}</span>
        <span className="sep">·</span>
        <span>{sourceCountryLabel(item.country)}</span>
        {place && (
          <>
            <span className="sep">·</span>
            <span title={placeTitle}>
              <PinIcon /> {place}
            </span>
          </>
        )}
        {date && (
          <>
            <span className="sep">·</span>
            <span>{date}</span>
          </>
        )}
        <a href={item.link} target="_blank" rel="noopener noreferrer">
          Source originale ↗
        </a>
      </footer>
    </article>
  );
}
