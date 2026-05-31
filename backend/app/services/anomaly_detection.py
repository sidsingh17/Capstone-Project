import logging
from typing import List, Dict, Any, Tuple
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from app.models.schemas import AnomalyRecord, AnomalyResponse

logger = logging.getLogger(__name__)

NUMERIC_FEATURES = ["delivery_delay", "inventory_level", "transportation_cost",
                    "order_quantity", "demand_forecast"]


def _build_feature_matrix(documents: List[Dict[str, Any]]) -> Tuple[np.ndarray, List[str]]:
    rows = []
    ids = []
    for doc in documents:
        meta = doc.get("metadata", {})
        row = [float(meta.get(f, 0.0)) for f in NUMERIC_FEATURES]
        rows.append(row)
        ids.append(doc["id"])
    return np.array(rows, dtype=float), ids


def detect_anomalies(
    documents: List[Dict[str, Any]],
    contamination: float = 0.05,
) -> AnomalyResponse:
    if len(documents) < 10:
        return AnomalyResponse(
            total_anomalies=0,
            anomalies=[],
            correlation_insights=["Insufficient data for anomaly detection (minimum 10 records required)"],
            detection_method="IsolationForest",
        )

    X, ids = _build_feature_matrix(documents)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    clf = IsolationForest(contamination=contamination, random_state=42, n_estimators=100)
    labels = clf.fit_predict(X_scaled)
    scores = clf.score_samples(X_scaled)

    anomaly_records = []
    for i, (label, score) in enumerate(zip(labels, scores)):
        if label == -1:
            doc = documents[i]
            meta = doc.get("metadata", {})
            anomalous_features = _identify_anomalous_features(X[i], X, scaler)
            description = _describe_anomaly(meta, anomalous_features)
            anomaly_records.append(AnomalyRecord(
                incident_id=ids[i],
                anomaly_score=round(float(-score), 4),
                anomalous_features=anomalous_features,
                description=description,
                severity=str(meta.get("severity", "unknown")),
                timestamp=str(meta.get("timestamp", "")),
            ))

    anomaly_records.sort(key=lambda x: x.anomaly_score, reverse=True)
    correlation_insights = _compute_correlations(documents)

    return AnomalyResponse(
        total_anomalies=len(anomaly_records),
        anomalies=anomaly_records[:20],
        correlation_insights=correlation_insights,
        detection_method="IsolationForest",
    )


def _identify_anomalous_features(
    row: np.ndarray, X: np.ndarray, scaler: StandardScaler
) -> List[str]:
    mean = X.mean(axis=0)
    std = X.std(axis=0)
    anomalous = []
    for i, feat in enumerate(NUMERIC_FEATURES):
        if std[i] > 0:
            z = abs(row[i] - mean[i]) / std[i]
            if z > 2.5:
                direction = "high" if row[i] > mean[i] else "low"
                anomalous.append(f"{feat} ({direction})")
    return anomalous if anomalous else ["multivariate pattern"]


def _describe_anomaly(meta: Dict[str, Any], features: List[str]) -> str:
    supplier = meta.get("supplier_id", "Unknown")
    warehouse = meta.get("warehouse_location", "Unknown")
    itype = meta.get("incident_type", "Unknown")
    return (
        f"Anomalous {itype} at {warehouse} from supplier {supplier}. "
        f"Unusual pattern detected in: {', '.join(features)}."
    )


def _compute_correlations(documents: List[Dict[str, Any]]) -> List[str]:
    rows = []
    for doc in documents:
        meta = doc.get("metadata", {})
        rows.append({f: float(meta.get(f, 0.0)) for f in NUMERIC_FEATURES})

    if not rows:
        return []

    df = pd.DataFrame(rows)
    insights = []

    corr = df.corr()

    if abs(corr.loc["delivery_delay", "transportation_cost"]) > 0.3:
        direction = "positive" if corr.loc["delivery_delay", "transportation_cost"] > 0 else "negative"
        insights.append(
            f"Strong {direction} correlation between delivery delays and transportation costs — "
            "delays often coincide with cost spikes."
        )

    if abs(corr.loc["inventory_level", "delivery_delay"]) > 0.2:
        insights.append(
            "Inventory levels correlate with delivery delays — stockout risk increases as delays lengthen."
        )

    if abs(corr.loc["demand_forecast", "transportation_cost"]) > 0.25:
        insights.append(
            "Demand spikes are correlated with higher transportation costs — capacity constraints during peak demand."
        )

    high_delay_pct = (df["delivery_delay"] > 7).mean() * 100
    if high_delay_pct > 20:
        insights.append(f"{high_delay_pct:.1f}% of incidents have delays > 7 days — systemic delay pattern detected.")

    low_inv_pct = (df["inventory_level"] < 100).mean() * 100
    if low_inv_pct > 15:
        insights.append(f"{low_inv_pct:.1f}% of records show critically low inventory levels.")

    return insights[:5]
