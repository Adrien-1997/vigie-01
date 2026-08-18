import type { AnalyzedItem } from "../types";
import { publishedMs } from "../lib/filters";
import { CATEGORY_LABEL, CATEGORY_VAR } from "../lib/taxonomy";
import { ItemCard } from "./ItemCard";
import { ThreadIcon } from "./Icons";

function dayLabel(item: AnalyzedItem): string | null {
  const ms = publishedMs(item);
  if (!ms) return null;
  return new Date(ms).toLocaleDateString("fr-FR", { day: "2-digit", month: "short" });
}

function spanLabel(items: AnalyzedItem[]): string | null {
  const first = dayLabel(items[0]);
  const last = dayLabel(items[items.length - 1]);
  if (!first || !last) return null;
  return first === last ? first : `${first} → ${last}`;
}

/** Fil chronologique : plusieurs items du même dossier (V3 tranche 1, backend/agents/threader.py),
 *  déjà triés du plus ancien au plus récent par groupThreads. La pastille de catégorie affichée est
 *  celle de l'item le plus récent — chaque ItemCard nichée garde de toute façon la sienne. */
export function ThreadGroupCard({ items }: { items: AnalyzedItem[] }) {
  const lead = items[items.length - 1];
  const span = spanLabel(items);

  return (
    <section className="panel thread" style={{ ["--cat" as string]: CATEGORY_VAR[lead.category] }}>
      <header className="thread-head">
        <i className="dot" style={{ ["--dot" as string]: CATEGORY_VAR[lead.category] }} />
        <ThreadIcon />
        <span>
          Fil · {items.length} articles · {CATEGORY_LABEL[lead.category]}
        </span>
        {span && <span className="thread-span">{span}</span>}
      </header>
      <div className="thread-items">
        {items.map((item) => (
          <ItemCard key={item.link} item={item} />
        ))}
      </div>
    </section>
  );
}
