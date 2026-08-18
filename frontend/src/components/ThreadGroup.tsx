import { useState } from "react";
import type { AnalyzedItem } from "../types";
import { publishedMs } from "../lib/filters";
import { CATEGORY_LABEL, CATEGORY_VAR } from "../lib/taxonomy";
import { ItemCard } from "./ItemCard";
import { ThreadIcon, CheckIcon, AlertIcon } from "./Icons";
import { confidenceColor } from "../lib/confidence";

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

function chipTitle(item: AnalyzedItem): string {
  const parts = [item.source];
  const day = dayLabel(item);
  if (day) parts.push(day);
  parts.push(item.confidence_score !== null ? `confiance ${item.confidence_score.toFixed(2)}` : "non vérifié");
  if (item.corroborated === true) parts.push("recoupé");
  if (item.corroborated === false) parts.push("source unique");
  if (item.state_affiliated) parts.push("média d'État");
  return parts.join(" · ");
}

/** Fil chronologique : plusieurs items du même dossier (V3 tranche 1, backend/agents/threader.py),
 *  déjà triés du plus ancien au plus récent par groupThreads. Une seule carte est affichée à la
 *  fois (la plus récente par défaut) ; la frise en dessous laisse choisir quel article du fil
 *  prend sa place, plutôt que d'empiler N cartes complètes — le signal qui manquait n'était pas
 *  plus de cartes, c'était la confiance/le recoupement de chaque source visibles d'un coup d'œil. */
export function ThreadGroupCard({ items }: { items: AnalyzedItem[] }) {
  const [selected, setSelected] = useState(items.length - 1);
  const shown = items[selected] ?? items[items.length - 1];
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

      <ItemCard item={shown} />

      <ol className="thread-rail">
        {items.map((item, i) => (
          <li key={item.link} className="thread-step">
            <button
              type="button"
              className="thread-chip"
              aria-pressed={i === selected}
              title={chipTitle(item)}
              onClick={() => setSelected(i)}
            >
              <i className="thread-chip-dot" style={{ ["--dot" as string]: confidenceColor(item.confidence_score) }} />
              {item.state_affiliated && (
                <span className="thread-chip-warn">
                  <AlertIcon />
                </span>
              )}
              <span className="thread-chip-source">{item.source}</span>
              <span className="thread-chip-date">{dayLabel(item)}</span>
              {item.corroborated === true && (
                <span className="thread-chip-good">
                  <CheckIcon />
                </span>
              )}
            </button>
          </li>
        ))}
      </ol>
    </section>
  );
}
