# Choix d'ingénierie

Ce document porte le « pourquoi » des décisions techniques de VEILLE-01 : garde-fous, invariants
de durabilité, règles de restitution, conduite de la campagne d'accumulation. Il a été extrait du
[`README.md`](../README.md), qui n'en garde que les conclusions — un lecteur doit pouvoir
comprendre le projet en quelques minutes sans traverser le raisonnement, et le retrouver ici
quand il le cherche.

Le cadrage produit — problématique, périmètre MECE, KPIs, matrice de risques, plan de livraison —
est dans [`cadrage.md`](cadrage.md). Ce document ne le double pas : il documente les décisions
d'implémentation prises pour le servir.

## Ce que le digest engage à l'écran

Le digest expose les signaux qui engagent la confiance plutôt que la seule liste d'articles : score de confiance du vérificateur, antécédent trouvé ou non dans l'historique, provenance « média d'État », citation vérifiée verbatim. Un item hors du périmètre du vérificateur sort sans score plutôt qu'avec un zéro trompeur.

Le libellé dit « avec / sans antécédent » et non « recoupé ». Le champ mesure ce que l'historique contenait au moment où l'article est passé au vérificateur, et les articles d'un même lot de collecte sont mutuellement invisibles au recoupement (`exclude_links`) : un thread de trois sources peut donc légitimement n'afficher qu'un seul antécédent. Lu « recoupé » à côté de ce même thread, le libellé passait pour une contradiction.

## La carte de couverture, et ce qu'elle refuse de fusionner

La carte est construite sur le champ `location` vérifié par item, pas sur le pays de la source, et affiche explicitement ce qu'elle ne peut pas placer — lieux non rattachables à un pays (espaces maritimes, détroits internationaux, régions transnationales). Une carte qui ne montrerait que ses succès surestimerait la couverture réelle.

Trois niveaux de rattachement sont comptés séparément et détaillés au survol, une couverture présumée ne devant pas se lire comme une couverture citée : le pays est **cité** par la source ; il est **déduit** par le modèle d'une localité nommée (« Darwin » → Australie) ; ou, à défaut de tout lieu nommé, l'événement est **présumé domestique** au pays du média — sur jugement du contenu de l'article, jamais sur la seule origine du média, qui placerait en Russie une dépêche TASS sur le Yémen.

## Les threads d'événements

