from fastapi import APIRouter, HTTPException, status, Query
from typing import Optional
from app.models.schemas import DashboardMetrics, AnomalyResponse
from app.core.vector_store import VectorStore
from app.services.anomaly_detection import detect_anomalies
from app.core.config import get_settings

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _get_all_docs():
    vs = VectorStore()
    return vs.get_all()


@router.get(
    "/dashboard",
    response_model=DashboardMetrics,
    summary="Supply chain analytics dashboard",
    description="Aggregated metrics for the supply chain analytics dashboard.",
)
def get_dashboard():
    try:
        docs = _get_all_docs()
        return _compute_dashboard(docs)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/anomalies",
    response_model=AnomalyResponse,
    summary="Detect supply chain anomalies",
    description="Run IsolationForest anomaly detection over ingested incident data.",
)
def detect_anomaly_patterns(
    contamination: float = Query(default=0.05, ge=0.01, le=0.5, description="Anomaly contamination rate"),
):
    try:
        docs = _get_all_docs()
        return detect_anomalies(docs, contamination=contamination)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


def _compute_dashboard(docs) -> DashboardMetrics:
    from collections import Counter

    if not docs:
        return DashboardMetrics(
            total_incidents=0, critical_incidents=0, high_risk_suppliers=[],
            average_delivery_delay=0.0, average_transportation_cost=0.0,
            stockout_risk_locations=[], top_incident_types={}, severity_distribution={},
            recent_anomalies=0, disruption_trend="insufficient data",
        )

    total = len(docs)
    critical = sum(1 for d in docs if d.get("metadata", {}).get("severity") == "critical")

    supplier_risk: Counter = Counter()
    for d in docs:
        meta = d.get("metadata", {})
        if meta.get("severity") in ("critical", "high"):
            supplier_risk[meta.get("supplier_id", "Unknown")] += 1
    high_risk_suppliers = [s for s, _ in supplier_risk.most_common(5)]

    delays = [float(d.get("metadata", {}).get("delivery_delay", 0)) for d in docs]
    avg_delay = sum(delays) / len(delays) if delays else 0.0

    costs = [float(d.get("metadata", {}).get("transportation_cost", 0)) for d in docs]
    avg_cost = sum(costs) / len(costs) if costs else 0.0

    stockout_risk: Counter = Counter()
    for d in docs:
        meta = d.get("metadata", {})
        if float(meta.get("inventory_level", 999)) < 100:
            stockout_risk[meta.get("warehouse_location", "Unknown")] += 1
    stockout_locations = [loc for loc, _ in stockout_risk.most_common(5)]

    incident_types = Counter(
        d.get("metadata", {}).get("incident_type", "Unknown") for d in docs
    )
    severities = Counter(
        d.get("metadata", {}).get("severity", "unknown") for d in docs
    )

    high_delay_recent = sum(1 for d, delay in zip(docs[-100:], delays[-100:]) if delay > 7)
    trend = "deteriorating" if high_delay_recent > 20 else "stable" if high_delay_recent > 10 else "improving"

    return DashboardMetrics(
        total_incidents=total,
        critical_incidents=critical,
        high_risk_suppliers=high_risk_suppliers,
        average_delivery_delay=round(avg_delay, 2),
        average_transportation_cost=round(avg_cost, 2),
        stockout_risk_locations=stockout_locations,
        top_incident_types=dict(incident_types.most_common(8)),
        severity_distribution=dict(severities),
        recent_anomalies=high_delay_recent,
        disruption_trend=trend,
    )
