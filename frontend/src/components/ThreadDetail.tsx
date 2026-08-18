import { useState } from "react";
import { CATEGORY_LABEL, CATEGORY_VAR } from "../lib/taxonomy";
import { formatDuration, type ThreadModel } from "../lib/threads";
import { ItemCard } from "./ItemCard";
import { ThreadTimeline } from "./ThreadTimeline";
import { ThreadProvenance } from "./ThreadProvenance";
import { AlertIcon, CheckIcon, ThreadIcon } from "./Icons";

/** Vue déployée d'un fil : la chronologie et la provenance passent devant l'article, qui devient
 *  le détail qu'on consulte après avoir lu la forme du dossier — l'inverse de la carte d'article,
 *  où le fil n'était qu'une décoration.
 *
 *  Aucun indicateur agrégé de fiabilité n'est calculé ici. Les compteurs de vérification disent
 *  combien d'articles ont été escaladés et ce qu'il est advenu des autres, en distinguant « pas
 *  escaladé faute de budget » de « hors du périmètre du vérificateur » : ce sont deux silences
 *  différents, et aucun des deux ne vaut un score. */
export function ThreadDetail({ thread }: { thread: ThreadModel }) {
  const [selected, setSelected] = useState(thread.items.length - 1);
  const shown = thread.items[selected] ?? thread.lead;
  const countries = thread.coverage.byCountry.size;

  return (
    <section className="panel thread-detail" style={{ ["--cat" as string]: CATEGORY_VAR[thread.category] }}>
      <header className="td-head">
        <span className="badge">
          <i className="dot" style={{ ["--dot" as string]: CATEGORY_VAR[thread.category] }} />
          {CATEGORY_LABEL[thread.category]}
        </span>
        <span className="td-kind">
          <ThreadIcon />
          Fil d'événements
        </span>
      </header>

      <h2 className="td-title">{thread.lead.title_fr}</h2>

      <p className="td-meta">
        <span>
          {thread.items.length} article{thread.items.length > 1 ? "s" : ""}
        </span>
        <span className="sep">·</span>
        <span>
          {thread.sources.length} source{thread.sources.length > 1 ? "s" : ""} ({thread.sources.join(", ")})
        </span>
        {countries > 0 && (
          <>
            <span className="sep">·</span>
            <span>
              {countries} pays d'événement
            </span>
          </>
        )}
        {thread.spanMs > 0 && (
          <>
            <span className="sep">·</span>
            <span>sur {formatDuration(thread.spanMs)}</span>
          </>
        )}
      </p>

      <div className="td-flags">
        {/* « Antécédent dans l'historique » plutôt que « recoupé » : le champ mesure ce que la base
            contenait au moment où l'article est passé au vérificateur, pas un recoupement entre les
            articles du fil — que le vérificateur ne fait jamais, `exclude_links` portant tout le lot
            en cours. Dit « recoupé » à côté d'un fil de trois sources, il se lisait comme une
            contradiction (cf. backend/memory/store.py:155). */}
        {thread.corroborated > 0 && (
          <span className="badge good" title="Le vérificateur a trouvé, dans l'historique des runs précédents, au moins un article traitant du même dossier.">
            <CheckIcon />
            {thread.corroborated} avec antécédent
          </span>
        )}
        {thread.singleSource > 0 && (
          <span className="badge quiet" title="Escaladés au vérificateur, sans article antérieur trouvé sur le même dossier. Le recoupement ne voit jamais les items du run en cours : deux articles collectés dans le même lot ne peuvent pas se corroborer l'un l'autre, même s'ils traitent visiblement du même sujet.">
            {thread.singleSource} sans antécédent à la collecte
          </span>
        )}
        {thread.unscoredInScope > 0 && (
          <span className="badge quiet" title="Catégorie couverte par le vérificateur, mais le plafond d'escalade du run a été atteint avant ces articles. Absence de mesure, pas mesure d'absence.">
            {thread.unscoredInScope} non vérifié{thread.unscoredInScope > 1 ? "s" : ""}
          </span>
        )}
        {thread.unscoredOutOfScope > 0 && (
          <span className="badge quiet" title="Catégorie hors du périmètre du vérificateur (VERIFIER_CATEGORIES) : ces articles ne sont pas censés porter de score.">
            {thread.unscoredOutOfScope} hors périmètre de vérification
          </span>
        )}
        {thread.breaker.state_affiliated && (
          <span className="badge warn" title="Le premier article paru du fil émane d'un média d'État ou d'une agence semi-officielle : la primeur est une revendication, pas un fait établi.">
            <AlertIcon />
            Primeur d'un média d'État
          </span>
        )}
      </div>

      <div className="td-block">
        <h3 className="panel-title">Chronologie</h3>
        <ThreadTimeline thread={thread} selected={selected} onSelect={setSelected} />
      </div>

      <div className="td-block">
        <h3 className="panel-title">Provenance</h3>
        <ThreadProvenance thread={thread} />
      </div>

      <div className="td-block">
        <h3 className="panel-title">
          Article sélectionné · {selected + 1} sur {thread.items.length}
        </h3>
        <ItemCard item={shown} />
      </div>
    </section>
  );
}
