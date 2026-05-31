"""
Generates a realistic synthetic supply chain dataset (supply_chain_data.csv).
Run: python -m app.data.generate_sample
"""

import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)
np.random.seed(42)

SUPPLIERS = [f"S{str(i).zfill(3)}" for i in range(1, 21)]

WAREHOUSES = [
    "New York, NY", "Los Angeles, CA", "Chicago, IL", "Houston, TX",
    "Phoenix, AZ", "Philadelphia, PA", "San Antonio, TX", "San Diego, CA",
    "Dallas, TX", "San Jose, CA", "Austin, TX", "Seattle, WA",
]

REGIONS = {
    "New York, NY": "Northeast", "Philadelphia, PA": "Northeast",
    "Chicago, IL": "Midwest", "Houston, TX": "South",
    "Phoenix, AZ": "Southwest", "San Antonio, TX": "South",
    "Dallas, TX": "South", "Los Angeles, CA": "West",
    "San Diego, CA": "West", "San Jose, CA": "West",
    "Austin, TX": "South", "Seattle, WA": "Northwest",
}

INCIDENT_TYPES = [
    "Supplier Delay", "Port Congestion", "Stockout Risk",
    "Transportation Issue", "Demand Spike", "Quality Issue",
    "Weather Disruption", "Customs Delay",
]

SHIPMENT_STATUSES = ["On-Time", "Delayed", "Critical Delay", "In-Transit", "Delivered"]

PRODUCT_CATEGORIES = [
    "Electronics", "Automotive Parts", "Medical Supplies", "Consumer Goods",
    "Industrial Equipment", "Food & Beverage", "Pharmaceuticals", "Raw Materials",
]

INCIDENT_DESCRIPTIONS = {
    "Supplier Delay": [
        "{supplier} reported production line shutdown due to equipment failure causing {delay}-day delivery delay.",
        "Supplier {supplier} experiencing raw material shortage resulting in {delay}-day shipment delay for {product} components.",
        "{supplier} labor dispute affecting production capacity, estimated {delay}-day delay on outstanding orders.",
        "Quality control issues at {supplier} facility halted production for {delay} days pending inspection.",
    ],
    "Port Congestion": [
        "Port congestion at {warehouse} terminal causing {delay}-day backlog for incoming shipments.",
        "Vessel berthing delays at {warehouse} port increasing transit times by {delay} days.",
        "Customs inspection backlog at {warehouse} customs facility delaying {product} clearance by {delay} days.",
        "Labor strike at {warehouse} port operations causing significant {delay}-day shipping delays.",
    ],
    "Stockout Risk": [
        "Inventory for {product} at {warehouse} warehouse approaching critical threshold — current level at {inv_level} units.",
        "{warehouse} distribution center reporting {product} stock depletion risk within {delay} days at current consumption rate.",
        "Safety stock breach detected at {warehouse} for {product} category; replenishment order placed with {supplier}.",
        "Demand surge exceeding supply at {warehouse} — {product} inventory at {inv_level} units vs {demand} forecasted demand.",
    ],
    "Transportation Issue": [
        "Truck fleet shortage affecting last-mile delivery from {warehouse}, {delay}-day delay on {product} orders.",
        "Route disruption due to road construction near {warehouse} increasing delivery time by {delay} days.",
        "Carrier capacity constraints impacting shipments from {supplier} to {warehouse} — {delay}-day estimated delay.",
        "Fuel price spike increasing transportation costs by {cost_pct}% for {warehouse} region shipments.",
    ],
    "Demand Spike": [
        "Unexpected {product} demand increase at {warehouse} region — {demand} units ordered vs {inv_level} in stock.",
        "Seasonal demand surge for {product} exceeding forecast by {cost_pct}% at {warehouse} fulfillment center.",
        "Flash sale event triggering {cost_pct}% above-forecast demand for {product} — inventory risk at {warehouse}.",
        "B2B bulk order from key account straining {product} availability across {warehouse} distribution network.",
    ],
    "Quality Issue": [
        "Batch quality failure detected for {product} from {supplier} — {delay}-day hold pending quality review.",
        "{supplier} reported defect rate of {cost_pct}% in recent {product} shipment, return and rework initiated.",
        "Product recall risk identified for {product} batch from {supplier} — proactive hold at {warehouse}.",
        "Material specification deviation in {supplier} {product} delivery requiring re-inspection and approval.",
    ],
    "Weather Disruption": [
        "Severe weather event impacting {warehouse} region causing {delay}-day operational disruption.",
        "Hurricane warning at {warehouse} port resulting in {delay}-day suspension of loading operations.",
        "Winter storm affecting ground transportation near {warehouse}, {delay}-day delivery delay expected.",
        "Flooding at {warehouse} warehouse facility causing {delay}-day shutdown and inventory relocation.",
    ],
    "Customs Delay": [
        "Customs documentation error for {supplier} shipment causing {delay}-day clearance delay at {warehouse}.",
        "Trade compliance review triggered for {product} shipment from {supplier} — {delay}-day estimated hold.",
        "New import regulations requiring additional certification for {product} category — {delay}-day processing time.",
        "Tariff classification dispute for {supplier} shipment adding {delay}-day delay at {warehouse} customs.",
    ],
}


