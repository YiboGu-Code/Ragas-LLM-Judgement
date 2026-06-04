from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from app.artifacts.redaction import redact_value


def save_trace_artifact(
    *,
    artifact_dir: str,
    run_id: str,
    record_id: str,
    trace: dict[str, Any],
    redaction_policy: str,
) -> tuple[str, str]:
    artifact_id = str(uuid.uuid4())
    root = Path(artifact_dir) / run_id
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{record_id}.json"

    payload = {"trace": redact_value(trace), "redaction_policy": redaction_policy}
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return artifact_id, str(path)

