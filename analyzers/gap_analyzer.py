from datetime import datetime, timezone
from loguru import logger
from models.assessment import Finding, Severity, FindingCategory

class GapAnalyzer:
    def __init__(self, scanners, assets, scans, policies, tags):
        self.scanners = scanners
        self.assets = assets
        self.scans = scans
        self.policies = policies
        self.tags = tags
        self.findings = []
        self._counter = 0

    def run_all_checks(self):
        logger.info("Running gap analysis checks...")
        self._check_scanner_health()
        self._check_scanner_linking()
        self._check_credential_coverage()
        self._check_asset_staleness()
        self._check_asset_tagging()
        self._check_scan_frequency()
        logger.info(f"Gap analysis complete: {len(self.findings)} findings.")
        return self.findings

    def _check_scanner_health(self):
        offline = [s for s in self.scanners if s.get("status") != "on"]
        if offline:
            self._add(
                title=f"{len(offline)} Scanner(s) Offline",
                category=FindingCategory.SCANNER_HEALTH,
                severity=Severity.HIGH,
                description="Offline scanners create blind spots in coverage.",
                evidence=str([s["name"] for s in offline]),
                recommendation="Restore offline scanners and verify connectivity.",
                effort="medium"
            )

    def _check_scanner_linking(self):
        unlinked = [s for s in self.scanners if not s.get("linked")]
        if unlinked:
            self._add(
                title=f"{len(unlinked)} Scanner(s) Not Linked to TVM",
                category=FindingCategory.SCANNER_HEALTH,
                severity=Severity.CRITICAL,
                description="Unlinked scanners cannot run scans or report findings.",
                evidence=str([s["name"] for s in unlinked]),
                recommendation="Re-link scanners using a valid Linking Key from Tenable.io.",
                effort="low"
            )

    def _check_credential_coverage(self):
        unauthenticated = [s for s in self.scans if not s.get("credential_enabled")]
        if unauthenticated:
            self._add(
                title=f"{len(unauthenticated)} Scan(s) Without Credentials",
                category=FindingCategory.CREDENTIAL_COVERAGE,
                severity=Severity.CRITICAL,
                description="Unauthenticated scans detect only ~30% of vulnerabilities.",
                evidence=str([s["name"] for s in unauthenticated]),
                recommendation="Configure credential sets for all internal scans.",
                effort="high"
            )

    def _check_asset_staleness(self):
        now = datetime.now(timezone.utc)
        stale = []
        for asset in self.assets:
            last_seen = asset.get("last_seen")
            if not last_seen:
                continue
            last_dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
            if (now - last_dt).days > 90:
                stale.append(asset.get("fqdn", "unknown"))
        if stale:
            pct = round(len(stale) / len(self.assets) * 100, 1)
            self._add(
                title=f"{len(stale)} Stale Assets ({pct}% of inventory)",
                category=FindingCategory.ASSET_COVERAGE,
                severity=Severity.MEDIUM,
                description="Assets not seen in 90+ days may be ghost assets or coverage gaps.",
                evidence=f"Sample: {stale[:3]}",
                recommendation="Audit stale assets and enable asset aging policy.",
                effort="medium"
            )

    def _check_asset_tagging(self):
        untagged = [a for a in self.assets if not a.get("tags")]
        if untagged:
            pct = round(len(untagged) / len(self.assets) * 100, 1)
            self._add(
                title=f"{len(untagged)} Assets Without Tags ({pct}%)",
                category=FindingCategory.TAG_MANAGEMENT,
                severity=Severity.MEDIUM if pct < 50 else Severity.HIGH,
                description="Untagged assets cannot be targeted by dynamic access groups.",
                evidence=f"{pct}% of assets have no classification tags.",
                recommendation="Define tagging taxonomy and apply Tag Propagation rules.",
                effort="high"
            )

    def _check_scan_frequency(self):
        now = datetime.now(timezone.utc)
        stale = []
        for scan in self.scans:
            last_run = scan.get("last_run")
            if not last_run:
                stale.append(scan["name"])
                continue
            last_dt = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
            if (now - last_dt).days > 30:
                stale.append(scan["name"])
        if stale:
            self._add(
                title=f"{len(stale)} Scan(s) Not Run in 30+ Days",
                category=FindingCategory.SCAN_POLICY,
                severity=Severity.HIGH,
                description="Stale scans leave assets unassessed.",
                evidence=str(stale),
                recommendation="Implement automated weekly scan schedules.",
                effort="low"
            )

    def _add(self, title, category, severity, description,
             recommendation, effort, evidence=None):
        self._counter += 1
        self.findings.append(Finding(
            id=f"F-{self._counter:03d}",
            title=title,
            category=category,
            severity=severity,
            description=description,
            evidence=evidence,
            recommendation=recommendation,
            effort=effort,
        ))