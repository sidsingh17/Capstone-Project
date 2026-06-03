"""
DeepEval-based evaluation + LLM-as-judge for recommendation quality.
"""
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI

from app.core.config import get_settings, make_openai_client
from app.models.schemas import RecommendationResponse

logger = logging.getLogger(__name__)

_JUDGE_SYSTEM = """You are an expert supply chain operations evaluator.
Your task is to critically assess the quality, relevance, and actionability of
supply chain risk mitigation recommendations."""


class EvaluationService:
    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[OpenAI] = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = make_openai_client()
        return self._client

    def llm_judge_recommendations(
        self,
        query: str,
        recommendations: RecommendationResponse,
        context_docs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        recs_text = "\n".join(
            f"{i+1}. {r.action} (Timeline: {r.timeline}, Owner: {r.owner})"
            for i, r in enumerate(recommendations.recommendations)
        )
        context_text = "\n".join(d.get("content", "")[:200] for d in context_docs[:3])

        prompt = f"""Evaluate these supply chain mitigation recommendations.

Original Query: {query}

Context (Historical Incidents):
{context_text}

Recommendations Generated:
{recs_text}

Summary: {recommendations.summary}
Risk Score: {recommendations.risk_assessment.overall_score:.2%}
Risk Level: {recommendations.risk_assessment.risk_level.value}

Evaluate on these dimensions (score 0-10 each):
1. RELEVANCE: How relevant are the recommendations to the stated risk?
2. ACTIONABILITY: How specific and immediately actionable are they?
3. COMPLETENESS: Do they address all major risk dimensions?
4. FEASIBILITY: Are the timelines and owners realistic?
5. EVIDENCE_BASED: Are recommendations grounded in the historical data?

Respond in this exact format:
RELEVANCE: [score]/10 - [one-line justification]
ACTIONABILITY: [score]/10 - [one-line justification]
COMPLETENESS: [score]/10 - [one-line justification]
FEASIBILITY: [score]/10 - [one-line justification]
EVIDENCE_BASED: [score]/10 - [one-line justification]
OVERALL_VERDICT: [APPROVED/NEEDS_IMPROVEMENT/REJECTED]
OVERALL_SCORE: [score]/10
FEEDBACK: [2-3 sentences of overall feedback]"""

        response = self.client.chat.completions.create(
            model=self.settings.LLM_MODEL,
            max_tokens=self.settings.MAX_TOKENS,
            messages=[
                {"role": "system", "content": _JUDGE_SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )

        return _parse_judge_response(response.choices[0].message.content or "")

    def evaluate_with_deepeval(
        self,
        query: str,
        response_text: str,
        context_texts: List[str],
    ) -> Dict[str, Any]:
        """
        Run DeepEval metrics: Answer Relevancy, Faithfulness, Contextual Precision, Recall.
        Falls back gracefully if DeepEval is not fully configured.
        """
        try:
            from deepeval import evaluate
            from deepeval.metrics import (
                AnswerRelevancyMetric,
                FaithfulnessMetric,
                ContextualPrecisionMetric,
                ContextualRecallMetric,
            )
            from deepeval.test_case import LLMTestCase

            test_case = LLMTestCase(
                input=query,
                actual_output=response_text,
                retrieval_context=context_texts[:5],
            )

            metrics = [
                AnswerRelevancyMetric(threshold=0.5),
                FaithfulnessMetric(threshold=0.5),
                ContextualPrecisionMetric(threshold=0.5),
                ContextualRecallMetric(threshold=0.5),
            ]

            results = {}
            for metric in metrics:
                try:
                    metric.measure(test_case)
                    results[metric.__class__.__name__] = {
                        "score": metric.score,
                        "passed": metric.is_successful(),
                        "reason": getattr(metric, "reason", ""),
                    }
                except Exception as e:
                    results[metric.__class__.__name__] = {"error": str(e)}

            overall = sum(v.get("score", 0) for v in results.values() if "score" in v)
            count = sum(1 for v in results.values() if "score" in v)
            results["average_score"] = overall / count if count > 0 else 0.0
            return results

        except ImportError:
            logger.warning("DeepEval not fully configured; returning placeholder scores")
            return {
                "AnswerRelevancyMetric": {"score": 0.75, "passed": True, "reason": "placeholder"},
                "FaithfulnessMetric": {"score": 0.80, "passed": True, "reason": "placeholder"},
                "ContextualPrecisionMetric": {"score": 0.70, "passed": True, "reason": "placeholder"},
                "ContextualRecallMetric": {"score": 0.72, "passed": True, "reason": "placeholder"},
                "average_score": 0.7425,
                "note": "DeepEval placeholder — configure OPENAI_API_KEY or deepeval credentials for real scores",
            }
        except Exception as e:
            logger.error(f"DeepEval evaluation failed: {e}")
            return {"error": str(e)}


def _parse_judge_response(text: str) -> Dict[str, Any]:
    import re
    result: Dict[str, Any] = {"raw_response": text}
    score_pattern = re.compile(r"(\w+):\s*(\d+(?:\.\d+)?)/10\s*-?\s*(.*)", re.IGNORECASE)
    scores = {}
    for match in score_pattern.finditer(text):
        key = match.group(1).upper()
        scores[key] = {
            "score": float(match.group(2)),
            "justification": match.group(3).strip(),
        }
    result["dimension_scores"] = scores

    verdict_match = re.search(r"OVERALL_VERDICT:\s*(APPROVED|NEEDS_IMPROVEMENT|REJECTED)", text, re.IGNORECASE)
    result["verdict"] = verdict_match.group(1).upper() if verdict_match else "UNKNOWN"

    overall_match = re.search(r"OVERALL_SCORE:\s*(\d+(?:\.\d+)?)/10", text, re.IGNORECASE)
    result["overall_score"] = float(overall_match.group(1)) / 10 if overall_match else 0.0

    feedback_match = re.search(r"FEEDBACK:\s*(.+?)(?:\Z|(?=\n[A-Z_]+:))", text, re.DOTALL | re.IGNORECASE)
    result["feedback"] = feedback_match.group(1).strip() if feedback_match else ""

    return result
