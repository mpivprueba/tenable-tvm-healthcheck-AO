from src.collectors.vm_collector import VMCollector
from src.analyzers.risk_analyzer import RiskAnalyzer


class AssessmentEngine:

    def run(self):
        print("Starting Assessment...")

        collector = VMCollector()
        analyzer = RiskAnalyzer()

        dataset = collector.collect()
        findings = analyzer.analyze(dataset)

        self._print_findings(findings)

    def _print_findings(self, findings):
        print("\n--- Assessment Results ---\n")

        for f in findings:
            print(f"Asset: {f['asset']}")
            print(f"Criticality: {f['criticality']}")
            print(f"Vulnerabilities: {f['vulnerability_count']}")
            print(f"Risk: {f['risk_level']}")
            print("----------------------------")
