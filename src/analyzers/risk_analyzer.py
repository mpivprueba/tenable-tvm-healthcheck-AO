"""
Risk analysis engine.
Transforms raw data into consulting insights.
"""

class RiskAnalyzer:

    def analyze(self, dataset):
        findings = []

        vuln_count = {}

        for vuln in dataset["vulnerabilities"]:
            asset = vuln["asset_id"]
            vuln_count[asset] = vuln_count.get(asset, 0) + 1

        for asset in dataset["assets"]:
            count = vuln_count.get(asset["id"], 0)

            findings.append({
                "asset": asset["hostname"],
                "criticality": asset["criticality"],
                "vulnerability_count": count,
                "risk_level": self._calculate_risk(asset["criticality"], count)
            })

        return findings

    def _calculate_risk(self, criticality, vuln_count):
        if criticality == "critical" and vuln_count >= 2:
            return "IMMEDIATE ACTION REQUIRED"

        if vuln_count >= 2:
            return "HIGH PRIORITY"

        if vuln_count == 1:
            return "MEDIUM PRIORITY"

        return "LOW"
