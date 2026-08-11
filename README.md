# VEILLE-01 — Agent de veille export & risque défense/géopolitique

Agent IA autonome qui collecte, classe et synthétise quotidiennement des sources ouvertes sur un périmètre défense/géopolitique restreint, avec traçabilité systématique de chaque affirmation vers sa source.

**Statut** : backend V1 fonctionnel de bout en bout (collecte → dédoublonnage → classification → API → frontend), déploiement cloud à venir. Détail dans [Roadmap](#roadmap).

![Aperçu du digest](docs/screenshot.png)

## Cadrage

Cadrage complet — problématique, périmètre MECE, alternatives évaluées, KPIs, matrice de risques, gouvernance, plan de livraison — dans [`docs/cadrage.md`](docs/cadrage.md).

**Valeur** : diviser le temps de synthèse quotidienne, standardiser la lecture des signaux faibles, tracer la fiabilité de chaque information remontée.

**Périmètre V1** : export control, contrats d'armement, mouvements militaires, diplomatie défense, programmes industriels — filtrage thématique (le lieu est extrait comme métadonnée, sans restreindre la collecte, cf. cadrage §4).

## Architecture

```
Sources (RSS, presse spécialisée, communiqués)
        │
        ▼
  Agent collecteur ──► Mémoire courte ──► Agent analyste
   (backend/agents/     (dédoublonnage,     (classification, résumé,
    collector.py)        avant l'appel LLM)  citation vérifiée)
                          backend/memory/     backend/agents/analyst.py
                          store.py                   │
                                                      ▼
                                            Agent vérificateur (V2)
                                            recoupement multi-sources,
                                            score de confiance
                                                      │
                                                      ▼
                                     API (FastAPI) ──► Front (flux ; carte
                                     backend/api/       sectorisée en V2)
                                     main.py             frontend/index.html
```

Implémenté comme un `StateGraph` LangGraph (`backend/graph.py`) : chaque étape est un nœud, l'état partagé (`VeilleState`, `backend/state.py`) transporte les items d'un nœud à l'autre. Le dédoublonnage est placé *avant* l'appel LLM, pas après, pour ne pas consommer de budget sur des items déjà vus. LangSmith trace chaque nœud sans instrumentation manuelle.

## Stack

| Composant       | Choix                                    | Statut                |
|-----------------|-------------------------------------------|------------------------|
| Orchestration   | LangGraph / LangChain                    | construit (V1)          |
| LLM             | Claude Haiku via `langchain-anthropic`   | construit (V1)          |
| Backend         | Python 3.13, FastAPI                     | construit (V1)          |
| Observabilité   | LangSmith (tracing natif par nœud)       | construit (V1)          |
| Frontend        | HTML/JS statique, sans build             | construit (V1)          |
| Vérificateur / carte sectorisée | LangGraph + score de confiance | prévu (V2)     |
| Déploiement     | Cloud Run + Cloud Scheduler (cron)        | prévu                   |
| Stockage        | GCS (raw/processed), Firestore (état)     | à valider (V1 : fichiers locaux gitignored) |

## Structure du repo

```
vigie/
├── backend/
│   ├── agents/
│   │   ├── collector.py       # collecte RSS multi-sources, sources validées en direct
│   │   └── analyst.py         # classification MECE, résumé FR, citation + lieu vérifiés
│   ├── api/
│   │   └── main.py            # FastAPI : /health, /run, /events
│   ├── eval/
│   │   ├── build_sample.py    # échantillon stratifié pour mesurer la précision
│   │   ├── annotate.py        # annotation manuelle interactive
│   │   └── score.py           # précision mesurée vs cible (cadrage §7)
│   ├── memory/
│   │   └── store.py           # dédoublonnage court terme (avant l'appel LLM)
│   ├── config.py               # sources RSS, garde-fous obligatoires
│   ├── guardrails.py           # plafond d'appels LLM quotidien
│   ├── graph.py                 # assemblage StateGraph LangGraph
│   ├── state.py                 # schéma d'état partagé (VeilleState)
│   └── requirements.txt
├── frontend/
│   └── index.html               # digest — HTML/JS statique, appelle l'API réelle
├── docs/
│   └── cadrage.md               # cadrage produit (problématique, MECE, risques, KPIs)
├── .env.example
└── README.md
```

## Démarrage rapide

```bash
git clone https://github.com/Adrien-1997/vigie-01.git
cd vigie-01

python -m venv .venv
source .venv/bin/activate        # .venv\Scripts\activate sous Windows

pip install -r backend/requirements.txt

cp .env.example .env             # renseigner ANTHROPIC_API_KEY, LANGCHAIN_API_KEY (LangSmith),
                                  # MAX_STEPS_PER_RUN, MAX_LLM_CALLS_PER_DAY (garde-fous obligatoires)

uvicorn backend.api.main:app --reload --port 8080
```

Dans un second terminal, pour le frontend :

```bash
cd frontend
python -m http.server 5500
```

Ouvrir `http://localhost:5500`, puis cliquer sur **Lancer la collecte** (déclenche `POST /run` — pipeline complet, ~5 min, consomme du budget LLM réel).

## Roadmap

- [x] V1 — collecte + dédoublonnage + classification + résumé tracé + API + frontend
- [ ] V1 — déploiement Cloud Run + Cloud Scheduler
- [ ] V2 — agent vérificateur (recoupement, score de confiance) + carte sectorisée interactive
- [ ] V3 — mémoire interrogeable sur l'historique (requêtes en langage naturel)

## Métriques de suivi

Définitions et cibles détaillées dans [`docs/cadrage.md` §7](docs/cadrage.md). Mesure de précision de classification outillée dans `backend/eval/` (échantillonnage stratifié, annotation manuelle, score vs cible).

- Couverture des sources (nb sources actives / nb sources ciblées)
- Précision de classification (échantillon annoté manuellement)
- Temps de traitement bout en bout par cycle
- Taux de faux positifs jugés critiques par l'analyste

## Garde-fous (implémentés dès V1)

- `backend/guardrails.py` — plafond d'appels LLM par jour, teste dans les deux sens (déclenchement réel vérifié, run normal non affecté)
- `backend/agents/analyst.py` — traçabilité systématique : un résumé sans citation vérifiable dans le texte source est rejeté automatiquement, pas seulement signalé

## Note

Projet de démonstration à vocation portfolio. Le pipeline et l'API sont réels et fonctionnels (sources RSS live, appels LLM réels, mesures réelles) ; le déploiement cloud et le vérificateur multi-sources restent à construire.
