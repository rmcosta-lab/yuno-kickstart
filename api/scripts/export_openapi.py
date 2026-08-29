"""Write the canonical OpenAPI artifact consumed by Orval."""

import json
from pathlib import Path

from app.config import Settings
from app.main import create_app

API_ROOT = Path(__file__).resolve().parents[1]
OPENAPI_PATH = API_ROOT / "openapi.json"


def main() -> None:
    schema = create_app(Settings(app_env="test")).openapi()
    OPENAPI_PATH.write_text(
        json.dumps(schema, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
