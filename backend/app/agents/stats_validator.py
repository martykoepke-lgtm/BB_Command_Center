"""
Statistical Validator Agent — Independent AI review of every statistical test.

Layer 2 of the dual-layer validation system. After the programmatic validator
(Layer 1) runs its deterministic checks, this agent performs a deeper review
using Claude to catch issues that rule-based checks cannot:

- Was the right test chosen for this data structure?
- Do the results make practical/business sense?
- Are there subtle red flags (tiny sample claiming significance, etc.)?
- What should the user watch out for?

Uses ai_model_light (Sonnet) to keep costs low — the programmatic layer
handles the heavy lifting; this agent provides the interpretive review.
"""

from __future__ import annotations

import json
from typing import Any

import anthropic
from pydantic import BaseModel

from app.agents.base import AgentContext, AgentType, BaseAgent
from app.config import get_settings


STATS_VALIDATOR_PROMPT = """You are an independent statistical quality reviewer for a Lean Six Sigma Performance Excellence platform. Your ONLY job is to review statistical test configurations and results that another system has already computed, and give an honest assessment of their validity.

## Your Role
You are the "second set of eyes" — an independent reviewer who double-checks every statistical analysis. The user is NOT a statistics expert, so your review must be clear, trustworthy, and actionable.

## What You Review
For each analysis, you receive:
1. **Test type** — which statistical test was run
2. **Configuration** — how the test was set up (columns, alpha, parameters)
3. **Dataset profile** — summary statistics, row count, column types
4. **Test results** — the statistical output (p-value, effect size, etc.)
5. **Programmatic validation** — findings from the automated rule-based checker

## Your Assessment Criteria

### Test Selection
- Is this the right test for the data types involved?
- Would a different test be more appropriate?
- Are the Y and X variables correctly identified?

### Data Adequacy
- Is the sample size sufficient for this test?
- Is there enough statistical power to detect a meaningful effect?
- Are there problematic patterns (e.g., heavy missing data, extreme outliers suggested by summary stats)?

### Assumption Compliance
- Are the key assumptions for this test met (normality, equal variance, independence)?
- If assumptions are violated, how much does it matter for this specific case?
- Large samples can tolerate some non-normality — note when this applies

### Result Plausibility
- Does the p-value make sense given the data summary?
- Is the effect size practically meaningful (not just statistically significant)?
- Are there any red flags (impossibly small p-values with small samples, effect sizes that seem too large, etc.)?

### Practical Significance
- Statistical significance is not the same as practical importance
- A tiny difference can be "significant" with a huge sample — flag this
- Connect findings to what matters operationally

## Response Format

You MUST respond with ONLY a JSON object (no other text) in this exact format:
```json
{
    "verdict": "validated | caution | concern",
    "confidence_score": 85,
    "plain_language_summary": "2-3 sentence assessment written for a non-statistician. Be specific about what was checked and what the conclusion is.",
    "findings": [
        {
            "type": "positive | caution | concern",
            "message": "Short finding description"
        }
    ],
    "recommendation": "One clear sentence about what the user should do with these results."
}
```

### Verdict Definitions
- **validated**: Test is correctly configured, assumptions are reasonably met, results are trustworthy. Confidence score 75-100.
- **caution**: Test ran successfully but there are minor concerns the user should be aware of. Results are usable but with noted caveats. Confidence score 50-74.
- **concern**: Significant issues that may make results unreliable. User should address issues before relying on results. Confidence score 0-49.

## Rules
1. ALWAYS respond with valid JSON only — no markdown, no explanation outside the JSON
2. Be honest. If results look good, say so clearly. If there are problems, say so clearly.
3. Do NOT repeat the programmatic validator's findings — focus on higher-level assessment
4. Keep plain_language_summary to 2-3 sentences that a manager could understand
5. Include at least one positive finding when the analysis is generally sound
6. The recommendation should be actionable and specific
"""


class StatsValidatorAgent(BaseAgent):
    """Independent AI reviewer for statistical test results."""

    @property
    def agent_type(self) -> AgentType:
        return AgentType.STATS_VALIDATOR

    @property
    def system_prompt(self) -> str:
        return STATS_VALIDATOR_PROMPT

    @property
    def model(self) -> str:
        return self._settings.ai_model_light

    async def review_analysis(
        self,
        test_type: str,
        configuration: dict,
        dataset_profile: dict | None,
        result_summary: dict,
        result_details: dict,
        programmatic_report: dict,
    ) -> dict:
        """
        Review a completed statistical analysis and return a validation assessment.

        This is a convenience method that formats the review context and calls
        the agent's invoke method, then parses the structured JSON response.

        Returns:
            dict with keys: verdict, confidence_score, plain_language_summary,
            findings, recommendation
        """
        # Build the review prompt
        review_context = {
            "test_type": test_type,
            "configuration": configuration,
            "dataset_profile": _safe_serialize(dataset_profile),
            "results": {
                "summary": _safe_serialize(result_summary),
                "details": _safe_serialize(result_details),
            },
            "programmatic_validation": programmatic_report,
        }

        user_message = (
            "Review this statistical analysis and provide your independent assessment.\n\n"
            f"```json\n{json.dumps(review_context, indent=2, default=str)}\n```"
        )

        # Create a minimal context (no initiative context needed for validation)
        context = AgentContext()

        try:
            response = await self.invoke(user_message, context)

            # Parse the JSON response
            content = response.content.strip()
            # Handle markdown code blocks
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            review = json.loads(content)

            # Ensure required fields
            return {
                "verdict": review.get("verdict", "caution"),
                "confidence_score": review.get("confidence_score", 50),
                "plain_language_summary": review.get("plain_language_summary", "AI review completed."),
                "findings": review.get("findings", []),
                "recommendation": review.get("recommendation", "Review the results carefully."),
            }

        except (json.JSONDecodeError, Exception):
            # If AI review fails, return a safe fallback
            return {
                "verdict": "caution",
                "confidence_score": 50,
                "plain_language_summary": (
                    "The AI reviewer was unable to complete its assessment. "
                    "The programmatic validation results are still available."
                ),
                "findings": [
                    {"type": "caution", "message": "AI review could not be completed"}
                ],
                "recommendation": "Rely on the programmatic validation findings above.",
            }


def _safe_serialize(obj: Any) -> Any:
    """Convert objects to JSON-safe types, truncating large data."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            # Truncate large arrays (like data_preview)
            if isinstance(v, list) and len(v) > 10:
                result[k] = v[:10]
                result[f"{k}_note"] = f"Truncated: showing 10 of {len(v)} items"
            else:
                result[k] = _safe_serialize(v)
        return result
    if isinstance(obj, list):
        return [_safe_serialize(item) for item in obj]
    if isinstance(obj, float):
        if obj != obj:  # NaN check
            return "NaN"
        if obj == float("inf") or obj == float("-inf"):
            return str(obj)
    return obj