Un **thread** rassemble les articles qui couvrent le même dossier — mêmes parties, même opération, même contrat — et non le même thème ni le même pays. Sa chronologie est tracée à l'échelle réelle du temps : trois dépêches tombées en vingt minutes et un dossier étalé sur trois semaines ne doivent pas se ressembler, l'écart entre les parutions étant précisément le signal (qui sort l'information, combien de temps la reprise met à suivre). Un article que son flux ne date pas est placé sur son entrée en base et marqué comme tel, jamais présenté comme une heure de parution — `first_seen` est un horodatage de lot, partagé par tous les items d'un même run.

Aucun indice de fiabilité agrégé n'est calculé au niveau du thread : moyenner des scores dont une partie vaut `null` comblerait implicitement ce vide et ferait passer un thread non vérifié pour un thread moyennement fiable. Les compteurs de vérification sont donc rendus séparément, en distinguant « non escaladé faute de budget » de « hors du périmètre du vérificateur » — deux silences différents, dont aucun ne vaut un score. Le bloc de provenance croise le pays du média et le pays de l'événement sans jamais les confondre : un thread couvert par une agence d'État étrangère ne se lit pas comme une couverture domestique.

## Le digest est une fenêtre glissante, pas la photographie du dernier run

Le dédoublonnage écartant, avant tout appel LLM, ce qui a déjà été vu dans les sept derniers jours, une seconde collecte dans la même journée ne produit qu'une poignée d'items neufs. Servir ce résultat brut reviendrait à effacer l'affichage à chaque collecte. `GET /events` lit donc l'historique des items analysés sur une profondeur paramétrable (`?days=`, bornée par la rétention de 7 jours), et le même historique alimente la recherche de recoupement du vérificateur — un seul stock, deux usages.

## Persistance : une interface, deux implémentations

(`backend/memory/persistence.py`). Trois états survivent aux runs : le compteur de budget LLM, les liens déjà vus et l'historique analysé. En développement ce sont des fichiers JSON ; en production ce sont des documents Firestore, parce que le système de fichiers de Cloud Run est éphémère et propre à chaque instance. La différence n'est pas qu'un confort de persistance : avec un compteur sur disque local, `MAX_LLM_CALLS_PER_DAY` redeviendrait contournable par un simple redémarrage. La réservation d'appel est donc exposée comme une opération du stockage (`reserve_llm_call`), atomique par transaction côté Firestore, plutôt que comme une lecture-modification-écriture faite par l'appelant — qui serait correcte en local et fausse en multi-instance. Le backend local reste le défaut : rien ne part vers GCP sans `VEILLE_STORAGE=firestore` explicite.

## Workflow déterministe et boucle agentique, séparés volontairement

Les nœuds `collect`/`deduplicate`/`analyze` forment un chemin de code fixe : un appel LLM par item, aucune décision dynamique du modèle — c'est le bon compromis pour une tâche de classification traçable et bon marché. Les nœuds `verify` et `thread` sont les deux points d'autonomie réelle : le modèle y dispose d'un outil de recherche dans l'historique des items analysés et décide lui-même s'il l'appelle, combien de fois, avant de conclure. Chaque escalade est bornée en code — nombre d'items par run et nombre d'itérations d'outil par item, plus une restriction aux catégories sensibles côté vérificateur — pour que l'agentivité reste un coût maîtrisé et non proportionnel au volume collecté.

## Le regroupement en threads réutilise ce patron, avec deux divergences assumées

Contrairement au vérificateur, le nœud `thread` n'applique aucun filtre par catégorie : `hors_perimetre` n'atteint jamais `analyzed_items`, donc tout item qui arrive là est déjà éligible à être rattaché à un dossier. Et il n'exclut pas le lot en cours — deux sources qui couvrent le même événement le même jour sont au contraire le cas le plus net de « même dossier », là où la corroboration du vérificateur exige une confirmation indépendante dans le temps. L'escalade est précédée d'un filtre gratuit (existence d'au moins un candidat au chevauchement de mots-clés) plutôt que d'un seuil de similarité : l'historique accumulé est encore trop mince pour en calibrer un, et un seuil non calibré serait un choix arbitraire déguisé en mesure.

**Mesure du 2026-08-18, qui corrige la portée du filtre annoncée ci-dessus.** Sur 199 items réels,
ce filtre est franchi par 100 % des items : sa requête étant le titre et le résumé entiers, elle
partage presque toujours un token avec au moins un enregistrement de la fenêtre. Il ne constitue
donc pas un second garde-fou — le seul plafond qui borne réellement le coût du nœud est
`MAX_THREAD_ESCALATIONS_PER_RUN`. Le score de chevauchement est en revanche pondéré depuis la même
date par la rareté des mots dans la fenêtre (IDF) : le comptage brut était dominé par les mots
vides, 64 % du score étant porté par des tokens présents dans plus d'un cinquième du corpus, et un
tiers des candidats servis au modèle a changé. Cela corrige le classement, pas le portillon, et ne
dit rien de la qualité du regroupement — la vérité terrain se limite à un seul thread.

## Garde-fous, implémentés dès V1

