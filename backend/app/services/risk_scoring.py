from typing import List, Dict, Any
from app.models.schemas import RiskScore, SeverityLevel


def compute_risk_score(documents: List[Dict[str, Any]]) -> RiskScore:
    if not documents:
        return RiskScore(
            overall_score=0.0,
            supplier_risk=0.0,
            inventory_risk=0.0,
            shipment_risk=0.0,
            demand_risk=0.0,
            risk_level=SeverityLevel.LOW,
            risk_factors=[],
        )

    supplier_risk = 0.0
    inventory_risk = 0.0
    shipment_risk = 0.0
    demand_risk = 0.0
    risk_factors: List[str] = []

    delays = []
    inv_levels = []
    costs = []
    statuses = []
    severities = []

    for doc in documents:
        meta = doc.get("metadata", {})
        delays.append(float(meta.get("delivery_delay", 0)))
        inv_levels.append(float(meta.get("inventory_level", 500)))
        costs.append(float(meta.get("transportation_cost", 0)))
        statuses.append(str(meta.get("shipment_status", "")))
        severities.append(str(meta.get("severity", "low")).lower())

    avg_delay = sum(delays) / len(delays) if delays else 0
    avg_inv = sum(inv_levels) / len(inv_levels) if inv_levels else 500
    avg_cost = sum(costs) / len(costs) if costs else 0
    critical_count = sum(1 for s in severities if s == "critical")
    high_count = sum(1 for s in severities if s == "high")
    delayed_count = sum(1 for s in statuses if "delay" in s.lower())

    # Supplier risk: based on delays and severity
    if avg_delay > 14:
        supplier_risk = 0.9
        risk_factors.append(f"Critical supplier delays averaging {avg_delay:.1f} days")
    elif avg_delay > 7:
        supplier_risk = 0.65
        risk_factors.append(f"Significant supplier delays averaging {avg_delay:.1f} days")
    elif avg_delay > 3:
        supplier_risk = 0.4
        risk_factors.append(f"Moderate supplier delays averaging {avg_delay:.1f} days")
    else:
        supplier_risk = 0.15

    # Inventory risk: based on stock levels
    if avg_inv < 50:
        inventory_risk = 0.95
        risk_factors.append(f"Critical inventory shortage — average {avg_inv:.0f} units")
    elif avg_inv < 150:
        inventory_risk = 0.7
        risk_factors.append(f"Low inventory levels — average {avg_inv:.0f} units")
    elif avg_inv < 300:
        inventory_risk = 0.4
        risk_factors.append(f"Inventory approaching safety threshold — {avg_inv:.0f} units")
    else:
        inventory_risk = 0.15

    # Shipment risk: based on status and delays
    delay_ratio = delayed_count / len(statuses) if statuses else 0
    if delay_ratio > 0.6:
        shipment_risk = 0.85
        risk_factors.append(f"{delayed_count}/{len(statuses)} shipments delayed or critically delayed")
    elif delay_ratio > 0.3:
        shipment_risk = 0.55
        risk_factors.append(f"{delayed_count}/{len(statuses)} shipments experiencing delays")
    else:
        shipment_risk = 0.2

    # Demand risk: based on transportation cost spikes and demand vs inventory
    if avg_cost > 3000:
        demand_risk = 0.7
        risk_factors.append(f"High transportation costs averaging ${avg_cost:.0f}")
    elif avg_cost > 2000:
        demand_risk = 0.45
        risk_factors.append(f"Elevated transportation costs averaging ${avg_cost:.0f}")
    else:
        demand_risk = 0.2

    # Severity multiplier
    severity_mult = 1.0
    if critical_count > 0:
        severity_mult = 1.2
        risk_factors.append(f"{critical_count} critical severity incidents detected")
    elif high_count > 1:
        severity_mult = 1.1
        risk_factors.append(f"{high_count} high severity incidents detected")

    overall = min(
        (supplier_risk * 0.35 + inventory_risk * 0.3 + shipment_risk * 0.25 + demand_risk * 0.1)
        * severity_mult,
        1.0,
    )

    if overall >= 0.75:
        level = SeverityLevel.CRITICAL
    elif overall >= 0.5:
        level = SeverityLevel.HIGH
    elif overall >= 0.25:
        level = SeverityLevel.MEDIUM
    else:
        level = SeverityLevel.LOW

    return RiskScore(
        overall_score=round(overall, 3),
        supplier_risk=round(min(supplier_risk, 1.0), 3),
        inventory_risk=round(min(inventory_risk, 1.0), 3),
        shipment_risk=round(min(shipment_risk, 1.0), 3),
        demand_risk=round(min(demand_risk, 1.0), 3),
        risk_level=level,
        risk_factors=risk_factors[:6],
    )
