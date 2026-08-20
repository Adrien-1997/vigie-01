import { useMemo } from "react";
import type { AnalyzedItem } from "../types";
import { countryKey, resolveLocation, sourceCountryLabel, type Provenance } from "../lib/geo";
import { unplacedReasons } from "../lib/coverage";
import type { ThreadModel } from "../lib/threads";
import { AlertIcon } from "./Icons";

/** Hauteur fixe, dictée par le texte : chaque article tirant son propre trait, c'est le nombre de
 *  traits qui porte la quantité, pas la taille du bloc. */
const BLOCK_H = 54;
const GAP = 10;
/** Retrait des ancrages aux bords du bloc, pour qu'un trait ne parte jamais de l'arête. */
const ANCHOR_PAD = 7;
const UNPLACED = "__unplaced";

/** Le niveau de provenance est porté par la forme du trait, jamais par la seule couleur : la
 *  distinction doit survivre à un daltonisme comme à une impression en noir et blanc. Motifs
 *  calibrés pour un trait épais à bouts ronds — le « pointillé » est un tiret de longueur nulle que
 *  le bout rond arrondit. Les mêmes valeurs servent au trait et à son échantillon de légende. */
const DASH: Record<Provenance, string | undefined> = {
  cited: undefined,
  deduced: "10 8",
  actor: "3 5",
  presumed: "0.01 9",
};

const PROVENANCE_LABEL: Record<Provenance, string> = {
  cited: "cité",
  deduced: "déduit",
  actor: "acteur",
  presumed: "présumé",
};

const PROVENANCE_HINT: Record<Provenance, string> = {
  cited: "le pays est nommé par la source, vérifié verbatim",
  deduced: "pays déduit par le modèle d'une localité nommée (« Darwin » → Australie)",
  actor:
    "aucun lieu rattachable : pays déduit du protagoniste nommé (« Houthis » → Yémen). " +
    "Dit d'où vient l'action, pas où elle se produit",
  presumed: "aucun lieu nommé : événement jugé domestique au média sur le contenu de l'article",
};

interface Block {
  key: string;
  label: string;
  count: number;
  detail: string;
  stateAffiliated?: number;
  y: number;
}

interface Strand {
  item: AnalyzedItem;
  from: string;
  to: string;
  provenance: Provenance | null;
  leftIndex: number;
  rightIndex: number;
  leftSlot: number;
  leftOf: number;
  rightSlot: number;
  rightOf: number;
}

const plural = (n: number, word: string) => `${n} ${word}${n > 1 ? "s" : ""}`;

/** Position verticale d'un trait dans son bloc : réparti régulièrement, jamais collé aux arêtes. */
const anchor = (blockY: number, slot: number, of: number) =>
  blockY + ANCHOR_PAD + ((BLOCK_H - 2 * ANCHOR_PAD) * (slot + 0.5)) / of;

/** Répartit les traits d'un même bloc dans l'ordre du bloc opposé, pour limiter les croisements
 *  gratuits : un croisement doit signifier un rattachement qui traverse, pas un artefact de tri. */
function assignSlots(strands: Strand[], side: "left" | "right") {
  const groups = new Map<string, Strand[]>();
  for (const s of strands) {
    const key = side === "left" ? s.from : s.to;
    const group = groups.get(key);
    if (group) group.push(s);
    else groups.set(key, [s]);
  }
  for (const group of groups.values()) {
    group.sort((a, b) =>
      side === "left" ? a.rightIndex - b.rightIndex : a.leftIndex - b.leftIndex,
    );
    group.forEach((s, i) => {
      if (side === "left") {
        s.leftSlot = i;
        s.leftOf = group.length;
      } else {
        s.rightSlot = i;
        s.rightOf = group.length;
      }
    });
  }
}

