# VEILLE-01 — Agent de veille export & risque défense/géopolitique

Agent IA autonome qui collecte, classe et synthétise quotidiennement des sources ouvertes sur un périmètre défense/géopolitique restreint, avec traçabilité systématique de chaque affirmation vers sa source.

**Statut** : pipeline V1 fonctionnel de bout en bout (collecte → dédoublonnage → classification → vérification → regroupement en threads → API → frontend), première tranche du vérificateur V2 et première tranche du raisonnement longitudinal V3 livrées, déploiement cloud à venir. Détail dans [Roadmap](#roadmap).

![Digest VIGIE : bandeau d'indicateurs, filtres par catégorie et par état de vérification, fiches d'événement portant la citation vérifiée, la provenance « média d'État » et l'état de vérification explicite ; en tête de liste, un thread rassemblant trois sources sur un même dossier](docs/screenshot.png)

Le digest expose les signaux qui engagent la confiance plutôt que la seule liste d'articles : score de confiance du vérificateur, antécédent trouvé ou non dans l'historique, provenance « média d'État », citation vérifiée verbatim. Un item hors du périmètre du vérificateur sort sans score plutôt qu'avec un zéro trompeur.

Le libellé dit « avec / sans antécédent » et non « recoupé ». Le champ mesure ce que l'historique contenait au moment où l'article est passé au vérificateur, et les articles d'un même lot de collecte sont mutuellement invisibles au recoupement (`exclude_links`) : un thread de trois sources peut donc légitimement n'afficher qu'un seul antécédent. Lu « recoupé » à côté de ce même thread, le libellé passait pour une contradiction.

![Carte de couverture géographique construite sur le lieu vérifié de chaque événement, avec le décompte des items sans lieu extrait et des lieux non rattachables à un pays](docs/screenshot-map.png)

La carte est construite sur le champ `location` vérifié par item, pas sur le pays de la source, et affiche explicitement ce qu'elle ne peut pas placer — lieux non rattachables à un pays (espaces maritimes, détroits internationaux, régions transnationales). Une carte qui ne montrerait que ses succès surestimerait la couverture réelle.

Trois niveaux de rattachement sont comptés séparément et détaillés au survol, une couverture présumée ne devant pas se lire comme une couverture citée : le pays est **cité** par la source ; il est **déduit** par le modèle d'une localité nommée (« Darwin » → Australie) ; ou, à défaut de tout lieu nommé, l'événement est **présumé domestique** au pays du média — sur jugement du contenu de l'article, jamais sur la seule origine du média, qui placerait en Russie une dépêche TASS sur le Yémen.

![Vue Threads : un dossier suivi par trois sources, sa chronologie à l'échelle réelle du temps, et le croisement entre pays du média et pays de l'événement](docs/screenshot-threads.png)

Un **thread** rassemble les articles qui couvrent le même dossier — mêmes parties, même opération, même contrat — et non le même thème ni le même pays. Sa chronologie est tracée à l'échelle réelle du temps : trois dépêches tombées en vingt minutes et un dossier étalé sur trois semaines ne doivent pas se ressembler, l'écart entre les parutions étant précisément le signal (qui sort l'information, combien de temps la reprise met à suivre). Un article que son flux ne date pas est placé sur son entrée en base et marqué comme tel, jamais présenté comme une heure de parution — `first_seen` est un horodatage de lot, partagé par tous les items d'un même run.

Aucun indice de fiabilité agrégé n'est calculé au niveau du thread : moyenner des scores dont une partie vaut `null` comblerait implicitement ce vide et ferait passer un thread non vérifié pour un thread moyennement fiable. Les compteurs de vérification sont donc rendus séparément, en distinguant « non escaladé faute de budget » de « hors du périmètre du vérificateur » — deux silences différents, dont aucun ne vaut un score. Le bloc de provenance croise le pays du média et le pays de l'événement sans jamais les confondre : un thread couvert par une agence d'État étrangère ne se lit pas comme une couverture domestique.

## Cadrage

Cadrage complet — problématique, périmètre MECE, alternatives évaluées, KPIs, matrice de risques, gouvernance, plan de livraison — dans [`docs/cadrage.md`](docs/cadrage.md). Synthèse visuelle : [`docs/slides.html`](docs/slides.html) (support de présentation navigable, ouvrir dans un navigateur).

**Valeur** : diviser le temps de synthèse quotidienne, standardiser la lecture des signaux faibles, tracer la fiabilité de chaque information remontée.

**Périmètre V1** : export control, contrats d'armement, mouvements militaires, diplomatie défense, programmes industriels — filtrage thématique (le lieu est extrait comme métadonnée, sans restreindre la collecte, cf. cadrage §4).

**Sources** : 18 flux RSS gratuits, organisés par pays plutôt que par thème — les 10 premiers exportateurs mondiaux d'armement (classement SIPRI *Trends in International Arms Transfers*, données 2020-24) plus l'Iran et la Corée du Nord pour la couverture export-contrôle. Chaque flux est validé en direct avant intégration ; les sources d'État (seule option gratuite disponible pour plusieurs de ces pays) sont marquées `state_affiliated` et restent visibles comme telles en aval, plutôt que d'être exclues ou mélangées silencieusement au reste. Le volume est plafonné par flux (`MAX_ITEMS_PER_SOURCE_PER_RUN`, cf. Garde-fous ci-dessous) plutôt que par flux à égalité de traitement : sans ce plafond, une agence de presse à cadence élevée épuisait le budget quotidien au détriment des sources spécialisées à plus faible volume mais plus fort signal.

## Architecture

```
Sources (RSS par pays, presse spécialisée, communiqués)
        │
        ▼
  Agent collecteur ──► Mémoire courte ──► Agent analyste
   (backend/agents/     (dédoublonnage,     (classification, résumé,
    collector.py)        avant l'appel LLM)  citation vérifiée)
                          backend/memory/     backend/agents/analyst.py
                          store.py                   │
                                                      ▼
                                            Agent vérificateur
                                            (backend/agents/verifier.py)
                                            recoupement sur l'historique,
                                            score de confiance
                                                      │
                                                      ▼
                                            Agent de regroupement
                                            (backend/agents/threader.py)
                                            threads d'événements sur
                                            l'historique
                                                      │
                                                      ▼
                                     API (FastAPI) ──► Front (digest filtrable,
                                     backend/api/       threads, carte de couverture)
                                     main.py             frontend/ (React + Vite)
```

Implémenté comme un `StateGraph` LangGraph (`backend/graph.py`) : chaque étape est un nœud, l'état partagé (`VeilleState`, `backend/state.py`) transporte les items d'un nœud à l'autre. Le dédoublonnage est placé *avant* l'appel LLM, pas après, pour ne pas consommer de budget sur des items déjà vus. LangSmith trace chaque nœud sans instrumentation manuelle.

**Le digest est une fenêtre glissante, pas la photographie du dernier run.** Le dédoublonnage écartant, avant tout appel LLM, ce qui a déjà été vu dans les sept derniers jours, une seconde collecte dans la même journée ne produit qu'une poignée d'items neufs. Servir ce résultat brut reviendrait à effacer l'affichage à chaque collecte. `GET /events` lit donc l'historique des items analysés sur une profondeur paramétrable (`?days=`, bornée par la rétention de 30 jours), et le même historique alimente la recherche de recoupement du vérificateur — un seul stock, deux usages.

**Persistance : une interface, deux implémentations** (`backend/memory/persistence.py`). Trois états survivent aux runs : le compteur de budget LLM, les liens déjà vus et l'historique analysé. En développement ce sont des fichiers JSON ; en production ce sont des documents Firestore, parce que le système de fichiers de Cloud Run est éphémère et propre à chaque instance. La différence n'est pas qu'un confort de persistance : avec un compteur sur disque local, `MAX_LLM_CALLS_PER_DAY` redeviendrait contournable par un simple redémarrage. La réservation d'appel est donc exposée comme une opération du stockage (`reserve_llm_call`), atomique par transaction côté Firestore, plutôt que comme une lecture-modification-écriture faite par l'appelant — qui serait correcte en local et fausse en multi-instance. Le backend local reste le défaut : rien ne part vers GCP sans `VEILLE_STORAGE=firestore` explicite.

**Workflow déterministe et boucle agentique, séparés volontairement.** Les nœuds `collect`/`deduplicate`/`analyze` forment un chemin de code fixe : un appel LLM par item, aucune décision dynamique du modèle — c'est le bon compromis pour une tâche de classification traçable et bon marché. Les nœuds `verify` et `thread` sont les deux points d'autonomie réelle : le modèle y dispose d'un outil de recherche dans l'historique des items analysés et décide lui-même s'il l'appelle, combien de fois, avant de conclure. Chaque escalade est bornée en code — nombre d'items par run et nombre d'itérations d'outil par item, plus une restriction aux catégories sensibles côté vérificateur — pour que l'agentivité reste un coût maîtrisé et non proportionnel au volume collecté.

**Le regroupement en threads réutilise ce patron, avec deux divergences assumées.** Contrairement au vérificateur, le nœud `thread` n'applique aucun filtre par catégorie : `hors_perimetre` n'atteint jamais `analyzed_items`, donc tout item qui arrive là est déjà éligible à être rattaché à un dossier. Et il n'exclut pas le lot en cours — deux sources qui couvrent le même événement le même jour sont au contraire le cas le plus net de « même dossier », là où la corroboration du vérificateur exige une confirmation indépendante dans le temps. L'escalade est précédée d'un filtre gratuit (existence d'au moins un candidat au chevauchement de mots-clés) plutôt que d'un seuil de similarité : l'historique accumulé est encore trop mince pour en calibrer un, et un seuil non calibré serait un choix arbitraire déguisé en mesure.

## Stack

| Composant       | Choix                                    | Statut                |
|-----------------|-------------------------------------------|------------------------|
| Orchestration   | LangGraph / LangChain                    | construit (V1)          |
| LLM             | Claude Haiku via `langchain-anthropic`   | construit (V1)          |
| Backend         | Python 3.13, FastAPI                     | construit (V1)          |
| Observabilité   | LangSmith (tracing natif par nœud)       | construit (V1)          |
| Frontend        | React + TypeScript + Vite                | construit (V1)          |
| Vérificateur (recoupement, score de confiance) | LangGraph + tool-calling borné | 1ʳᵉ tranche construite (catégories sensibles) |
| Carte de couverture interactive | d3-geo + Natural Earth, sur le champ `location` | construite (V2, 1ʳᵉ tranche) |
| Threads d'événements (regroupement longitudinal) | LangGraph + tool-calling borné, chronologie et provenance côté front | 1ʳᵉ tranche construite (V3) |
| Déploiement     | Cloud Run + Cloud Scheduler (cron)        | prévu                   |
| Stockage        | Fichiers JSON locaux (dev) / Firestore (production), derrière une interface unique | construit en local ; backend Firestore écrit mais **non validé contre une base réelle** |

## Structure du repo

```
vigie/
├── backend/
│   ├── agents/
│   │   ├── collector.py       # collecte RSS par pays, sources validées en direct
│   │   ├── analyst.py         # classification MECE, résumé FR, citation + lieu vérifiés
│   │   ├── verifier.py        # recoupement + score de confiance (boucle tool-calling bornée)
│   │   └── threader.py        # regroupement en threads d'événements (même patron borné)
│   ├── api/
│   │   └── main.py            # FastAPI : /health, /run, /events
│   ├── eval/
│   │   ├── build_sample.py    # échantillon stratifié pour mesurer la précision
│   │   ├── annotate.py        # annotation manuelle interactive
│   │   ├── score.py           # précision mesurée vs cible (cadrage §7)
│   │   └── candidates.py      # densité de candidats de recoupement, sans appel LLM
│   ├── memory/
│   │   ├── store.py           # dédoublonnage + historique analysé (recoupement et digest)
│   │   └── persistence.py     # fichiers JSON locaux (dev) ou Firestore (prod), même interface
│   ├── config.py               # sources RSS par pays, garde-fous obligatoires
│   ├── guardrails.py           # plafond d'appels LLM quotidien
│   ├── graph.py                 # assemblage StateGraph LangGraph
│   ├── state.py                 # schéma d'état partagé (VeilleState)
│   ├── requirements.txt
│   └── requirements-gcp.txt     # dépendance Firestore, déploiement uniquement
├── frontend/                    # React + TypeScript + Vite, appelle l'API réelle
│   └── src/
│       ├── components/          # digest filtrable, threads (chronologie + provenance),
│       │                        #   carte de couverture, vue tableau
│       └── lib/                 # taxonomie, filtres/tri, résolution des lieux, modèle de thread
├── scripts/
│   └── daily_run.py             # lancement quotidien + journal de campagne (hors service)
├── tests/                       # pytest — LLM et flux RSS mockés
├── docs/
│   ├── cadrage.md               # cadrage produit (problématique, MECE, risques, KPIs)
│   ├── slides.html              # support de présentation navigable
│   └── screenshot*.png          # captures régénérées contre l'application réelle
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
npm install
npm run dev
```

Ouvrir `http://localhost:5173`, puis cliquer sur **Lancer la collecte** (déclenche `POST /run` — pipeline complet, ~5 min, consomme du budget LLM réel). L'URL de l'API est `http://localhost:8080` par défaut, surchargeable via `VITE_API_BASE`.

## Accumulation d'historique

Plusieurs décisions ouvertes — l'extension du vérificateur ([§10](docs/cadrage.md) V2) et le calibrage du regroupement en threads — reposent sur une quantité qu'un historique court ne permet pas de mesurer : la proportion d'items ayant, dans l'historique, un voisin traitant du même dossier. Deux dépêches sur un même dossier à 48 h d'écart sont rares par construction ; la mesure n'a de sens que sur plusieurs semaines. Tant que le déclenchement automatique (Cloud Scheduler) n'est pas déployé, le pipeline est lancé une fois par jour à la main :

```bash
python -m scripts.daily_run              # le lancement quotidien
python -m scripts.daily_run --dry-run    # état de la campagne, sans consommer de budget
```

Le script journalise **chaque lancement**, y compris ceux qui ne produisent aucun item neuf et ceux qui échouent. Cette distinction ne se déduit pas de l'historique analysé : un jour sans nouveauté et un jour non lancé y laissent la même trace, alors que le premier est une mesure et le second un trou. `COLLECTION_LOOKBACK_HOURS` (96 h) borne ce qu'une collecte rattrape — un jour sauté est récupéré par le lancement suivant, des jours consécutifs sautés au-delà de cette fenêtre perdent définitivement les items publiés dans l'intervalle non couvert. L'écart depuis le dernier lancement est donc mesuré et signalé à chaque run. Chaque lancement mesure aussi, sans coût LLM, combien de sources ont produit au moins un item récent (`sources_active`/`sources_targeted`/`sources_silent` dans le journal) — une source qui se parse sans erreur mais ne publie plus rien de récent doit apparaître comme silencieuse, pas comme active (cf. KPI de couverture, `docs/cadrage.md` §7).

La mesure qu'alimente cette campagne se rejoue ensuite sans aucun appel LLM :

```bash
python -m backend.eval.candidates
```

## Roadmap

- [x] V1 — collecte + dédoublonnage + classification + résumé tracé + API + frontend
- [x] V1 — sources organisées par pays (top 10 exportateurs SIPRI + Iran/Corée du Nord), validées en direct
- [ ] V1 — déploiement Cloud Run + Cloud Scheduler
- [~] V2 — agent vérificateur : recoupement et score de confiance livrés sur les catégories sensibles ; extension aux autres catégories et `fetch_full_article` à venir
- [~] V2 — carte de couverture interactive livrée (filtrage par pays depuis le champ `location`) ; sectorisation par thème à venir
- [~] V3 — raisonnement longitudinal sur l'historique : le pipeline traitait chaque item isolément, alors qu'une part du signal se situe entre les items (un dossier qui évolue, la fréquence d'un pays qui monte). Cinq tranches séquencées, cadrées en [§10](docs/cadrage.md) :
  - [x] threads d'événements — regrouper les items d'un même dossier, restitués en chronologie à l'échelle réelle du temps avec le croisement média/lieu de l'événement ; critère d'acceptation sur échantillon annoté encore à mesurer, faute d'assez de threads réels
  - [ ] brief hebdomadaire — tendances de volume par catégorie/pays vs semaine précédente, chiffres issus d'une agrégation et non du modèle
  - [ ] détection de signal faible — concentration inhabituelle d'items corroborés sur un couple pays/catégorie
  - [ ] restitution temporelle — axe de temps des séries de volume, distinct du thread par dossier
  - [ ] mémoire interrogeable (requêtes en langage naturel)

## Métriques de suivi

Définitions et cibles détaillées dans [`docs/cadrage.md` §7](docs/cadrage.md). Mesure de précision de classification outillée dans `backend/eval/` (échantillonnage stratifié, annotation manuelle, score vs cible).

- Couverture des sources (nb sources actives / nb sources ciblées)
- Précision de classification (échantillon annoté manuellement)
- Temps de traitement bout en bout par cycle
- Taux de faux positifs jugés critiques par l'analyste

Deux mesures de précision ont été conduites (n=30 puis n=88 après la reconfiguration des sources). Les résultats, les correctifs de définition qu'ils ont déclenchés et les réserves méthodologiques qui les accompagnent sont détaillés en [§7](docs/cadrage.md) — y compris ce qui reste à revérifier avant de considérer le KPI comme tranché.

## Garde-fous (implémentés dès V1)

- `backend/guardrails.py` — plafond d'appels LLM par jour, testé dans les deux sens (déclenchement réel vérifié, run normal non affecté). Couvre aussi les appels du vérificateur, sans compteur séparé. Atteint, il **tronque** le run au lieu de l'annuler : les items déjà analysés sont enregistrés et servis, ceux qui n'ont pas été soumis au modèle restent collectables au cycle suivant, et l'API répond un succès partiel explicite (`truncated`) plutôt qu'une erreur — sans quoi le garde-fou de coût détruirait le travail qu'il vient de faire payer
- `backend/graph.py` — plafond de steps par run (`MAX_STEPS_PER_RUN`), appliqué via le `recursion_limit` LangGraph — protection contre une boucle d'agent incontrôlée (cadrage §8), testée dans les deux sens
- `backend/agents/verifier.py` — double plafond sur l'escalade agentique : nombre d'items escaladés par run et nombre d'itérations d'outil par item. Vérifié en code et non via `MAX_STEPS_PER_RUN`, qui compte les nœuds du graphe et ne borne pas une boucle interne à un nœud
- `backend/agents/threader.py` — même double plafond (`MAX_THREAD_ESCALATIONS_PER_RUN`, `MAX_THREAD_STEPS_PER_ITEM`), sans compteur de budget distinct : le regroupement passe par le garde-fou quotidien commun. Le plafond par run y est plus haut que celui du vérificateur, l'éligibilité étant plus large (cinq catégories contre deux), et il est précédé d'un filtre gratuit qui écarte sans aucun appel LLM les items sans candidat dans l'historique
- `backend/agents/collector.py` — fenêtre de fraîcheur (`COLLECTION_LOOKBACK_HOURS`) : plusieurs flux institutionnels exposent des mois d'historique sans pagination par date ; sans ce filtre, un premier run soumettrait tout l'arriéré au budget quotidien d'un seul coup
- `backend/agents/collector.py` — plafond par source (`MAX_ITEMS_PER_SOURCE_PER_RUN`, override possible par `Source.max_per_run`) : ajouté le 2026-08-17, mesuré en conditions réelles — sans lui, une agence de presse à cadence élevée (TASS, ~45 items/jour dans la fenêtre alors en vigueur) consommait le budget quotidien à elle seule, au détriment des flux spécialisés à faible volume mais fort signal. Complète la fenêtre de fraîcheur ci-dessus plutôt que de la remplacer : elle borne l'ancienneté, celui-ci borne le volume
- `backend/agents/analyst.py` — traçabilité systématique : un résumé sans citation vérifiable dans le texte source est rejeté automatiquement, pas seulement signalé

Les deux premiers garde-fous étaient initialement déclarés en config sans être vérifiés en code — écart trouvé par auto-audit et corrigé, plutôt que découvert en revue externe. C'est le type de vérification qu'un audit technique répété périodiquement pendant le développement doit attraper.

## Qualité & CI

- Lint et format : `ruff` (config dans `pyproject.toml`)
- Tests : `pytest` (`tests/`, LLM et flux RSS mockés — rapides, déterministes, sans coût)
- CI : `.github/workflows/ci.yml`, lance lint + format + tests sur chaque push/PR

## Note

Projet de démonstration à vocation portfolio. Le pipeline et l'API sont réels et fonctionnels (sources RSS live, appels LLM réels, mesures réelles) ; le déploiement cloud reste à construire, et le vérificateur ne couvre pour l'instant que les catégories les plus sensibles — les autres items sortent sans score de confiance plutôt qu'avec un score fabriqué par défaut.
