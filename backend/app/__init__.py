import os

# Suppress remote model price map fetch and telemetry across all workers and environments
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
os.environ.setdefault("LITELLM_TELEMETRY", "False")
