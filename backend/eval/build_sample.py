"""Construit un échantillon pour mesurer la précision de classification (cf. docs/cadrage.md §7).

Usage : python -m backend.eval.build_sample [--per-source N]
Puis  : python -m backend.eval.annotate
Puis  : python -m backend.eval.score
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

from backend.agents.analyst import _clean_text, classify_item
from backend.agents.collector import collect

SAMPLE_FILE = Path(__file__).parent / "sample.json"


def main(per_source: int) -> None:
    raw = collect({})["raw_items"]

    by_source: dict[str, list] = defaultdict(list)
    for item in raw:
        by_source[item["source"]].append(item)

    selected = [item for items in by_source.values() for item in items[:per_source]]
    print(f"Échantillon : {len(selected)} items ({per_source} max par source, {len(by_source)} sources)")

    rows = []
    for i, item in enumerate(selected):
        result = classify_item(item)
        rows.append(
            {
                "id": i,
                "source": item["source"],
                "title": item["title"],
                "text_excerpt": _clean_text(item["raw_text"])[:500],
                "link": item["link"],
                "category_system": result.category,
                "citation": result.citation,
                "category_gold": None,
            }
        )
        print(f"  [{i}] {item['source']} — {result.category} — {item['title'][:70]}")

    SAMPLE_FILE.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nÉcrit dans {SAMPLE_FILE}.")
    print("Prochaine étape (dans un terminal interactif) : python -m backend.eval.annotate")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-source", type=int, default=6)
    args = parser.parse_args()
    main(args.per_source)
