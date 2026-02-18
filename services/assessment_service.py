from datetime import datetime
from loguru import logger
from config.settings import settings
from integrations.tenable_client import TenableClient
from analyzers.gap_analyzer import GapAnalyzer
from core.maturity_engine import MaturityEngine
from core.recommendation_engine import RecommendationEngine
from services.ai_narrative import AINarrativeEngine
from models.assessment import AssessmentSummary

class AssessmentService:
    def __init__(self):
        self.client = TenableClient()
        self.ai = AINarrativeEngine()

    def run(self) -> AssessmentSummary:
        logger.info(f"Assessment started for: {settings.CUSTOMER_NAME}")

        scanners = self.client.get_scanners()
        assets = self.client.get_assets()
        scans = self.client.get_scans()
        policies = self.client.get_policies()
        tags = self.client.get_tags()

        findings = GapAnalyzer(scanners, assets, scans, policies, tags).run_all_checks()

        healthy = sum(1 for s in scanners if s.get("status") == "on" and s.get("linked"))
        scanner_health_pct = (healthy / len(scanners) * 100) if scanners else 0

        auth = sum(1 for s in scans if s.get("credential_enabled"))
        auth_pct = (auth / len(scans) * 100) if scans else 0

        metrics = {
            "authenticated_scans_pct": round(auth_pct, 1),
            "scanner_health_pct": round(scanner_health_pct, 1),
        }

        score, level = MaturityEngine(findings, metrics).calculate()
        recommendations = RecommendationEngine(findings).generate()

        summary = AssessmentSummary(
            customer_name=settings.CUSTOMER_NAME,
            engagement_id=settings.ENGAGEMENT_ID,
            assessment_date=datetime.utcnow(),
            maturity_level=level,
            maturity_score=score,
            total_assets=len(assets),
            authenticated_scans_pct=auth_pct,
            scanner_health_pct=scanner_health_pct,
            findings=findings,
            recommendations=recommendations,
        )

        summary.executive_narrative = self.ai.generate(summary)
        logger.info("Assessment complete.")
        return summary