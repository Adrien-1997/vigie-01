import type { AnalyzedItem } from "../types";
import { CATEGORY_LABEL, CATEGORY_VAR, LANG_LABEL } from "../lib/taxonomy";
import { sourceCountryLabel } from "../lib/geo";
import { ConfidenceGauge } from "./ConfidenceGauge";
import { AlertIcon, CheckIcon, PinIcon } from "./Icons";

function formatDate(published: string): string | null {
  const d = new Date(published);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

export function ItemCard({ item }: { item: AnalyzedItem }) {
  const date = formatDate(item.published);

  return (
    <article className="card" style={{ ["--cat" as string]: CATEGORY_VAR[item.category] }}>
      <div className="card-top">
        <span className="badge">
          <i className="dot" style={{ ["--dot" as string]: CATEGORY_VAR[item.category] }} />
          {CATEGORY_LABEL[item.category]}
        </span>

        <ConfidenceGauge score={item.confidence_score} category={item.category} />

        {item.corroborated === true && (
          <span className="badge good" title="Au moins un item de l'historique traite du même dossier.">
            <CheckIcon />
            Recoupé
          </span>
        )}
        {item.corroborated === false && (
          <span
            className="badge quiet"
            title="Aucun item corroborant trouvé dans l'historique (30 jours glissants). Un signal isolé n'est pas pour autant faux — c'est précisément ce que la veille cherche à détecter."
          >
            Source unique
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
        {item.location && (
          <>
            <span className="sep">·</span>
            <span>
              <PinIcon /> {item.location}
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
