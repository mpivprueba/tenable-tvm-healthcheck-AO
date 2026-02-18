from loguru import logger
from config.settings import settings
from models.assessment import AssessmentSummary

class AINarrativeEngine:
    def __init__(self):
        self.enabled = settings.is_openai_configured()
        if not self.enabled:
            logger.warning("AI Narrative disabled — OPENAI_API_KEY not set.")

    def generate(self, summary: AssessmentSummary) -> str:
        if not self.enabled:
            return self._fallback(summary)
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            recs = "\n".join(f"{i+1}. {r.title}"
                            for i, r in enumerate(summary.recommendations[:5]))
            prompt = f"""You are a senior cybersecurity consultant from MPIV.
Write a 4-paragraph executive summary for {summary.customer_name}.
Maturity: {summary.maturity_level.value} ({summary.maturity_score}/5.0)
Assets: {summary.total_assets}
Authenticated coverage: {summary.authenticated_scans_pct:.1f}%
Critical findings: {len(summary.critical_findings)}
Total findings: {len(summary.findings)}
Top recommendations:
{recs}
Write in formal English prose. No bullet points."""

            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4, max_tokens=800,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            return self._fallback(summary)

    def _fallback(self, summary):
        return (
            f"MPIV conducted a Tenable VM Health Check for {summary.customer_name} "
            f"on {summary.assessment_date.strftime('%B %d, %Y')}. "
            f"The assessment identified {len(summary.findings)} findings including "
            f"{len(summary.critical_findings)} critical issues. "
            f"Maturity level: {summary.maturity_level.value} ({summary.maturity_score}/5.0).\n\n"
            f"Immediate action is required on critical findings. MPIV recommends a "
            f"structured 90-day remediation roadmap beginning with quick-win items."
        )