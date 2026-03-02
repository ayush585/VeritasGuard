import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server.database import get_db_runtime_status


def main() -> int:
    status = get_db_runtime_status()
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0 if status.get("healthy") else 1


if __name__ == "__main__":
    raise SystemExit(main())
