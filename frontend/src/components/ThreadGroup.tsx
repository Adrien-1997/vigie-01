import { useMemo, useState } from "react";
import type { AnalyzedItem } from "../types";
import { CATEGORY_LABEL, CATEGORY_VAR } from "../lib/taxonomy";
import { buildThread, formatDuration } from "../lib/threads";
import { ItemCard } from "./ItemCard";
import { ThreadTimeline } from "./ThreadTimeline";
import { ThreadIcon } from "./Icons";

/** Fil chronologique dans le flux de lecture (V3 tranche 1, backend/agents/threader.py).
 *
 *  Le rail de pastilles équidistantes qui tenait ce rôle disait bien *qui* composait le fil, mais
 *  écrasait le *quand* : trois dépêches en vingt minutes et trois dépêches en trois semaines s'y
 *  affichaient à l'identique. La frise proportionnelle le corrige ici sous forme resserrée ;
 *  l'onglet Fils en donne la lecture complète, provenance comprise. */
export function ThreadGroupCard({ items, onOpen }: { items: AnalyzedItem[]; onOpen?: () => void }) {
  const thread = useMemo(() => buildThread(items), [items]);
  const [selected, setSelected] = useState(thread.items.length - 1);
  const shown = thread.items[selected] ?? thread.lead;

  return (
    <section className="panel thread" style={{ ["--cat" as string]: CATEGORY_VAR[thread.category] }}>
      <header className="thread-head">
        <i className="dot" style={{ ["--dot" as string]: CATEGORY_VAR[thread.category] }} />
        <ThreadIcon />
        <span>
          Fil · {thread.items.length} articles · {CATEGORY_LABEL[thread.category]}
        </span>
        {thread.spanMs > 0 && <span className="thread-span">sur {formatDuration(thread.spanMs)}</span>}
      </header>

      <ItemCard item={shown} />

      <ThreadTimeline thread={thread} selected={selected} onSelect={setSelected} compact />

      {onOpen && (
        <button type="button" className="link-btn thread-open" onClick={onOpen}>
          Ouvrir le fil — chronologie et provenance →
        </button>
      )}
    </section>
  );
}
