# VEILLE-01 — Agent de veille export & risque défense/géopolitique

Agent IA autonome qui collecte, classe, recoupe et synthétise quotidiennement des sources ouvertes sur un périmètre défense/géopolitique restreint.

## Cadrage

**Client (hypothèse)** : un grand groupe défense dont les équipes suivent aujourd'hui le risque export et géopolitique à la main, de façon lente et non homogène.

**Valeur** : diviser le temps de synthèse quotidienne, standardiser la lecture des signaux faibles, tracer la fiabilité de chaque information remontée.

**Périmètre V1** : export control, contrats d'armement, mouvements militaires, diplomatie défense, programmes industriels — zone Atlantique-Méditerranée.

## Architecture cible

```
Sources (RSS, presse spécialisée, communiqués)
        │
        ▼
  Agent collecteur ──► Agent analyste (classification, résumé)
        │                        │
        │                        ▼
        │              Agent vérificateur (recoupement multi-sources,
        │               score de confiance, détection contradictions)
        ▼                        │
   Mémoire courte  ◄─────────────┘
   (dédoublonnage)
        │
        ▼
   API (FastAPI) ──► Front (carte sectorisée + flux + timeline)
```

Implémenté comme un `StateGraph` LangGraph : chaque agent (collector, analyst, verifier) est un nœud, l'état partagé (`VeilleState`) transporte le texte brut, la classification, le résumé, le score de confiance et le flag de recoupement d'un nœud à l'autre. LangSmith trace chaque nœud sans instrumentation manuelle.

## Stack

| Composant       | Choix                                    | Statut     |
|-----------------|-------------------------------------------|------------|
| Orchestration   | LangGraph / LangChain                    | retenu     |
| LLM             | Claude via `langchain-anthropic`         | retenu     |
| Backend         | Python 3.12, FastAPI, async               | retenu     |
| Déploiement     | Cloud Run + Cloud Scheduler (cron)        | retenu     |
| Observabilité   | LangSmith (tracing natif par nœud)        | retenu     |
| Frontend        | HTML/JS ou React, déployé avec l'API      | retenu     |
| Stockage        | GCS (raw/processed), Firestore (état)     | à valider  |

## Structure du repo

```
veille-01/
├── backend/
│   ├── agents/
│   │   ├── collector.py       # collecte des sources (RSS, API recherche)
│   │   ├── analyst.py         # classification + résumé
│   │   └── verifier.py        # recoupement, score de confiance
│   ├── api/
│   │   └── main.py            # FastAPI, endpoints /events, /health
│   ├── memory/
│   │   └── store.py           # dédoublonnage, état court terme
│   ├── config.py
│   └── requirements.txt
├── frontend/
│   └── index.html              # maquette actuelle (veille-01-mockup.html)
├── infra/
│   ├── Dockerfile
│   └── cloudrun.yaml
├── docs/
│   └── cadrage.md               # cadrage produit (problématique, MECE, risques, KPIs)
├── .env.example
└── README.md
```

## Démarrage rapide

```bash
git clone <repo-url> veille-01
cd veille-01

python -m venv .venv
source .venv/bin/activate        # .venv\Scripts\activate sous Windows

pip install -r backend/requirements.txt   # inclut langchain-anthropic, langgraph

cp .env.example .env             # renseigner ANTHROPIC_API_KEY, clé API recherche, LANGCHAIN_API_KEY (LangSmith)

uvicorn backend.api.main:app --reload --port 8080
```

Ouvrir `frontend/index.html` en parallèle pour visualiser le flux (données fictives tant que l'agent n'est pas branché).

## Roadmap

- [ ] V1 — collecte + classification + résumé texte, sources fixes
- [ ] V2 — agent vérificateur (recoupement, score de confiance) + carte sectorisée interactive
- [ ] V3 — mémoire interrogeable sur l'historique (requêtes en langage naturel)

## Métriques de suivi

- Couverture des sources (nb sources actives / nb sources ciblées)
- Précision de classification (échantillon annoté manuellement)
- Taux d'événements recoupés vs source unique
- Temps de traitement bout en bout par cycle

## Garde-fous (obligatoires dès V1)

- Limite de steps par run d'agent
- Plafond de budget/appels LLM par jour
- Traçabilité systématique : chaque affirmation doit pointer vers sa ou ses sources

## Note

Projet de démonstration. Les données affichées dans la maquette actuelle sont fictives.
