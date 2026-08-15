"""API FastAPI : expose le digest genere par le pipeline (README architecture).

/run declenche le pipeline complet (~5 min, cf. NOTES.private.md) ; /events sert une fenetre
glissante sur l'historique analyse, sans rien recalculer. Declenchement manuel en V1 (POST /run
appele a la main), remplace par Cloud Scheduler -> Cloud Run job en production.

Le digest n'est deliberement pas le resultat du dernier run : le dedoublonnage ecarte avant l'appel
LLM tout ce qui a deja ete vu dans les 7 derniers jours, donc un second run dans la meme journee ne
renvoie qu'une poignee d'items neufs. Servir ce resultat brut reviendrait a effacer l'historique
affiche a chaque collecte (cf. backend/memory/store.py).
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.config import DIGEST_WINDOW_DAYS
from backend.graph import run_pipeline
from backend.guardrails import BudgetExceeded
from backend.memory.store import RELATED_ITEMS_WINDOW_DAYS, last_run_at, load_digest

app = FastAPI(title="VEILLE-01 API")

# Ouvert en V1 pour permettre au frontend statique (fichier local ou serveur dev) d'appeler
# l'API sans configuration supplementaire. A restreindre a l'origine reelle avant deploiement.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/run")
def run() -> dict:
    try:
        result = run_pipeline()
    except BudgetExceeded as e:
        # Garde-fou §8 : le run est interrompu volontairement, ce n'est pas une panne serveur.
        raise HTTPException(status_code=429, detail=str(e)) from e

    return {"item_count": len(result["analyzed_items"])}


@app.get("/events")
def events(
    days: int = Query(
        DIGEST_WINDOW_DAYS,
        ge=1,
        le=RELATED_ITEMS_WINDOW_DAYS,
        description="Profondeur du digest en jours, bornee par la retention de l'historique analyse.",
    ),
) -> dict:
    items = load_digest(days)
    # 404 signifie « le pipeline n'a jamais tourne », pas « rien sur cette periode » : une fenetre
    # etroite sur un historique non vide doit rester un digest vide navigable, avec le selecteur de
    # periode disponible pour elargir.
    if not items and not load_digest(RELATED_ITEMS_WINDOW_DAYS):
        raise HTTPException(status_code=404, detail="Aucun digest genere. Appeler POST /run d'abord.")
    return {
        "generated_at": last_run_at(items),
        "window_days": days,
        "max_window_days": RELATED_ITEMS_WINDOW_DAYS,
        "items": items,
    }
