import pandas as pd
import numpy as np
from typing import Optional
from pathlib import Path


def load_and_clean(data_path: str) -> pd.DataFrame:
    path = Path(data_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found at {data_path}")

    df = pd.read_csv(path)

    required_cols = {"supplier_id", "incident_description"}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"Dataset missing required columns: {required_cols - set(df.columns)}")

    df["inventory_level"] = pd.to_numeric(df.get("inventory_level", 0), errors="coerce").fillna(0)
    df["delivery_delay"] = pd.to_numeric(df.get("delivery_delay", 0), errors="coerce").fillna(0)
    df["transportation_cost"] = pd.to_numeric(df.get("transportation_cost", 0), errors="coerce").fillna(0)
    df["order_quantity"] = pd.to_numeric(df.get("order_quantity", 0), errors="coerce").fillna(0)
    df["demand_forecast"] = pd.to_numeric(df.get("demand_forecast", 0), errors="coerce").fillna(0)

    for col in ["supplier_id", "warehouse_location", "shipment_status", "severity",
                "incident_type", "region", "product_category"]:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown").astype(str).str.strip()

    if "incident_id" not in df.columns:
        df["incident_id"] = [f"INC{str(i).zfill(5)}" for i in range(len(df))]

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%d").fillna("Unknown")

    df = df.drop_duplicates(subset=["incident_id"]).reset_index(drop=True)
    return df


def compute_risk_score(row: pd.Series) -> float:
    score = 0.0
    delay = float(row.get("delivery_delay", 0))
    inv = float(row.get("inventory_level", 500))
    status = str(row.get("shipment_status", ""))
    severity = str(row.get("severity", "low")).lower()

    if delay > 14:
        score += 0.4
    elif delay > 7:
        score += 0.3
    elif delay > 3:
        score += 0.2
    elif delay > 0:
        score += 0.1

    if inv < 50:
        score += 0.3
    elif inv < 150:
        score += 0.2
    elif inv < 300:
        score += 0.1

    if status == "Critical Delay":
        score += 0.2
    elif status == "Delayed":
        score += 0.1

    severity_map = {"low": 0.0, "medium": 0.1, "high": 0.2, "critical": 0.3}
    score += severity_map.get(severity, 0.0)

    return min(round(score, 3), 1.0)


def enrich_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df["risk_score"] = df.apply(compute_risk_score, axis=1)

    if "inventory_level" in df.columns and "order_quantity" in df.columns:
        df["inventory_turnover"] = np.where(
            df["order_quantity"] > 0,
            df["inventory_level"] / df["order_quantity"].replace(0, np.nan),
            np.nan,
        )

    if "delivery_delay" in df.columns and "resolution_time_days" in df.columns:
        df["delay_ratio"] = (
            df["delivery_delay"] / df["resolution_time_days"].replace(0, np.nan)
        ).fillna(0)

    return df
