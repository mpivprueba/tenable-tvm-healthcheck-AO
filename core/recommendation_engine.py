from models.assessment import Finding, Recommendation, Severity, FindingCategory

PRIORITY = {Severity.CRITICAL: 1, Severity.HIGH: 2,
            Severity.MEDIUM: 3, Severity.LOW: 4}

# Clasificación por CATEGORÍA — no por esfuerzo
CATEGORY_TYPE = {
    FindingCategory.SCANNER_HEALTH:      "quick-win",   # 30 días — impacto inmediato
    FindingCategory.SCAN_POLICY:         "quick-win",   # 30 días — solo activar schedules
    FindingCategory.CREDENTIAL_COVERAGE: "strategic",   # 60 días — requiere coordinación
    FindingCategory.ASSET_COVERAGE:      "strategic",   # 60 días — auditoría y cleanup
    FindingCategory.TAG_MANAGEMENT:      "roadmap",     # 90 días — taxonomía y governance
}


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
                type=CATEGORY_TYPE.get(category, "strategic"),
            ))

        recs.sort(key=lambda r: r.priority)
        for i, r in enumerate(recs, 1):
            r.priority = i
        return recs