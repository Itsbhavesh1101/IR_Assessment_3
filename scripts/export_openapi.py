from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def export_openapi(output_path: Path | None = None) -> Path:
    from app.main import app

    target_path = output_path or PROJECT_ROOT / "openapi.json"
    schema = app.openapi()
    target_path.write_text(
        json.dumps(schema, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target_path


if __name__ == "__main__":
    exported_path = export_openapi()
    print(f"Exported OpenAPI schema to {exported_path}")
