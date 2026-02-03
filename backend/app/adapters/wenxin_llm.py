"""T10 – Wenxin (Baidu LLM) 5.0 Adapter.

Input:  structured metrics + key chunks + prompt_version
Output: strict JSON: { summary, kpis_overrides, risks, recommendations, evidence_refs }

Validation: Pydantic JSON Schema enforcement + retry + fallback
Caching:    input-hash based to avoid duplicate API calls for same version
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, Optional

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.core.config import settings

logger = logging.getLogger(__name__)


# ── Pydantic models for strict LLM output validation ────
class LlmEvidenceRef(BaseModel):
    page_no: int
    bbox_norm: Optional[list[float]] = None
    snippet: Optional[str] = None


class LlmRisk(BaseModel):
    level: str  # high / medium / low
    title: str
    description: Optional[str] = None
    recommendation: Optional[str] = None
    evidence_refs: list[LlmEvidenceRef] = []


class LlmKpiOverride(BaseModel):
    metric_code: str
    value: Optional[float] = None
    value_text: Optional[str] = None
    evidence_refs: list[LlmEvidenceRef] = []


class LlmInsightOutput(BaseModel):
    """Strict schema that the LLM JSON must conform to."""
    summary: str = ""
    kpis_overrides: list[LlmKpiOverride] = []
    risks: list[LlmRisk] = []
    recommendations: list[str] = []
    evidence_refs: list[LlmEvidenceRef] = []


def compute_input_hash(metrics_json: str, chunks_text: str, prompt_version: str) -> str:
    """SHA-256 hash of inputs for caching."""
    raw = f"{prompt_version}|{metrics_json}|{chunks_text}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _build_prompt(metrics_json: str, chunks_text: str) -> str:
    return f"""你是一位资深金融分析师。以下是从一份上市公司年报中提取的结构化数据和关键文本片段。
请根据这些信息生成以下内容并严格以 JSON 格式输出：

1. summary: 一段简洁的年报总结（200-500字）
2. kpis_overrides: 对已有指标的修正或补充（如有）
3. risks: 风险项列表，每项包含 level(high/medium/low)、title、description、recommendation、evidence_refs
4. recommendations: 建议列表
5. evidence_refs: 全局证据引用

已提取指标:
{metrics_json}

关键文本片段:
{chunks_text}

请严格返回如下JSON格式（不要包含任何非JSON内容）:
{{
  "summary": "...",
  "kpis_overrides": [...],
  "risks": [...],
  "recommendations": [...],
  "evidence_refs": [...]
}}"""


async def generate_insights(
    metrics_json: str,
    chunks_text: str,
    prompt_version: str = "v1",
) -> LlmInsightOutput:
    """Call Wenxin 5.0 API and return validated structured output.

    Retries up to 2 times on failure; falls back to a basic report on
    persistent errors.
    """
    prompt = _build_prompt(metrics_json, chunks_text)

    headers = {
        "Authorization": f"Bearer {settings.WENXIN_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": settings.WENXIN_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
    }

    max_retries = 2
    backoff = 2.0

    async with httpx.AsyncClient(timeout=settings.WENXIN_TIMEOUT_SEC) as client:
        for attempt in range(max_retries + 1):
            try:
                resp = await client.post(
                    f"{settings.WENXIN_API_BASE}/v1/chat/completions",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()

                body = resp.json()
                content = body.get("choices", [{}])[0].get("message", {}).get("content", "{}")

                # Parse and validate
                raw = json.loads(content)
                return LlmInsightOutput.model_validate(raw)

            except (httpx.HTTPError, json.JSONDecodeError, ValidationError) as exc:
                logger.warning("LLM attempt %d failed: %s", attempt + 1, exc)
                if attempt == max_retries:
                    logger.error("LLM failed after all retries, returning fallback")
                    return LlmInsightOutput(
                        summary="LLM分析暂时不可用，请稍后重试。",
                        risks=[
                            LlmRisk(
                                level="medium",
                                title="自动分析失败",
                                description="LLM服务暂时不可用，本次分析结果需人工复核。",
                            )
                        ],
                    )
                time.sleep(backoff * (2 ** attempt))

    return LlmInsightOutput(summary="分析异常")
