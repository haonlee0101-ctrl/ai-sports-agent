from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from src.analysis.analysis_validator import validate_analysis_output
from src.analysis.fallback_analyst import analyze_report_with_fallback
from src.analysis.prompt_builder import build_analysis_prompt
from src.contracts.analysis_output import AnalysisOutput
from src.contracts.report_input import ReportInput


class GPTAnalystError(ValueError):
    """Raised when the GPT analyst client response cannot be used safely."""


class GPTAnalyst:
    """Small wrapper that builds a prompt and validates injected client output."""

    def __init__(self, client: Any):
        self.client = client

    def analyze(
        self, report_input: ReportInput | dict, use_fallback_on_error: bool = False
    ) -> AnalysisOutput:
        report = (
            report_input
            if isinstance(report_input, ReportInput)
            else ReportInput.model_validate(report_input)
        )
        prompt = build_analysis_prompt(report)

        try:
            raw_response = self._request_client_response(prompt, report)
            payload = self._normalize_response_payload(raw_response)
            analysis_output = AnalysisOutput.model_validate(payload)
            return validate_analysis_output(report, analysis_output)
        except (ValidationError, ValueError, TypeError, json.JSONDecodeError) as error:
            if use_fallback_on_error:
                return analyze_report_with_fallback(report)
            raise GPTAnalystError(f"Invalid GPT analyst response: {error}") from error

    def _request_client_response(self, prompt: str, report: ReportInput) -> Any:
        create_analysis = getattr(self.client, "create_analysis", None)
        if callable(create_analysis):
            return create_analysis(prompt=prompt, report_input=report)

        if callable(self.client):
            return _call_client_callable(self.client, prompt, report)

        raise GPTAnalystError(
            "Injected client must be callable or provide a create_analysis("
            "prompt=..., report_input=...) method."
        )

    def _normalize_response_payload(self, response: Any) -> Any:
        if isinstance(response, AnalysisOutput):
            return response.model_dump()

        if isinstance(response, str):
            return json.loads(response)

        if isinstance(response, dict):
            return response

        model_dump = getattr(response, "model_dump", None)
        if callable(model_dump):
            return model_dump()

        output = getattr(response, "output", None)
        if output is not None:
            return self._normalize_response_payload(output)

        content = getattr(response, "content", None)
        if content is not None:
            return self._normalize_response_payload(content)

        raise GPTAnalystError(f"Unsupported GPT analyst response type: {type(response).__name__}")


def _call_client_callable(client: Callable[..., Any], prompt: str, report: ReportInput) -> Any:
    try:
        return client(prompt=prompt, report_input=report)
    except TypeError:
        return client(prompt, report)
