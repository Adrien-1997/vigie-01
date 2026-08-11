"""Configuration centrale : sources de veille, plafonds, clés d'environnement."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    lang: str
    theme: str  # export_control | contrats | mouvements | diplomatie | programmes


# Sources vérifiées manuellement (feed RSS valide au 2026-08-10, cf. docs/cadrage.md §4).
SOURCES: list[Source] = [
    Source("Breaking Defense", "https://feeds.feedburner.com/breakingdefense", "en", "programmes"),
    Source("Defense News", "https://www.defensenews.com/arc/outboundfeeds/rss/", "en", "contrats"),
    Source("Opex360", "https://opex360.com/feed/", "fr", "mouvements"),
    Source("Bruxelles2", "https://bruxelles2.eu/api/rss.xml", "fr", "diplomatie"),
    Source("OFAC (US Treasury)", "https://ofac.treasury.gov/rss.xml", "en", "export_control"),
]

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")

# Garde-fous obligatoires (cf. docs/cadrage.md §7) — pas de valeur par défaut :
# une config incomplète doit échouer au démarrage plutôt que tourner sans plafond.
MAX_STEPS_PER_RUN = int(os.environ["MAX_STEPS_PER_RUN"])
MAX_LLM_CALLS_PER_DAY = int(os.environ["MAX_LLM_CALLS_PER_DAY"])
