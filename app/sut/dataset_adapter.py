from __future__ import annotations

from typing import Any


class DatasetSUTAdapter:
    name = "dataset"

    def __init__(self, **_: Any) -> None:
        pass

    async def execute(self, *, record: dict, provider) -> dict:
        trace = record.get("trace")
        output = record.get("output")

        if not isinstance(trace, dict):
            trace = None
        if output is None and isinstance(trace, dict):
            output = trace.get("output")

        if trace is None and output is None:
            raise ValueError("dataset adapter requires record.trace and/or record.output")

        trace_dict: dict[str, Any] = dict(trace or {})
        if output is not None and "output" not in trace_dict:
            trace_dict["output"] = output

        return {"output": output, "trace": trace_dict}