- `backend/guardrails.py` — plafond d'appels LLM par jour, testé dans les deux sens (déclenchement réel vérifié, run normal non affecté). Couvre aussi les appels du vérificateur, sans compteur séparé. Atteint, il **tronque** le run au lieu de l'annuler : les items déjà analysés sont enregistrés et servis, ceux qui n'ont pas été soumis au modèle restent collectables au cycle suivant, et l'API répond un succès partiel explicite (`truncated`) plutôt qu'une erreur — sans quoi le garde-fou de coût détruirait le travail qu'il vient de faire payer
- `backend/graph.py` — plafond de steps par run (`MAX_STEPS_PER_RUN`), appliqué via le `recursion_limit` LangGraph — protection contre une boucle d'agent incontrôlée (cadrage §8), testée dans les deux sens
- `backend/agents/verifier.py` — double plafond sur l'escalade agentique : nombre d'items escaladés par run et nombre d'itérations d'outil par item. Vérifié en code et non via `MAX_STEPS_PER_RUN`, qui compte les nœuds du graphe et ne borne pas une boucle interne à un nœud
- `backend/agents/threader.py` — même double plafond (`MAX_THREAD_ESCALATIONS_PER_RUN`, `MAX_THREAD_STEPS_PER_ITEM`), sans compteur de budget distinct : le regroupement passe par le garde-fou quotidien commun. Le plafond par run y est plus haut que celui du vérificateur, l'éligibilité étant plus large (cinq catégories contre deux), et il est précédé d'un filtre gratuit qui écarte sans aucun appel LLM les items sans candidat dans l'historique
- `backend/agents/collector.py` — fenêtre de fraîcheur (`COLLECTION_LOOKBACK_HOURS`) : plusieurs flux institutionnels exposent des mois d'historique sans pagination par date ; sans ce filtre, un premier run soumettrait tout l'arriéré au budget quotidien d'un seul coup
- `backend/agents/collector.py` — plafond par source (`MAX_ITEMS_PER_SOURCE_PER_RUN`, override possible par `Source.max_per_run`) : ajouté le 2026-08-17, mesuré en conditions réelles — sans lui, une agence de presse à cadence élevée (TASS, ~45 items/jour dans la fenêtre alors en vigueur) consommait le budget quotidien à elle seule, au détriment des flux spécialisés à faible volume mais fort signal. Complète la fenêtre de fraîcheur ci-dessus plutôt que de la remplacer : elle borne l'ancienneté, celui-ci borne le volume
- `backend/agents/analyst.py` — traçabilité systématique : un résumé sans citation vérifiable dans le texte source est rejeté automatiquement, pas seulement signalé

Les deux premiers garde-fous étaient initialement déclarés en config sans être vérifiés en code — écart trouvé par auto-audit et corrigé, plutôt que découvert en revue externe. C'est le type de vérification qu'un audit technique répété périodiquement pendant le développement doit attraper.

**Contrepartie mesurée du plafond par source.** Le plafond ne diffère pas la collecte, il l'écarte :
conservant les items les plus récents, il laisse la queue du flux vieillir hors de la fenêtre, où
elle n'est jamais reprise. Sur une fenêtre de 96 h, 279 items sont ainsi écartés sur 7 flux — plus
que l'historique analysé entier — concentrés sur Yonhap (-97), TASS (-88) et CGTN (-37). Le chiffre
est journalisé à chaque lancement à côté du KPI de couverture, parce qu'il n'est visible nulle part
ailleurs : rien dans l'historique analysé ne distingue « la source n'a rien publié » de « on a
écarté sa queue de flux ». La comparaison qu'il permet est le vrai apport — TASS écarte 88 items
tout en produisant 69 des 199 items analysés, là où Yonhap en écarte 97 pour 10 : le plafond rogne
un flux généraliste à faible rendement dans un cas, le flux le plus productif dans l'autre.

## Conduite de la campagne d'accumulation

Plusieurs décisions ouvertes — l'extension du vérificateur ([§10](cadrage.md) V2) et le calibrage du regroupement en threads — reposent sur une quantité qu'un historique court ne permet pas de mesurer : la proportion d'items ayant, dans l'historique, un voisin traitant du même dossier. Deux dépêches sur un même dossier à 48 h d'écart sont rares par construction ; la mesure n'a de sens que sur plusieurs semaines. Tant que le déclenchement automatique (Cloud Scheduler) n'est pas déployé, le pipeline est lancé une fois par jour à la main :