/** Croisement « qui raconte » × « où se passe l'événement ».
 *
 *  Deux dimensions distinctes que l'interface ne doit jamais confondre : à gauche le pays du média,
 *  à droite le pays de l'événement tel que `resolveLocation` le résout. Le pays d'un média ne
 *  rattache pas à lui seul un article — sans quoi une dépêche TASS sur le Yémen se lirait comme une
 *  actualité russe (cf. lib/geo.ts, docs/cadrage.md §11). C'est l'écart entre les deux colonnes qui
 *  porte l'information : un thread couvert par une agence d'État étrangère ne se lit pas comme une
 *  couverture domestique.
 *
 *  Un trait par article, plutôt qu'un ruban épais par flux : la quantité se compte au lieu de se
 *  jauger, chaque trait reste rattachable à son article au survol, et le niveau de provenance se
 *  lit sur le trait lui-même. */
export function ThreadProvenance({ thread }: { thread: ThreadModel }) {
  const { left, right, strands, height } = useMemo(() => {
    const leftBlocks: Block[] = [...thread.sourceCountries.entries()]
      .sort((a, b) => b[1].count - a[1].count)
      .map(([code, bucket]) => ({
        key: code,
        label: sourceCountryLabel(code),
        count: bucket.count,
        stateAffiliated: bucket.stateAffiliated,
        detail:
          bucket.stateAffiliated === 0
            ? plural(bucket.count, "article")
            : bucket.stateAffiliated === bucket.count
              ? `${plural(bucket.count, "article")} · média d'État`
              : `${plural(bucket.count, "article")} · dont ${bucket.stateAffiliated} d'État`,
        y: 0,
      }));

    const rightBlocks: Block[] = [...thread.coverage.byCountry.entries()]
      .sort((a, b) => b[1].total - a[1].total)
      .map(([key, bucket]) => {
        const cited = bucket.total - bucket.deduced - bucket.actor - bucket.presumed;
        // Le décompte d'abord, comme dans la colonne des médias, pour que les deux se comparent.
        const parts: string[] = [plural(bucket.total, "article")];
        if (cited > 0) parts.push(`${cited} cité${cited > 1 ? "s" : ""}`);
        if (bucket.deduced > 0) parts.push(`${bucket.deduced} déduit${bucket.deduced > 1 ? "s" : ""}`);
        if (bucket.actor > 0) parts.push(`${bucket.actor} par l'acteur`);
        if (bucket.presumed > 0) parts.push(`${bucket.presumed} présumé${bucket.presumed > 1 ? "s" : ""}`);
        return { key, label: bucket.name, count: bucket.total, detail: parts.join(" · "), y: 0 };
      });

    const unplacedCount = thread.coverage.unlocated + thread.coverage.unresolved;
    if (unplacedCount > 0) {
      rightBlocks.push({
        key: UNPLACED,
        label: "Non rattaché",
        count: unplacedCount,
        detail: unplacedReasons(thread.coverage).join(" · "),
        y: 0,
      });
    }

    const span = (n: number) => Math.max(0, n * (BLOCK_H + GAP) - GAP);
    const total = Math.max(span(leftBlocks.length), span(rightBlocks.length), BLOCK_H);
    // Colonnes centrées l'une par rapport à l'autre : alignées en haut, deux colonnes de hauteurs
    // différentes feraient partir tous les traits en biais vers le bas.
    const place = (blocks: Block[]) => {
      const offset = (total - span(blocks.length)) / 2;
      blocks.forEach((b, i) => {
        b.y = offset + i * (BLOCK_H + GAP);
      });
    };
    place(leftBlocks);
    place(rightBlocks);

    const drawn: Strand[] = thread.items.map((item) => {
      const match = resolveLocation(item);
      const to = match ? countryKey(match.feature) : UNPLACED;
      return {
        item,
        from: item.country,
        to,
        provenance: match ? match.provenance : null,
        leftIndex: leftBlocks.findIndex((b) => b.key === item.country),
        rightIndex: rightBlocks.findIndex((b) => b.key === to),
        leftSlot: 0,
        leftOf: 1,
        rightSlot: 0,
        rightOf: 1,
      };
    });
    assignSlots(drawn, "left");
    assignSlots(drawn, "right");

    return { left: leftBlocks, right: rightBlocks, strands: drawn, height: total };
  }, [thread]);

  const { placed, deduced, actor, presumed } = thread.coverage;
  const counts: Record<Provenance, number> = {
    cited: placed - deduced - actor - presumed,
    deduced,
    actor,
    presumed,
  };

  return (
    <div className="pv-wrap">
      <div className="pv" style={{ height }}>
        <div className="pv-col">
          <span className="pv-head">Médias</span>
          {left.map((b) => (
            <div
              key={b.key}
              className="pv-block pv-block-left"
              style={{ top: b.y, height: BLOCK_H }}
              title={`${b.label} — ${b.detail}`}
            >
              <strong>
                {b.stateAffiliated ? (
                  <i className="pv-state" aria-label="Média d'État">
                    <AlertIcon />
                  </i>
                ) : null}
                {b.label}
              </strong>
              <span>{b.detail}</span>
            </div>
          ))}
        </div>

        <svg
          className="pv-flow"
          viewBox={`0 0 100 ${height}`}
          height={height}
          preserveAspectRatio="none"
          role="img"
          aria-label="Rattachement de chaque article au lieu de son événement"
        >
          {strands.map((s) => {
            const y0 = anchor(left[s.leftIndex].y, s.leftSlot, s.leftOf);
            const y1 = anchor(right[s.rightIndex].y, s.rightSlot, s.rightOf);
            return (
              <path
                key={s.item.link}
                className={`pv-strand${s.to === UNPLACED ? " pv-strand-unplaced" : ""}`}
                /* Points de contrôle croisés (58 puis 42) plutôt que tous deux au milieu : le trait
                   quitte et rejoint ses blocs à plat, toute la courbure se concentrant dans une
                   inflexion centrale nette. */
                d={`M 0 ${y0} C 58 ${y0}, 42 ${y1}, 100 ${y1}`}
                strokeDasharray={s.provenance ? DASH[s.provenance] : "1.5 3.5"}
                vectorEffect="non-scaling-stroke"
              >
                <title>
                  {s.item.source} → {right[s.rightIndex].label}
                  {s.provenance
                    ? ` (${PROVENANCE_LABEL[s.provenance]}${s.item.location ? ` · « ${s.item.location} »` : ""})`
                    : " · lieu non rattachable"}
                </title>
              </path>
            );
          })}
        </svg>

        <div className="pv-col">
          <span className="pv-head">Lieu de l'événement</span>
          {right.map((b) => (
            <div
              key={b.key}
              className={`pv-block pv-block-right${b.key === UNPLACED ? " pv-block-unplaced" : ""}`}
              style={{ top: b.y, height: BLOCK_H }}
              title={`${b.label} — ${b.detail}`}
            >
              <strong>{b.label}</strong>
              <span>{b.detail}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Les trois niveaux sont toujours affichés, y compris à zéro : un niveau masqué parce que
          vide se lirait comme un niveau inexistant. */}
      <ul className="pv-key">
        {(Object.keys(PROVENANCE_LABEL) as Provenance[]).map((p) => (
          <li key={p}>
            <svg className="pv-sample" width="36" height="10" aria-hidden="true">
              <line x1="2" y1="5" x2="34" y2="5" strokeDasharray={DASH[p]} />
            </svg>
            <b>{PROVENANCE_LABEL[p]}</b>
            <span className="pv-count">{counts[p]}</span>
            <span className="pv-hint">{PROVENANCE_HINT[p]}</span>
          </li>
        ))}
      </ul>

      <p className="note pv-note">
        Un trait par article : à gauche le pays du <strong>média</strong>, à droite celui de
        l'<strong>événement</strong>, résolu article par article sur le champ <code>location</code> —
        jamais sur l'origine du média, qui ne rattache rien à elle seule. Les trois niveaux ne sont
        jamais additionnés, et ce qui n'est pas plaçable est affiché plutôt qu'écarté
        (docs/cadrage.md §11).
      </p>
    </div>
  );
}
