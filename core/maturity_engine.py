from models.assessment import Finding, MaturityLevel, Severity

WEIGHTS = {
    Severity.CRITICAL: -1.0,
    Severity.HIGH: -0.5,
    Severity.MEDIUM: -0.25,
    Severity.LOW: -0.1,
}

class MaturityEngine:
    BASE = 3.5

    def __init__(self, findings, metrics):
        self.findings = findings
        self.metrics = metrics

    def calculate(self):
        score = self.BASE
        for f in self.findings:
            score += WEIGHTS.get(f.severity, 0)
        auth_pct = self.metrics.get("authenticated_scans_pct", 0)
        if auth_pct >= 90:
            score += 0.5
        elif auth_pct >= 70:
            score += 0.25
        score = round(max(1.0, min(5.0, score)), 2)
        return score, self._level(score)

    @staticmethod
    def _level(score):
        if score >= 4.5: return MaturityLevel.OPTIMIZED
        elif score >= 3.5: return MaturityLevel.MANAGED
        elif score >= 2.5: return MaturityLevel.DEFINED
        elif score >= 1.5: return MaturityLevel.DEVELOPING
        else: return MaturityLevel.INITIAL