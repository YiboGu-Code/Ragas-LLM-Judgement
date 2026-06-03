from __future__ import annotations

import json
from typing import Any, Iterable

from pydantic import ValidationError

from app.datasets.records import AgentRecord, EvalType, PromptRecord, RagRecord, WorkflowRecord


def _parse_json(line: str, *, line_number: int) -> dict[str, Any]:
    try:
        value = json.loads(line)
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid json line={line_number}: {e.msg}") from e
    if not isinstance(value, dict):
        raise ValueError(f"invalid json object line={line_number}: expected object")
    return value


def validate_jsonl_lines(*, lines: Iterable[str], eval_type: EvalType) -> list[dict[str, Any]]:
    parsed: list[dict[str, Any]] = []
    for idx, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        obj = _parse_json(line, line_number=idx)
        try:
            if eval_type == "prompt":
                rec = PromptRecord.model_validate(obj)
            elif eval_type == "rag":
                rec = RagRecord.model_validate(obj)
            elif eval_type == "workflow":
                rec = WorkflowRecord.model_validate(obj)
            elif eval_type == "agent":
                rec = AgentRecord.model_validate(obj)
            else:
                raise ValueError(f"unsupported eval_type={eval_type}")
        except ValidationError as e:
            raise ValueError(f"schema error line={idx}: {e.errors()}") from e
        parsed.append(rec.model_dump(mode="json"))
    if not parsed:
        raise ValueError("empty dataset")
    return parsed
