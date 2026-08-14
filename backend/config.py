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
    country: str  # code pays ISO 3166-1 alpha-2, ou "INT" pour une source multi-pays/institutionnelle UE
    state_affiliated: bool = False  # média d'État ou lié à un service officiel — cf. docs/cadrage.md §4


# Sources vérifiées manuellement (feed RSS testé en direct au 2026-08-14, cf. docs/cadrage.md §4).
# Périmètre géographique : top 10 exportateurs d'armement SIPRI (Trends in International Arms
# Transfers, mars 2025, données 2020-24) + Iran/Corée du Nord pour la couverture export_control
# (régimes sous embargo actif, absents du classement SIPRI par volume).
SOURCES: list[Source] = [
    # États-Unis (43% des exports mondiaux)
    Source("Breaking Defense", "https://feeds.feedburner.com/breakingdefense", "en", "programmes", "US"),
    Source("Defense News", "https://www.defensenews.com/arc/outboundfeeds/rss/", "en", "contrats", "US"),
    Source("OFAC (US Treasury)", "https://ofac.treasury.gov/rss.xml", "en", "export_control", "US"),
    Source(
        "Defense.gov (DoD)",
        "https://www.defense.gov/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=945",
        "en",
        "mouvements",
        "US",
    ),
    # France (9.6%)
    Source("Opex360", "https://opex360.com/feed/", "fr", "mouvements", "FR"),
    Source("Bruxelles2", "https://bruxelles2.eu/api/rss.xml", "fr", "diplomatie", "INT"),
    # Russie (7.8%, en forte baisse) — pas de presse indépendante accessible, TASS = média d'État
    Source("TASS", "https://tass.com/rss/v2.xml", "en", "mouvements", "RU", state_affiliated=True),
    # Chine (5.9%) — pas de presse indépendante accessible, CGTN = média d'État ; feed généraliste
    # Chine (pas de flux spécifique défense trouvé), taux de hors_perimetre attendu plus élevé
    Source(
        "CGTN (Chine, généraliste)",
        "https://www.cgtn.com/subscribe/rss/section/china.xml",
        "en",
        "mouvements",
        "CN",
        state_affiliated=True,
    ),
    # Allemagne (5.6%)
    Source("Hartpunkt", "https://www.hartpunkt.de/feed/", "de", "programmes", "DE"),
    Source("ESUT", "https://esut.de/feed/", "de", "mouvements", "DE"),
    # Italie (4.8%, +138% — plus forte croissance du top 10)
    Source("Analisi Difesa", "https://www.analisidifesa.it/feed/", "it", "programmes", "IT"),
    # Royaume-Uni (3.6%)
    Source("UK Defence Journal", "https://ukdefencejournal.org.uk/feed/", "en", "programmes", "GB"),
    # Israël (3.1%) — pas de flux SIBAT/MOD trouvé, presse généraliste filtrée en aval par le LLM
    Source(
        "Jerusalem Post (généraliste)",
        "https://www.jpost.com/rss/rssfeedsfrontpage.aspx",
        "en",
        "diplomatie",
        "IL",
    ),
    # Espagne (3.0%, +29%)
    Source("Infodefensa", "https://www.infodefensa.com/feed/all", "es", "contrats", "ES"),
    # Corée du Sud (2.2%) — pas de flux DAPA trouvé, dépêches Yonhap généralistes filtrées en aval
    Source("Yonhap (généraliste)", "https://en.yna.co.kr/RSS/national.xml", "en", "mouvements", "KR"),
    # Iran — hors top 10 SIPRI (0.4%, +749% quasi exclusivement vers la Russie), couverture
    # export_control ; Mehr News est un média semi-officiel (gouvernemental)
    Source(
        "Mehr News (Iran)",
        "https://en.mehrnews.com/rss",
        "en",
        "export_control",
        "IR",
        state_affiliated=True,
    ),
    # Corée du Nord — hors classement SIPRI, transferts sous embargo vers la Russie ; NK News agrège
    # les médias d'État nord-coréens (KCNA), seule source practicable identifiée
    Source(
        "NK News",
        "https://www.nknews.org/feed/",
        "en",
        "export_control",
        "KP",
        state_affiliated=True,
    ),
]

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")

# Fenêtre de fraîcheur appliquée à la collecte (backend/agents/collector.py) : au-delà de cette
# ancienneté, un item est écarté avant même le dédoublonnage. Certains flux institutionnels
# (Defense.gov, Bruxelles2, NK News) exposent un historique profond (des mois, voire années) sans
# pagination par date — sans ce filtre, un premier run (ou un run après une coupure) soumettrait
# tout l'historique au budget LLM quotidien d'un coup. Item sans date publiée/parsable : conservé
# par prudence, le garde-fou MAX_LLM_CALLS_PER_DAY reste le filet de sécurité final.
COLLECTION_LOOKBACK_HOURS = 48

# Garde-fous obligatoires (cf. docs/cadrage.md §7) — pas de valeur par défaut :
# une config incomplète doit échouer au démarrage plutôt que tourner sans plafond.
MAX_STEPS_PER_RUN = int(os.environ["MAX_STEPS_PER_RUN"])
MAX_LLM_CALLS_PER_DAY = int(os.environ["MAX_LLM_CALLS_PER_DAY"])
