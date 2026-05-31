from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ShipmentStatus(str, Enum):
    ON_TIME = "On-Time"
    DELAYED = "Delayed"
    CRITICAL_DELAY = "Critical Delay"
    IN_TRANSIT = "In-Transit"
    DELIVERED = "Delivered"


class IncidentType(str, Enum):
    SUPPLIER_DELAY = "Supplier Delay"
    PORT_CONGESTION = "Port Congestion"
    STOCKOUT_RISK = "Stockout Risk"
    TRANSPORTATION_ISSUE = "Transportation Issue"
    DEMAND_SPIKE = "Demand Spike"
    QUALITY_ISSUE = "Quality Issue"
    WEATHER_DISRUPTION = "Weather Disruption"
    CUSTOMS_DELAY = "Customs Delay"


# ─── Request Models ────────────────────────────────────────────────────────────

class SearchQuery(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000, description="Natural language supply chain query")
    top_k: int = Field(default=5, ge=1, le=20)
    supplier_id: Optional[str] = None
    warehouse_location: Optional[str] = None
    shipment_status: Optional[ShipmentStatus] = None
    severity: Optional[SeverityLevel] = None
    incident_type: Optional[IncidentType] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    use_hybrid: bool = True

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Query must be at least 3 characters")
        return v


class RecommendationRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000)
    context_incidents: Optional[List[str]] = None
    supplier_id: Optional[str] = None
    severity: Optional[SeverityLevel] = None
    evaluate_quality: bool = False


class AgentAnalysisRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000)
    analysis_type: Optional[str] = None
    supplier_id: Optional[str] = None
    warehouse_location: Optional[str] = None
    include_all_agents: bool = True


class IngestionRequest(BaseModel):
    data_path: Optional[str] = None
    force_rebuild: bool = False


# ─── Response Models ───────────────────────────────────────────────────────────

class IncidentDocument(BaseModel):
    id: str
    content: str
    supplier_id: Optional[str] = None
    warehouse_location: Optional[str] = None
    shipment_status: Optional[str] = None
    severity: Optional[str] = None
    incident_type: Optional[str] = None
    delivery_delay: Optional[float] = None
    transportation_cost: Optional[float] = None
    inventory_level: Optional[float] = None
    timestamp: Optional[str] = None
    region: Optional[str] = None
    score: Optional[float] = None
    rank: Optional[int] = None


class SearchResponse(BaseModel):
    query: str
    results: List[IncidentDocument]
    total_found: int
    search_method: str
    latency_ms: float


class RiskScore(BaseModel):
    overall_score: float = Field(..., ge=0.0, le=1.0)
    supplier_risk: float = Field(..., ge=0.0, le=1.0)
    inventory_risk: float = Field(..., ge=0.0, le=1.0)
    shipment_risk: float = Field(..., ge=0.0, le=1.0)
    demand_risk: float = Field(..., ge=0.0, le=1.0)
    risk_level: SeverityLevel
    risk_factors: List[str]


class MitigationStep(BaseModel):
    priority: int
    action: str
    timeline: str
    owner: str
    expected_impact: str


class RecommendationResponse(BaseModel):
    query: str
    risk_assessment: RiskScore
    recommendations: List[MitigationStep]
    summary: str
    confidence_score: float
    evaluation_score: Optional[float] = None
    llm_judge_verdict: Optional[str] = None
    latency_ms: float


class AnomalyRecord(BaseModel):
    incident_id: str
    anomaly_score: float
    anomalous_features: List[str]
    description: str
    severity: str
    timestamp: Optional[str] = None


class AnomalyResponse(BaseModel):
    total_anomalies: int
    anomalies: List[AnomalyRecord]
    correlation_insights: List[str]
    detection_method: str


class AgentResult(BaseModel):
    agent_name: str
    agent_type: str
    findings: List[str]
    risk_score: float
    recommendations: List[str]
    escalated: bool = False
    escalation_reason: Optional[str] = None


class OrchestratorResponse(BaseModel):
    query: str
    agents_invoked: List[str]
    agent_results: List[AgentResult]
    consolidated_risk_score: float
    consolidated_recommendations: List[str]
    proactive_alerts: List[str]
    escalation_chain: List[str]
    summary: str
    latency_ms: float


class DashboardMetrics(BaseModel):
    total_incidents: int
    critical_incidents: int
    high_risk_suppliers: List[str]
    average_delivery_delay: float
    average_transportation_cost: float
    stockout_risk_locations: List[str]
    top_incident_types: Dict[str, int]
    severity_distribution: Dict[str, int]
    recent_anomalies: int
    disruption_trend: str


class HealthResponse(BaseModel):
    status: str
    version: str
    vector_store_ready: bool
    llm_connected: bool
    total_documents: int


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    code: int
