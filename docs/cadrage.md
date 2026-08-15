# Cadrage produit — VEILLE-01

Document de cadrage préalable au développement. Objectif : poser la problématique, le périmètre et les critères de succès avant d'écrire du code.

## 1. Contexte

Dans l'industrie de défense, le suivi du risque export-contrôle et de l'actualité géopolitique se fait, dans la plupart des organisations, de façon manuelle : revue de presse quotidienne, alertes email dispersées, pas de trace structurée de la fiabilité des sources. Deux conséquences typiques : un temps de réaction humain élevé face à une actualité dense et multilingue, et l'absence de traçabilité de la remontée d'information (impossible de justifier a posteriori pourquoi une information a été retenue ou écartée).

**Utilisateurs cibles** : analystes des fonctions conformité export, intelligence économique et affaires publiques.

## 2. Problématique

> Comment réduire le temps de synthèse quotidienne du risque export et géopolitique, tout en standardisant la lecture des signaux faibles et en traçant la fiabilité de chaque information remontée — sans dégrader la qualité du jugement humain final ?

Le point critique n'est pas la collecte (déjà partiellement automatisable par des outils de veille existants) mais :
1. la **classification** cohérente d'un flux hétérogène de sources,
2. le **recoupement multi-sources** pour distinguer signal confirmé et rumeur isolée,
3. la **traçabilité** systématique (chaque affirmation doit être adossée à une ou plusieurs sources identifiées).

## 3. Valeur attendue

