import os

# backend/config.py requires these at import time, with no defaults (fail-fast by design).
# Tests must not depend on a local .env, so set safe defaults before backend.* is imported.
os.environ.setdefault("MAX_STEPS_PER_RUN", "20")
os.environ.setdefault("MAX_LLM_CALLS_PER_DAY", "200")
