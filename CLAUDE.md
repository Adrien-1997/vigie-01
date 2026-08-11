# CLAUDE.md

Instructions de projet pour VEILLE-01 (repo GitHub : `vigie-01`). Lu automatiquement à chaque session — objectif : ne pas perdre les conventions établies au fil des itérations précédentes.

## Discipline de base

- **Ne jamais déclarer un composant "fait" sans l'avoir testé contre des données réelles.** Chaque nœud du pipeline a été testé en direct (RSS live, appels LLM réels) avant de passer au suivant. Un test qui "devrait marcher" ne compte pas.
- **Les garde-fous documentés dans `docs/cadrage.md` (§6, §8) doivent être appliqués en code, pas seulement déclarés.** Précédent vécu : `MAX_LLM_CALLS_PER_DAY` existait dans `config.py` mais n'était vérifié nulle part — trouvé par auto-audit, corrigé dans `backend/guardrails.py`. Avant d'ajouter un garde-fou au cadrage, vérifier qu'il est câblé dans le code correspondant.
- **Traçabilité systématique** : tout résumé généré par le LLM doit être accompagné d'une citation vérifiée verbatim contre le texte source (`_extract_verified` dans `backend/agents/analyst.py`). Un résumé sans citation vérifiable est rejeté, pas juste signalé.

## Conventions techniques

- **Toujours `encoding="utf-8"` explicite** sur `Path.read_text()`/`write_text()`. Sans ça, ça casse sous Windows (cp1252 par défaut) alors que ça peut sembler marcher sous Git Bash avec `PYTHONUTF8=1` positionné — bug rencontré deux fois avant d'être corrigé partout.
- **Stockage fichier local comme placeholder documenté avant Firestore/GCS** (`backend/guardrails.py`, `backend/memory/store.py`) : ne pas construire l'infra cloud avant d'avoir un pipeline local qui tourne de bout en bout. Le déploiement GCP (Dockerfile, Cloud Run, Cloud Scheduler) est la dernière étape, pas une étape en parallèle du reste du backend.
- **Dédoublonnage placé avant l'appel LLM**, pas après (`backend/memory/store.py` opère sur `raw_items`, pas `analyzed_items`) : un item déjà vu ne doit pas consommer de budget LLM avant d'être filtré.

## Périmètre produit

Les définitions de catégories MECE (thématiques, frontière fusion-acquisition/export-control, opinion vs fait daté vérifiable) sont dans `docs/cadrage.md` §4 — à consulter avant de modifier le prompt de classification dans `backend/agents/analyst.py`. Ces définitions ont déjà été affinées suite à des désaccords constatés en annotation manuelle ; ne pas les rouvrir sans preuve concrète nouvelle.

## Documents publics vs privés

- `README.md` et `docs/cadrage.md` sont publics : cadrage produit neutre uniquement, aucune narration personnelle ou contextuelle.
- Un fichier `*.private.md` local (gitignored, jamais committé) peut contenir du contexte et un journal de bord détaillé. S'il existe, le consulter pour comprendre l'historique des décisions avant de proposer de rouvrir un sujet déjà tranché.

## Git

- Commits toujours au nom de l'utilisateur, sans trailer de co-attribution.
- Messages de commit en anglais.
- Ne jamais committer sans demande explicite.

## Budget LLM

Vérifier `backend.guardrails.remaining_calls_today()` avant un test qui appelle le LLM sur un volume significatif (le pipeline complet consomme ~1 appel/item, ~110 items/jour). Préférer un sous-échantillon pour valider un changement de logique ; réserver les runs complets aux vraies validations de milestone.