```bash
python -m scripts.daily_run              # le lancement quotidien
python -m scripts.daily_run --dry-run    # état de la campagne, sans consommer de budget
```

Le script journalise **chaque lancement**, y compris ceux qui ne produisent aucun item neuf et ceux qui échouent. Cette distinction ne se déduit pas de l'historique analysé : un jour sans nouveauté et un jour non lancé y laissent la même trace, alors que le premier est une mesure et le second un trou. `COLLECTION_LOOKBACK_HOURS` (96 h) borne ce qu'une collecte rattrape — un jour sauté est récupéré par le lancement suivant, des jours consécutifs sautés au-delà de cette fenêtre perdent définitivement les items publiés dans l'intervalle non couvert. L'écart depuis le dernier lancement est donc mesuré et signalé à chaque run. Chaque lancement mesure aussi, sans coût LLM, combien de sources ont produit au moins un item récent (`sources_active`/`sources_targeted`/`sources_silent` dans le journal) — une source qui se parse sans erreur mais ne publie plus rien de récent doit apparaître comme silencieuse, pas comme active (cf. KPI de couverture, `cadrage.md` §7).

La mesure qu'alimente cette campagne se rejoue ensuite sans aucun appel LLM :

```bash
python -m backend.eval.candidates
```

### Clôture, et pourquoi les mesures sont désormais gelées

La campagne s'est arrêtée le 2026-08-20 à cinq lancements et sept jours continus (261 items), sous les quinze jours visés. Ce n'est pas un abandon en cours de route : la rétention de l'historique a été ramenée le même jour de 30 à 7 jours pour le coût de stockage, ce qui rend l'assiette initialement visée inatteignable par construction — le jour le plus ancien est purgé à chaque run, l'historique ne peut plus jamais dépasser sept jours. Attendre plus longtemps n'aurait produit aucun corpus plus large.

La mesure a donc été prise sur sept jours, et à cette taille elle tranche ce qu'elle devait trancher : le score pondéré IDF discrimine (3 % des items au seuil 40, 12 % à 30, 34 % à 20), là où le portillon en production laisse passer 100 % des items. Ce que sept jours ne donnent pas, c'est le *seuil* lui-même — une échelle qui sépare ne dit pas où couper.

D'où la conséquence de méthode, qui vaut pour toute mesure ultérieure : **un corpus doit être gelé hors du stock au moment où il est mesuré**. Une mesure qui relit l'historique à la demande n'est pas rejouable, puisque recalculée une semaine plus tard elle ne retrouve plus aucun des items d'origine — et une annotation manuelle, qui coûte du temps humain, serait perdue avec eux. `backend/eval/build_pairs.py` applique cette règle à l'appariement de dossiers, comme `build_sample.py` le faisait déjà pour la classification : il écrit un échantillon autonome, portant tout le contexte nécessaire à l'annotation et au calcul, et archive toute version déjà annotée avant de la remplacer.

```bash
python -m backend.eval.build_pairs      # gèle l'échantillon (aucun appel LLM)
python -m backend.eval.annotate_pairs   # jugement humain : même dossier ?
python -m backend.eval.score_pairs      # précision du threading, effet d'un seuil
```

L'échantillon mêle deux populations qui répondent à la même question sans se confondre : les paires que le modèle a effectivement regroupées en threads — toutes, puisque ce sont exactement celles que juge le critère d'acceptation de la V3 tranche 1 — et des paires candidates tirées par bande de score, qui seules permettent de lire où le taux de vrais appariements s'effondre. Les taux sont repondérés par la population réelle de chaque bande au moment du calcul : l'échantillon étant stratifié, un comptage brut sur-pondérerait les bandes hautes, volontairement sur-tirées parce que peu peuplées.
