from typing import List, Dict, Any
import pandas as pd
import tiktoken


_TOKENIZER = None

def _get_tokenizer():
    global _TOKENIZER
    if _TOKENIZER is None:
        _TOKENIZER = tiktoken.get_encoding("cl100k_base")
    return _TOKENIZER


def count_tokens(text: str) -> int:
    return len(_get_tokenizer().encode(text))


def row_to_document(row: pd.Series) -> Dict[str, Any]:
    """Convert a DataFrame row into a structured document for embedding."""
    parts = [row.get("incident_description", "")]

    if row.get("incident_type") and row["incident_type"] != "Unknown":
        parts.append(f"Incident Type: {row['incident_type']}")
    if row.get("supplier_id") and row["supplier_id"] != "Unknown":
        parts.append(f"Supplier: {row['supplier_id']}")
    if row.get("warehouse_location") and row["warehouse_location"] != "Unknown":
        parts.append(f"Warehouse: {row['warehouse_location']}")
    if row.get("region") and row["region"] != "Unknown":
        parts.append(f"Region: {row['region']}")
    if row.get("shipment_status") and row["shipment_status"] != "Unknown":
        parts.append(f"Status: {row['shipment_status']}")
    if row.get("severity") and row["severity"] != "Unknown":
        parts.append(f"Severity: {row['severity']}")
    if pd.notna(row.get("delivery_delay")) and float(row.get("delivery_delay", 0)) > 0:
        parts.append(f"Delivery Delay: {row['delivery_delay']} days")
    if pd.notna(row.get("inventory_level")):
        parts.append(f"Inventory Level: {row['inventory_level']} units")
    if pd.notna(row.get("transportation_cost")):
        parts.append(f"Transportation Cost: ${row['transportation_cost']:.2f}")
    if row.get("product_category"):
        parts.append(f"Product Category: {row['product_category']}")
    if row.get("timestamp") and row["timestamp"] != "Unknown":
        parts.append(f"Date: {row['timestamp']}")

    content = ". ".join(filter(None, parts))

    metadata = {
        "incident_id": str(row.get("incident_id", "")),
        "supplier_id": str(row.get("supplier_id", "Unknown")),
        "warehouse_location": str(row.get("warehouse_location", "Unknown")),
        "shipment_status": str(row.get("shipment_status", "Unknown")),
        "severity": str(row.get("severity", "Unknown")),
        "incident_type": str(row.get("incident_type", "Unknown")),
        "region": str(row.get("region", "Unknown")),
        "product_category": str(row.get("product_category", "Unknown")),
        "delivery_delay": float(row.get("delivery_delay", 0.0)),
        "inventory_level": float(row.get("inventory_level", 0.0)),
        "transportation_cost": float(row.get("transportation_cost", 0.0)),
        "order_quantity": float(row.get("order_quantity", 0.0)),
        "demand_forecast": float(row.get("demand_forecast", 0.0)),
        "risk_score": float(row.get("risk_score", 0.0)),
        "timestamp": str(row.get("timestamp", "Unknown")),
        "token_count": count_tokens(content),
    }

    return {"id": metadata["incident_id"], "content": content, "metadata": metadata}


def dataframe_to_documents(df: pd.DataFrame) -> List[Dict[str, Any]]:
    return [row_to_document(row) for _, row in df.iterrows()]


def truncate_context(documents: List[Dict[str, Any]], max_tokens: int = 6000) -> List[Dict[str, Any]]:
    """Select as many top-ranked documents as fit within the token budget."""
    selected = []
    used_tokens = 0
    for doc in documents:
        tokens = doc["metadata"].get("token_count", count_tokens(doc["content"]))
        if used_tokens + tokens > max_tokens:
            break
        selected.append(doc)
        used_tokens += tokens
    return selected
