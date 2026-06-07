from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


EvalType = Literal["prompt", "rag", "workflow", "agent"]


class BaseRecord(BaseModel):
    record_id: str | None = None
    type: EvalType
    input: dict[str, Any]
    expected: dict[str, Any] | None = None
    tags: dict[str, Any] | None = None
    output: dict[str, Any] | str | None = None
    trace: dict[str, Any] | None = None


class PromptInput(BaseModel):
    user_input: str
    system_prompt: str | None = None
    variables: dict[str, Any] | None = None
    constraints: dict[str, Any] | None = None


class PromptRecord(BaseModel):
    record_id: str | None = None
    type: Literal["prompt"] = Field(default="prompt")
    input: PromptInput
    expected: dict[str, Any] | None = None
    tags: dict[str, Any] | None = None
    output: dict[str, Any] | str | None = None
    trace: dict[str, Any] | None = None


class RagInput(BaseModel):
    question: str
    retrieval_config: dict[str, Any] | None = None


class RagRecord(BaseModel):
    record_id: str | None = None
    type: Literal["rag"] = Field(default="rag")
    input: RagInput
    expected: dict[str, Any] | None = None
    tags: dict[str, Any] | None = None
    output: dict[str, Any] | str | None = None
    trace: dict[str, Any] | None = None


class WorkflowInput(BaseModel):
    goal: str
    inputs: dict[str, Any] | None = None
    workflow_ref: dict[str, Any] | None = None


class WorkflowRecord(BaseModel):
    record_id: str | None = None
    type: Literal["workflow"] = Field(default="workflow")
    input: WorkflowInput
    expected: dict[str, Any] | None = None
    tags: dict[str, Any] | None = None
    output: dict[str, Any] | str | None = None
    trace: dict[str, Any] | None = None


class AgentInput(BaseModel):
    task: str
    tools_allowed: list[str] | None = None
    environment: dict[str, Any] | None = None
    termination_criteria: dict[str, Any] | None = None


class AgentRecord(BaseModel):
    record_id: str | None = None
    type: Literal["agent"] = Field(default="agent")
    input: AgentInput
    expected: dict[str, Any] | None = None
    tags: dict[str, Any] | None = None
    output: dict[str, Any] | str | None = None
    trace: dict[str, Any] | None = None
