"""API FastAPI : expose le digest genere par le pipeline (README architecture).

/run declenche le pipeline complet (~5 min, cf. NOTES.private.md) et sauvegarde le resultat ;
/events sert le dernier digest sauvegarde sans recalculer. Declenchement manuel en V1 (POST /run
appele a la main), remplace par Cloud Scheduler -> Cloud Run job en production.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.graph import run_pipeline
from backend.guardrails import BudgetExceeded

app = FastAPI(title="VEILLE-01 API")

# Ouvert en V1 pour permettre au frontend statique (fichier local ou serveur dev) d'appeler
# l'API sans configuration supplementaire. A restreindre a l'origine reelle avant deploiement.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_DIGEST_FILE = Path(__file__).parent / ".digest.json"


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

    digest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": result["analyzed_items"],
    }
    _DIGEST_FILE.write_text(json.dumps(digest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"generated_at": digest["generated_at"], "item_count": len(digest["items"])}


@app.get("/events")
def events() -> dict:
    if not _DIGEST_FILE.exists():
        raise HTTPException(status_code=404, detail="Aucun digest genere. Appeler POST /run d'abord.")
    return json.loads(_DIGEST_FILE.read_text(encoding="utf-8"))
