from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class MaturityLevel(str, Enum):
    INITIAL = "Initial"
    DEVELOPING = "Developing"
    DEFINED = "Defined"
    MANAGED = "Managed"
    OPTIMIZED = "Optimized"

class FindingCategory(str, Enum):
    SCANNER_HEALTH = "Scanner Health"
    SCAN_POLICY = "Scan Policy"
    CREDENTIAL_COVERAGE = "Credential Coverage"
    ASSET_COVERAGE = "Asset Coverage"
    TAG_MANAGEMENT = "Tag Management"
    PROGRAM_MATURITY = "Program Maturity"

class Finding(BaseModel):
    id: str
    title: str
    category: FindingCategory
    severity: Severity
    description: str
    evidence: Optional[str] = None
    recommendation: str
    effort: str

class Recommendation(BaseModel):
    priority: int
    title: str
    description: str
    findings_refs: list[str] = Field(default_factory=list)
    type: str

class AssessmentSummary(BaseModel):
    customer_name: str
    engagement_id: str
    assessment_date: datetime = Field(default_factory=datetime.utcnow)
    maturity_level: MaturityLevel
    maturity_score: float
    total_assets: int = 0
    authenticated_scans_pct: float = 0.0
    scanner_health_pct: float = 0.0
    findings: list[Finding] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    executive_narrative: Optional[str] = None

    @property
    def critical_findings(self):
        return [f for f in self.findings if f.severity == Severity.CRITICAL]

    @property
    def high_findings(self):
        return [f for f in self.findings if f.severity == Severity.HIGH]