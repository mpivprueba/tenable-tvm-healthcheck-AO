from models.assessment import Finding, Recommendation, Severity

PRIORITY = {Severity.CRITICAL: 1, Severity.HIGH: 2,
            Severity.MEDIUM: 3, Severity.LOW: 4}
EFFORT_TYPE = {"low": "quick-win", "medium": "strategic", "high": "roadmap"}

class RecommendationEngine:
    def __init__(self, findings):
        self.findings = findings

    def generate(self):
        by_category = {}
        for f in self.findings:
            by_category.setdefault(f.category, []).append(f)

        recs = []
        for category, items in by_category.items():
            items.sort(key=lambda f: PRIORITY.get(f.severity, 5))
            top = items[0]
            lines = [f"• [{f.severity.upper()}] {f.recommendation}" for f in items[:3]]
            recs.append(Recommendation(
                priority=PRIORITY.get(top.severity, 5),
                title=f"Remediate {category.value} ({len(items)} finding(s))",
                description="\n".join(lines),
                findings_refs=[f.id for f in items],
                type=EFFORT_TYPE.get(top.effort, "strategic"),
            ))

        recs.sort(key=lambda r: r.priority)
        for i, r in enumerate(recs, 1):
            r.priority = i
        return recs