| Dimension | Valeur | Mesurable via |
|---|---|---|
| Temps | Réduction du temps de synthèse quotidienne (revue manuelle → lecture d'un digest structuré) | Temps de traitement bout en bout par cycle |
| Qualité | Standardisation de la lecture des signaux faibles (grille de classification homogène, indépendante de l'analyste de service) | Précision de classification sur échantillon annoté |
| Fiabilité | Traçabilité systématique source → affirmation, score de confiance explicite | Taux d'événements recoupés vs source unique |
| Couverture | Élargissement du périmètre surveillé sans effort humain proportionnel | Couverture des sources (actives / ciblées) |

**Non-objectif explicite** : le système ne prend aucune décision (pas de blocage automatique d'un contrat, pas d'alerte réglementaire opposable). Il augmente la vitesse et la rigueur de la veille humaine — la décision reste humaine. C'est un point de vigilance éthique et légal à assumer explicitement dans le positionnement du produit.

### Ordre de grandeur illustratif (hypothèses de dimensionnement, à valider avec l'organisation utilisatrice)

| Poste | Hypothèse | Valeur |
|---|---|---|
| Équipe concernée | Analystes dédiés à la veille export/géopolitique | 4 |
| Temps de revue manuelle actuel | Revue de presse dispersée, sans agrégation | ~90 min/jour/analyste |
| Temps de revue avec digest structuré | Lecture ciblée, priorisée par catégorie et source | ~30 min/jour/analyste |
| Gain de temps | 60 min/jour/analyste × 4 analystes × ~220 j ouvrés/an | ~528 h/an |
| Coût chargé analyste (ordre de grandeur marché) | Hypothèse | ~60 €/h |
| **Valeur temps estimée** | 528 h × 60 € | **~32 000 €/an** |
| **Coût réel du système (mesuré)** | ~200 items/jour × 1 appel de classification, plus l'escalade du vérificateur (plafonnée) ; coût par appel mesuré en conditions réelles | **~140 €/an** (borne haute ~160 €/an si l'escalade sature ses plafonds) |

Le coût par appel (0,0018 $, mesuré : ~667 tokens d'entrée / ~231 de sortie) est stable ; c'est le volume qui pilote la facture. La reprise de la sélection des sources (§4) a environ doublé le volume quotidien sans changer l'ordre de grandeur du coût — à cette échelle, le poste de dépense réel n'est pas la classification de masse mais l'escalade agentique du vérificateur, dont le coût est proportionnel au nombre d'items escaladés et non au volume collecté. C'est la raison d'être des deux plafonds documentés en §8.

Le ratio valeur/coût reste favorable même avec des hypothèses dégradées (ex. gain de temps divisé par deux). L'essentiel du bénéfice attendu n'est de toute façon pas uniquement le temps mais la standardisation de la lecture des signaux faibles et la traçabilité systématique — qualitatives, plus difficiles à monétiser, mais tout aussi déterminantes dans la décision d'adoption.

## 4. Cadrage MECE du périmètre

### Inclus (V1)
- **Thématiques** : export control (licences, sanctions, embargos), contrats d'armement, mouvements militaires, diplomatie défense, programmes industriels.
- **Zone géographique** : mondiale — le filtrage MECE est thématique uniquement (cf. révision ci-dessous), le lieu de chaque item est extrait comme métadonnée sans restreindre la collecte.
- **Sources** : presse spécialisée défense, communiqués officiels, flux RSS publics — sélection par pays, cf. méthodologie ci-dessous.
- **Langues** : anglais, français, allemand, italien, espagnol (la classification est multilingue ; la restitution est en français).
- **Horizon temporel** : veille quotidienne (fenêtre de fraîcheur de 48 h à la collecte), pas d'historique profond en V1.

#### Méthodologie de sélection des sources

La première liste de sources (5 flux) avait été constituée par disponibilité — ce qui exposait un déséquilibre assumé vers l'actualité américaine et francophone. Sélection reprise sur un critère explicite et citable plutôt que sur la commodité :

1. **Colonne vertébrale géographique** : les 10 premiers exportateurs mondiaux d'armement selon le classement SIPRI (*Trends in International Arms Transfers*, données 2020-24), qui représentent ~89 % des exportations mondiales. Ce classement couvre directement trois des cinq catégories du périmètre (contrats, programmes industriels, mouvements).
2. **Ajout séparé pour l'export-contrôle** : l'Iran et la Corée du Nord, absents d'un classement par volume d'exportation mais centraux pour la catégorie `export_control` (régimes sous embargo actif). Ils sont ajoutés comme une liste fixe distincte, pas intégrés artificiellement au top 10.
3. **Quota par *type* de source plutôt que par nombre brut** : viser, par pays, une source institutionnelle et une à deux sources de presse spécialisée. Un nombre strictement égal de flux par pays égaliserait l'effort d'échantillonnage sans égaliser la représentativité réelle — le volume d'actualité défense produit par les États-Unis et la France est objectivement supérieur à celui du Brésil ou de la Corée du Sud.
4. **Validation empirique avant intégration** : chaque flux candidat est testé en direct (disponibilité, validité du format, fraîcheur) avant d'entrer dans `backend/config.py`. Sur 19 candidats identifiés, 7 se sont révélés inexploitables (erreurs 403/404, DNS, certificat invalide) et ont été remplacés par des alternatives testées.

**Traitement des sources d'État.** Pour la Chine, la Russie, l'Iran et la Corée du Nord, les seuls flux RSS gratuits disponibles sont des médias d'État ou d'agences semi-officielles. Trois options se présentaient : les exclure (angle mort sur des pays centraux pour l'export-contrôle), les inclure sans distinction (biais de propagande non déclaré), ou les inclure en marquant explicitement leur provenance. La troisième a été retenue : un champ `state_affiliated` est porté par la source et propagé jusqu'au digest, dans la même logique de traçabilité que la citation vérifiée (§8) — l'information reste collectée, mais sa nature est visible par l'analyste plutôt que noyée dans le flux général.

#### Révision : filtrage géographique retiré du critère de collecte

Version initiale du cadrage : périmètre restreint à la zone Atlantique-Méditerranée, appliqué comme
critère de rejet. Revu après test sur données réelles — à l'époque de cette révision, la liste de
sources comptait 5 flux, avant la sélection par pays décrite ci-dessus. Deux des cinq sources
confirmées d'alors (Breaking
Defense, Defense News) publient majoritairement de l'actualité domestique américaine sans jamais
nommer explicitement un pays de la zone dans le texte — un filtrage géographique strict au moment de
la collecte aurait rejeté la quasi-totalité de leurs items, alors que ce contenu (programmes,
contrats, sanctions) est bien pertinent pour la veille export-contrôle et que la façade atlantique
américaine n'a pas de raison d'être exclue de la zone. Décision : le lieu (pays/mer/région) reste
extrait et vérifié par item — nécessaire pour la carte sectorisée prévue en V2 (section 10) — mais ne
sert plus de critère de rejet en V1. Un filtrage géographique reste possible en aval (affichage,
V2) si le besoin est confirmé par l'usage, plutôt que décidé a priori à la collecte.

### Précisions de frontière (ajoutées après désaccords constatés en annotation, cf. §7)

- **Fusions-acquisitions / prises de participation dans l'industrie de défense** : classées `programme_industriel` si l'article porte sur l'opération elle-même (parties, montant, enjeu stratégique ou de souveraineté) — ex. un rachat par une entité étrangère susceptible de déclencher un contrôle des investissements. Classées `export_control` uniquement si l'article traite explicitement d'une procédure de licence, de sanction ou d'embargo. Classées `hors_perimetre` si l'article est centré sur l'analyse boursière (cours, réaction de marché) plutôt que sur l'opération.
- **Contenu d'opinion, tribune ou analyse prospective** : classé `hors_perimetre`, même si le thème correspond au périmètre, s'il ne rapporte pas un fait ou événement daté et vérifiable — la veille porte sur des faits sourcés (cf. §2 "chaque affirmation doit être adossée à une source"), pas sur des points de vue. Un article qui rapporte un fait daté et l'accompagne d'une analyse reste inclus ; un article qui n'est qu'une prise de position ne l'est pas.
- **`diplomatie_defense` vs `mouvement_militaire`** (ajouté après un échantillon de 88 items annotés, confusion la plus fréquente de l'échantillon — cf. §7) : une déclaration, un communiqué officiel ou la prise de parole d'un responsable nommé sur la posture, les intentions ou la coopération défense entre États est classée `diplomatie_defense`, même si le sujet évoqué est une force armée ou un armement — c'est la nature de l'acte rapporté (une déclaration) qui prime sur son sujet. `mouvement_militaire` est réservé au déploiement, positionnement ou contrôle effectif rapporté d'une force, d'un navire ou d'un asset militaire, pas à un commentaire sur ce déploiement.
- **`diplomatie_defense` vs `hors_perimetre`** (même échantillon) : une déclaration ou un communiqué officiel attribué à un responsable nommé, sur la coopération, les alliances ou la posture défense/sécurité entre États, est un fait daté — elle n'est pas classée `hors_perimetre` au seul motif qu'aucun contrat ni mouvement n'est décrit. À l'inverse, une visite d'État, un message protocolaire ou une pression diplomatique générale (droits humains, politique intérieure d'un pays tiers) sans contenu défense/sécurité explicite reste `hors_perimetre`, même si les deux pays ont par ailleurs une relation de défense.

### Exclu (explicitement, pour éviter la dérive de périmètre)
- Renseignement classifié ou sources fermées / payantes non contractualisées.
- Cybersécurité et menaces informatiques (périmètre voisin mais distinct, sujet à lui seul).
- Décision automatisée ou action corrective automatique (blocage, alerte réglementaire contraignante).
- Analyse financière de marché (cours, valorisation d'entreprises) — hors sujet risque export/géopolitique.

### Zones grises restant ouvertes
- Un mouvement militaire hors zone mais impliquant un client export de la zone (ex. livraison vers un pays tiers) : inclus ou non ?
- Sources en langue arabe ou russe pertinentes pour la zone Méditerranée : couvertes en V1 ou reportées en V2 (dépend de la disponibilité d'un LLM fiable en traduction/classification sur ces langues) ?

## 5. Alternatives évaluées (build vs buy)

| Option | Avantages | Limites pour ce cas d'usage | Décision |
|---|---|---|---|
| Outil de veille SaaS généraliste (ex. Meltwater, Onclusive, Netvibes Entreprise) | Déploiement rapide, pas de développement | Pas de recoupement multi-sources personnalisable au périmètre export-contrôle, pas de score de confiance ni de garde-fous sur mesure, licence récurrente, dépendance fournisseur forte sur un périmètre métier sensible | Écarté |
| Automatisation no-code (Make/Zapier/n8n + appel LLM générique) | Prototypage très rapide, pas d'infra à gérer | Pas d'état partagé explicite entre étapes, traçabilité fine par nœud difficile à obtenir, garde-fous (plafonds, limite de steps) peu robustes à faire respecter sur une plateforme tierce | Écarté |
| Développement sur mesure, orchestrateur agentique (LangGraph) | État partagé explicite (`VeilleState`) entre les nœuds, traçabilité native par nœud (LangSmith), garde-fous codés en dur, architecture qui absorbe l'ajout du vérificateur (V2) et de la mémoire interrogeable (V3) sans réécriture | Coût de développement et de maintenance plus élevé qu'une brique SaaS ou no-code | **Retenu** |

Le critère décisif n'est pas la vitesse de mise en œuvre initiale mais la capacité à garantir, de façon vérifiable, la traçabilité systématique et les plafonds de coût — des exigences non négociables (cf. section 8) qu'une brique tierce généraliste ne permet pas de garantir contractuellement.

## 6. Hypothèses & contraintes

- Les sources RSS/presse spécialisée ciblées sont accessibles publiquement et sans restriction de scraping (à vérifier juridiquement par source — conditions d'utilisation, robots.txt).
- Le LLM (Claude) est jugé suffisamment fiable pour la classification et le résumé sous réserve d'un score de confiance explicite et d'une revue humaine sur les cas à faible confiance — le système ne prétend pas à une fiabilité de 100 %.
- Budget LLM et infra plafonné dès V1 (garde-fou non négociable, cf. section 8).
- L'utilisateur final relit systématiquement le digest quotidien avant toute action — le système est un accélérateur, pas un substitut au jugement humain.

## 7. Métriques de succès (KPIs)

| KPI | Définition | Cible indicative V1 |
|---|---|---|
| Couverture des sources | Nb sources actives / nb sources ciblées | ≥ 90 % |
| Précision de classification | Accord système / annotation humaine sur échantillon | ≥ 85 % |
| Taux de recoupement | % d'événements confirmés par ≥ 2 sources indépendantes | Mesuré, pas de cible imposée (indicateur de robustesse, pas de performance à maximiser artificiellement) |
| Temps de traitement | Durée bout en bout par cycle de collecte | < 15 min pour un cycle quotidien |
| Taux de faux positifs jugés critiques | % d'événements remontés comme prioritaires mais jugés non pertinents par l'analyste | À suivre dès les premiers retours humains |

**Première mesure de précision (2026-08-11, n=30)** : 27/30 (90 %) en accord brut avec l'annotation humaine, au-dessus de la cible. En reprenant les 3 désaccords contre la définition littérale des catégories plutôt qu'à l'intuition, un seul s'est confirmé comme un vrai gap du classifieur (contenu d'opinion classé à tort dans une catégorie thématique — corrigé, cf. précisions de frontière §4) ; les deux autres reflétaient des définitions de catégorie encore ambiguës à ce moment-là (frontière fusion-acquisition / export-control / analyse financière), depuis clarifiées. Enseignement à retenir : sur un échantillon de cette taille, la mesure de précision est autant un test de la clarté des définitions que de la qualité du classifieur — les deux doivent être auditées ensemble, pas la seconde seule. `n=30` reste insuffisant pour une confiance statistique forte ; à reconduire à plus grande échelle avant de considérer ce KPI comme validé.

**Deuxième mesure (2026-08-14, n=88, après reconfiguration des sources par pays)** : 73/88 (83 %), légèrement sous la cible. Les 15 désaccords ont fait ressortir deux frontières de catégorie mal définies (`diplomatie_defense` vs `mouvement_militaire`, 4 cas ; `diplomatie_defense` vs `hors_perimetre`, 3 cas), corrigées ci-dessus §4. **Réserve méthodologique** : une partie de l'échantillon (~20 items) a été annotée avec l'aide d'un second avis consulté pendant l'annotation plutôt que jugée de façon strictement indépendante — le chiffre de 83 % doit être lu comme indicatif, pas comme une mesure d'accord indépendant au sens strict. Une reprise avec annotation strictement indépendante, après le correctif de prompt ci-dessus, est nécessaire avant de considérer ce KPI comme validé ou non sur cette itération des sources.

Le taux de recoupement est délibérément un indicateur de suivi et non un objectif à maximiser : le pousser artificiellement à la hausse inciterait le système à sur-pondérer les sujets déjà largement couverts au détriment des signaux faibles isolés, ce qui contredirait l'objectif de détection de signal faible.

## 8. Risques & garde-fous

Priorité = Probabilité × Impact ; classement décroissant, les risques Élevé/Élevé traités en premier dès V1.

| Risque | Probabilité | Impact | Priorité | Mitigation |
|---|---|---|---|---|
| Hallucination du LLM (affirmation sans source réelle) | Moyenne | Élevé | **Haute** | Traçabilité obligatoire : chaque affirmation du résumé doit pointer vers l'extrait source ; rejet automatique d'un résumé sans citation |
| Usage détourné (le système perçu comme validant une décision export/réglementaire) | Moyenne | Élevé | **Haute** | Positionnement explicite du livrable comme aide à la veille, non comme outil de décision ou de conformité opposable — risque juridique et réputationnel pour l'organisation utilisatrice en cas de mésusage |
| Biais de sources (sur-représentation d'une zone ou d'un point de vue) | Élevée | Moyen | Moyenne | Sélection des sources par pays sur critère explicite (§4), marquage `state_affiliated` des médias d'État, suivi de la couverture par pays, revue périodique de la liste |
| Dérive de coût (appels LLM incontrôlés) | Faible* | Moyen | Moyenne | Plafond de budget/appels LLM par jour (garde-fou dès V1, couvrant aussi les appels du vérificateur) + fenêtre de fraîcheur à la collecte, qui empêche un flux à historique profond de soumettre tout son arriéré en un seul run — *probabilité élevée si les garde-fous ne sont pas actifs, d'où leur caractère non négociable |
| Boucle d'agent incontrôlée | Faible* | Moyen | Moyenne | Limite de steps par run d'agent (`recursion_limit` du graphe) **et** double plafond sur l'escalade du vérificateur : items escaladés par run, itérations d'outil par item — le premier borne le graphe, le second borne la boucle interne au nœud, qui n'est pas couverte par le `recursion_limit` — *idem, dépend des garde-fous actifs |
| Dépendance à un unique fournisseur LLM | Faible | Moyen | Basse | Architecture découplée (LangChain) permettant un changement de modèle sans réécriture complète |

## 9. Gouvernance & adoption

- **Décisionnaire produit** : à désigner au sein de l'organisation utilisatrice, probablement la fonction conformité export ou intelligence économique — arbitre les évolutions de périmètre (sources, thématiques, zones grises listées en section 4).
- **Place dans le workflow existant** : digest quotidien généré avant l'heure de début de la revue matinale, consulté en amont de toute réunion de coordination — le système alimente un processus humain existant, il ne le remplace pas.
- **Répartition des rôles** : l'analyste reste seul décisionnaire de toute action ; le système priorise et synthétise, il ne valide ni n'invalide une affirmation de façon autonome.
- **Formation** : une grille de lecture du score de confiance et de la classification doit être diffusée aux utilisateurs — un score de confiance mal compris (perçu comme une garantie plutôt qu'une aide à la priorisation) invaliderait le garde-fou du non-objectif décrit en section 3.
- **Boucle de retour** : les faux positifs/négatifs signalés par les analystes alimentent l'amélioration de la classification, mais toute évolution du prompt ou de la logique de classification est validée manuellement — pas de réapprentissage automatique silencieux, pour rester auditable.

## 10. Plan de livraison

- **V1** — collecte + classification + résumé texte, sources fixes. Critère d'acceptation : couverture ≥ 90 %, digest quotidien généré sans intervention manuelle, chaque élément du digest tracé à sa source.
- **V2** — agent vérificateur (recoupement, score de confiance) + carte sectorisée interactive. Critère d'acceptation : score de confiance disponible sur 100 % des événements, taux de recoupement mesuré et documenté.
  - *Première tranche livrée* : le nœud vérificateur produit `confidence_score` et `corroborated` par une boucle d'outil bornée (recherche dans l'historique des items déjà analysés, fenêtre 30 jours), sur les catégories `export_control` et `contrat_armement` uniquement. Les autres items sortent sans score plutôt qu'avec une valeur par défaut — un score fabriqué par heuristique serait plus trompeur qu'utile pour la priorisation humaine (cf. §9, risque d'un score de confiance mal compris). Le critère d'acceptation "100 % des événements" n'est donc **pas** atteint à ce stade et reste l'objectif de la tranche suivante.
  - *Reste à faire sur V2* : extension aux trois autres catégories, enrichissement du contexte par récupération du texte intégral des articles (les extraits RSS sont souvent tronqués), carte sectorisée interactive à partir du champ `location` déjà extrait et vérifié.
- **V3** — mémoire interrogeable sur l'historique (requêtes en langage naturel). Critère d'acceptation : requête historique répondue avec citation des sources d'origine.
  - *Prérequis déjà posé* : l'historique des items analysés est devenu le stock unique du produit — il alimente à la fois le recoupement du vérificateur et le digest servi par l'API, sur une fenêtre glissante paramétrable plutôt que sur le seul dernier run. La V3 étend l'interrogation de ce stock, elle n'a plus à le constituer. La persistance est abstraite derrière une interface unique (fichiers locaux en développement, Firestore en production), condition pour que cet historique survive à un déploiement sur des instances au disque éphémère.

## 11. Limites connues

- Le système ne couvre que les sources ouvertes en français/anglais : un angle mort existe sur les sources locales en langue arabe ou russe tant que V1/V2 ne les intègrent pas.
- La classification par LLM reste probabiliste : le score de confiance affiché est une aide à la priorisation humaine, pas une garantie de véracité.
- Le périmètre est thématique et mondial (cf. révision §4) : sans filtrage géographique à la collecte, la couverture réelle dépend entièrement du mix de sources. La sélection par pays (§4) corrige le déséquilibre initial vers l'actualité américaine, mais ne l'annule pas : le volume collecté reste proportionnel à ce que chaque flux publie, pas au poids du pays dans les exportations mondiales.
- Certaines sources officielles pressenties (sites ministériels français, Mer et Marine) ne publient pas de flux RSS exploitable en l'état. La liste de sources (`backend/config.py`) est validée empiriquement flux par flux, mais la couverture institutionnelle reste inégale : plusieurs pays du périmètre n'ont pas d'agence de contrôle export ou de direction des achats exposant un flux exploitable (Corée du Sud, Israël notamment), ce qui oblige à s'appuyer sur la presse pour des faits qui gagneraient à venir d'une source primaire.
- Pour quatre pays du périmètre (Chine, Russie, Iran, Corée du Nord), aucune source gratuite indépendante n'a été trouvée : la couverture repose sur des médias d'État, marqués comme tels (§4) mais non recoupés par une source indépendante. Les affirmations issues de ces flux doivent être lues comme des revendications, pas comme des faits établis.
- Le vérificateur ne couvre que deux des cinq catégories, et son recoupement s'appuie sur un historique glissant de 30 jours qui démarre vide : le taux de corroboration observé les premiers jours d'exploitation sous-estime structurellement le taux réel, le temps que l'historique se constitue.
- La persistance de production (Firestore) est écrite et documentée mais **n'a pas été exécutée contre une base réelle** : le développement se fait sur le backend fichier, et l'émulateur Firestore n'est pas disponible dans l'environnement de travail. Elle ne doit pas être considérée comme validée tant qu'un run complet n'a pas tourné sur un projet GCP — l'atomicité de la réservation de budget en transaction, en particulier, ne se vérifie qu'en conditions concurrentes réelles. Trois points restent à trancher au moment du déploiement : le coût des lectures Firestore (l'historique est relu intégralement à chaque run, ce qui reste acceptable au volume actuel — ~6 000 documents sur 30 jours — mais devra passer par une pagination si le périmètre s'élargit) ; la région de la base, choisie une fois pour toutes ; et la fenêtre de rétention, aujourd'hui alignée sur le besoin de recoupement plutôt que sur un besoin d'archivage.
- Le champ `location` dépend de la mention explicite d'un lieu dans le texte source : un item réellement localisé ressort avec `location` vide si aucun lieu n'est nommé noir sur blanc, le garde-fou de traçabilité (§8) interdisant de déduire un lieu non écrit. Deux limites résiduelles mesurées sur un run réel, après correction du périmètre de vérification (le lieu est désormais vérifié contre le titre *et* le corps, non contre le seul corps — les extraits RSS étant souvent tronqués, le pays n'est fréquemment nommé que dans le titre ; la couverture est passée de 6 à 13 lieux extraits sur 16 items) :
  - **Gentilés non convertis** : « Ukrainian » n'autorise pas « Ukraine » si le mot n'apparaît nulle part, la conversion étant une déduction. Un article entièrement rédigé au gentilé reste sans lieu.
  - **Lieux non rattachables à un pays** : espaces maritimes, détroits internationaux et régions transnationales (Black Sea, Strait of Hormuz, Sahel) sont des extractions correctes qu'une carte par pays ne peut pas placer, et qui restent donc hors carte. Le cas des villes (Darwin, Kharkiv), lui, est traité : un champ `location_country` distinct porte le pays du lieu, déduit par le modèle. C'est la seule sortie du LLM soustraite au garde-fou verbatim (§8), puisque le pays d'une ville est par construction absent du texte. Trois contreparties la bornent : le champ est vidé dès que `location` l'est, donc un lieu rejeté à la vérification ne peut pas revenir placer l'item par ce biais ; il n'est retenu à l'affichage que s'il désigne une entité du référentiel cartographique, vocabulaire fermé qui fait retomber un pays inventé en « non rattaché » plutôt qu'en pays erroné ; et tout item placé par cette voie est compté à part et signalé comme déduit dans la carte comme dans le tableau. Le modèle a pour consigne de laisser le champ vide plutôt que d'arbitrer une souveraineté contestée, une région à cheval sur plusieurs pays ou une organisation.
  - **Homonymes de pays** : un lieu dont le nom correspond à plusieurs pays (« Korea ») n'est pas rattaché par ressemblance de nom — la restitution refuse de trancher et laisse la main au pays déduit, qui dispose du contexte de l'article. Constaté sur un run réel : une dépêche nord-coréenne était placée sur la Corée du Sud par le seul ordre d'itération du fonds de carte.
  - **Articles sans aucun lieu nommé** : un dernier repli les rattache au pays de la source, mais uniquement lorsque le modèle juge, sur le contenu de l'article, que l'événement y est domestique — actualité intérieure, institution ou forces armées du pays du média agissant chez elles. Le pays de la source seul ne suffit jamais : appliqué mécaniquement, il ferait peindre en Russie une dépêche TASS sur le Yémen, et le biais serait orienté, puisque le périmètre sur-échantillonne délibérément les médias d'État couvrant l'étranger (§4). Ce rattachement est plus faible que le précédent — rien n'est nommé, seul le sujet est interprété — et constitue donc un troisième niveau de provenance distinct, « présumé domestique », compté et affiché séparément du pays cité et du pays déduit. Il est refusé aux sources sans pays d'origine (multi-pays, institutionnelles UE), et ne s'applique jamais lorsqu'un lieu a été extrait : un lieu non rattachable à un pays (« Black Sea ») est une réponse, pas un manque.

  Trois niveaux de provenance en résultent, jamais fusionnés dans un total unique : **cité** (le pays est nommé dans la source et vérifié verbatim), **déduit** (un lieu est nommé, le modèle en donne le pays), **présumé domestique** (aucun lieu nommé, le modèle juge l'événement domestique au média). Un analyste doit pouvoir lire la couverture de la carte en sachant sur quoi elle repose.