def severity_from_delay(delay: float, inv_level: float, status: str) -> str:
    if status == "Critical Delay" or delay > 14 or inv_level < 50:
        return "critical"
    elif delay > 7 or inv_level < 150:
        return "high"
    elif delay > 3 or inv_level < 300:
        return "medium"
    return "low"


def generate_dataset(n_records: int = 600) -> pd.DataFrame:
    records = []
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2026, 5, 1)
    date_range = (end_date - start_date).days

    for i in range(n_records):
        supplier = random.choice(SUPPLIERS)
        warehouse = random.choice(WAREHOUSES)
        region = REGIONS[warehouse]
        incident_type = random.choice(INCIDENT_TYPES)
        product = random.choice(PRODUCT_CATEGORIES)

        inv_level = max(0, np.random.exponential(300))
        delivery_delay = max(0, np.random.exponential(5) if random.random() > 0.3 else np.random.exponential(12))
        transport_cost = max(100, np.random.normal(1500, 600))
        order_qty = max(10, int(np.random.normal(200, 80)))
        demand_forecast = max(10, int(order_qty * np.random.uniform(0.7, 1.4)))

        if incident_type in ("Stockout Risk", "Demand Spike"):
            inv_level = max(0, np.random.exponential(100))

        if incident_type in ("Port Congestion", "Customs Delay", "Weather Disruption"):
            delivery_delay = max(1, np.random.exponential(10))

        status_weights = [0.3, 0.3, 0.15, 0.15, 0.1]
        if delivery_delay > 10:
            status_weights = [0.05, 0.35, 0.4, 0.15, 0.05]
        elif delivery_delay > 5:
            status_weights = [0.1, 0.4, 0.2, 0.2, 0.1]
        status = random.choices(SHIPMENT_STATUSES, weights=status_weights)[0]

        severity = severity_from_delay(delivery_delay, inv_level, status)

        desc_template = random.choice(INCIDENT_DESCRIPTIONS[incident_type])
        description = desc_template.format(
            supplier=supplier,
            warehouse=warehouse,
            product=product,
            delay=int(delivery_delay),
            inv_level=int(inv_level),
            demand=demand_forecast,
            cost_pct=round(random.uniform(5, 40), 1),
        )

        resolution_days = max(1, int(delivery_delay * random.uniform(1.2, 2.5)))
        timestamp = start_date + timedelta(days=random.randint(0, date_range))

        records.append({
            "incident_id": f"INC{str(i + 1).zfill(5)}",
            "supplier_id": supplier,
            "warehouse_location": warehouse,
            "region": region,
            "incident_type": incident_type,
            "product_category": product,
            "shipment_status": status,
            "severity": severity,
            "inventory_level": round(inv_level, 2),
            "delivery_delay": round(delivery_delay, 2),
            "transportation_cost": round(transport_cost, 2),
            "order_quantity": order_qty,
            "demand_forecast": demand_forecast,
            "resolution_time_days": resolution_days,
            "timestamp": timestamp.strftime("%Y-%m-%d"),
            "incident_description": description,
        })

    df = pd.DataFrame(records)
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def main():
    output_path = Path(__file__).parent.parent.parent / "data" / "supply_chain_data.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df = generate_dataset(600)
    df.to_csv(output_path, index=False)
    print(f"Generated {len(df)} supply chain incident records -> {output_path}")
    print(df[["incident_type", "severity", "shipment_status"]].value_counts().head(20).to_string())


if __name__ == "__main__":
    main()
