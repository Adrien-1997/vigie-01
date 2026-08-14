import { useMemo, useState } from "react";
import { geoNaturalEarth1, geoPath } from "d3-geo";
import type { AnalyzedItem, Category } from "../types";
import { COUNTRIES, countryKey, countryLabel, resolveLocation, type CountryFeature } from "../lib/geo";
import { CATEGORY_LABEL, CATEGORY_VAR } from "../lib/taxonomy";

const W = 960;
const H = 460;
const STEPS = ["var(--seq-250)", "var(--seq-400)", "var(--seq-550)", "var(--seq-700)"];

// L'Antarctique n'accueille aucun item du périmètre et occupe le tiers bas du cadre.
const DRAWN = COUNTRIES.filter((f) => f.properties.name !== "Antarctica");

const projection = geoNaturalEarth1().fitSize([W, H], { type: "FeatureCollection", features: DRAWN } as never);
const path = geoPath(projection);

const PATHS: { feature: CountryFeature; d: string }[] = DRAWN.map((feature) => ({
  feature,
  d: path(feature) ?? "",
})).filter((p) => p.d !== "");

interface Bucket {
  total: number;
  /** Part du total rattachée au pays par déduction et non par citation (cf. lib/geo.ts). */
  inferred: number;
  byCategory: Map<Category, number>;
  name: string;
}

interface Props {
  items: AnalyzedItem[];
  selected: string | null;
  onSelect: (id: string | null) => void;
}

export function WorldMap({ items, selected, onSelect }: Props) {
  const [hover, setHover] = useState<{ id: string; x: number; y: number } | null>(null);

  const { byCountry, unlocated, unresolved, inferred, max } = useMemo(() => {
    const byCountry = new Map<string, Bucket>();
    let unlocated = 0;
    let unresolved = 0;
    let inferred = 0;

    for (const item of items) {
      if (!item.location.trim()) {
        unlocated += 1;
        continue;
      }
      const match = resolveLocation(item.location, item.location_country);
      if (!match) {
        unresolved += 1;
        continue;
      }
      const key = countryKey(match.feature);
      let bucket = byCountry.get(key);
      if (!bucket) {
        bucket = { total: 0, inferred: 0, byCategory: new Map(), name: countryLabel(match.feature) };
        byCountry.set(key, bucket);
      }
      bucket.total += 1;
      if (match.inferred) {
        bucket.inferred += 1;
        inferred += 1;
      }
      bucket.byCategory.set(item.category, (bucket.byCategory.get(item.category) ?? 0) + 1);
    }

    const max = Math.max(0, ...[...byCountry.values()].map((b) => b.total));
    return { byCountry, unlocated, unresolved, inferred, max };
  }, [items]);

  // Autant de paliers que de valeurs distinctes possibles, plafonné à la rampe : sur un digest
  // où aucun pays ne dépasse un item, une rampe à quatre paliers ferait croire à une gradation
  // qui n'existe pas. Les paliers retenus sont les plus foncés, pour que le maximum réel soit
  // toujours l'extrémité de la rampe.
  const { steps, thresholds } = useMemo(() => {
    const count = Math.min(STEPS.length, Math.max(1, max));
    const steps = STEPS.slice(STEPS.length - count);
    return { steps, thresholds: steps.map((_, i) => Math.ceil((max * (i + 1)) / count)) };
  }, [max]);

  const stepFor = (total: number) => steps[thresholds.findIndex((t) => total <= t)] ?? steps[steps.length - 1];

  const hovered = hover ? byCountry.get(hover.id) : null;

  return (
    <div className="panel panel-pad">
      <div className="panel-head">
        <h2 className="panel-title">Couverture géographique · lieu de l'événement</h2>
        {selected && (
          <button className="link-btn" onClick={() => onSelect(null)}>
            retirer le filtre
          </button>
        )}
      </div>

      <div className="map-wrap" onMouseLeave={() => setHover(null)}>
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Carte du nombre d'items par pays">
          {PATHS.map(({ feature, d }) => {
            const key = countryKey(feature);
            const bucket = byCountry.get(key);
            const isSelected = selected === key;
            return (
              <path
                key={key}
                d={d}
                className={[
                  "map-country",
                  bucket ? "has-data" : "",
                  selected && !isSelected ? "dim" : "",
                  isSelected ? "active" : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
                style={bucket ? { fill: stepFor(bucket.total) } : undefined}
                onMouseMove={(e) => {
                  if (!bucket) return setHover(null);
                  const box = e.currentTarget.ownerSVGElement!.getBoundingClientRect();
                  setHover({ id: feature.id, x: e.clientX - box.left, y: e.clientY - box.top });
                }}
                onClick={() => bucket && onSelect(isSelected ? null : key)}
              >
                {bucket && (
                  <title>
                    {bucket.name} — {bucket.total} item{bucket.total > 1 ? "s" : ""}
                    {bucket.inferred > 0 && `, dont ${bucket.inferred} rattaché${bucket.inferred > 1 ? "s" : ""} par déduction`}
                  </title>
                )}
              </path>
            );
          })}
        </svg>

        {hover && hovered && (
          <div
            className="map-tooltip map-tooltip-body"
            style={{
              left: Math.min(hover.x + 14, 640),
              top: hover.y + 14,
            }}
          >
            <strong>{hovered.name}</strong>
            {hovered.inferred > 0 && (
              <span className="tooltip-note">
                {hovered.inferred}/{hovered.total} rattaché{hovered.inferred > 1 ? "s" : ""} par déduction
              </span>
            )}
            <ul>
              {[...hovered.byCategory.entries()]
                .sort((a, b) => b[1] - a[1])
                .map(([category, n]) => (
                  <li key={category}>
                    <i className="dot" style={{ ["--dot" as string]: CATEGORY_VAR[category] }} />
                    {CATEGORY_LABEL[category]}
                    <span className="count">{n}</span>
                  </li>
                ))}
            </ul>
          </div>
        )}
      </div>

      <div className="map-legend">
        {max > 0 && (
          <span className="ramp">
            <span className="swatches">
              {steps.map((step, i) => (
                <i key={step} style={{ background: step }} title={`jusqu'à ${thresholds[i]} item(s)`} />
              ))}
            </span>
            <span>{max === 1 ? "1 item par pays" : `1 à ${max} items par pays`}</span>
          </span>
        )}
        <span>
          {unlocated} sans lieu extrait
        </span>
        <span>
          {unresolved} lieu{unresolved > 1 ? "x" : ""} non rattaché{unresolved > 1 ? "s" : ""} à un pays
        </span>
        {inferred > 0 && (
          <span>
            {inferred} rattaché{inferred > 1 ? "s" : ""} par déduction
          </span>
        )}
      </div>

      <p className="note" style={{ marginTop: 8 }}>
        Carte construite sur le champ <code>location</code> vérifié par item, pas sur le pays de la source.
        Un lieu absent du texte source ressort vide : la couverture réelle est sous-estimée
        (docs/cadrage.md §11). Une localité (« Darwin ») est rattachée à son pays par déduction du
        modèle, pas par citation de la source : ces items sont comptés à part ci-dessus et signalés
        au survol du pays.
      </p>
    </div>
  );
}
