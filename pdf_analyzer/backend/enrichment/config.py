import os
from dataclasses import dataclass

def _load_env_file():
    """Automatically load .env file if present in workspace."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_paths = [
        os.path.join(os.path.dirname(base_dir), ".env"),
        os.path.abspath(".env")
    ]
    for env_path in env_paths:
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            # Overwrite or set if not present
                            os.environ[k.strip()] = v.strip().strip('"').strip("'")
            except Exception:
                pass

_load_env_file()

@dataclass
class EnrichmentConfig:
    openalex_api_key: str = os.getenv("OPENALEX_API_KEY", "").strip()
    openalex_email: str = os.getenv("OPENALEX_EMAIL", "").strip()
    crossref_mailto: str = os.getenv("CROSSREF_MAILTO", "").strip()
    serpapi_key: str = os.getenv("SERPAPI_KEY", "").strip()
    match_threshold: float = float(os.getenv("REFERENCE_MATCH_THRESHOLD", "0.80"))
    cache_enabled: bool = os.getenv("REFERENCE_CACHE_ENABLED", "true").lower() in ("true", "1", "yes")

    @property
    def has_openalex_key(self) -> bool:
        return bool(self.openalex_api_key)

config = EnrichmentConfig()
