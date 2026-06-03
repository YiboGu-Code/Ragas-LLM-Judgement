import pytest

from app.datasets.validator import validate_jsonl_lines


def test_validate_prompt_missing_user_input_reports_line_number():
    lines = [
        '{"type":"prompt","input":{"system_prompt":"x"}}',
    ]
    with pytest.raises(ValueError) as exc:
        validate_jsonl_lines(lines=lines, eval_type="prompt")
    assert "line=1" in str(exc.value)


def test_validate_rag_ok():
    lines = ['{"type":"rag","input":{"question":"q"}}']
    records = validate_jsonl_lines(lines=lines, eval_type="rag")
    assert records[0]["type"] == "rag"


def test_validate_empty_dataset_rejected():
    with pytest.raises(ValueError):
        validate_jsonl_lines(lines=[], eval_type="prompt")
