import re
from datetime import datetime, timezone
from loguru import logger
from models.assessment import Finding, Severity, FindingCategory

_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.IGNORECASE
)

def _is_readable_name(name: str) -> bool:
    if not name or not name.strip():
        return False
    if _UUID_RE.match(name.strip()):
        return False
    return True


def _truncate_evidence(items: list, max_items: int = 5) -> str:
    readable = [str(i) for i in items if _is_readable_name(str(i))]
    total = len(items)
    if not readable:
        return f"{total} items (names not available)"
    sample = readable[:max_items]
    remaining = total - len(sample)
    if remaining > 0:
        return f"{', '.join(sample)} (+ {remaining} more)"
    return ', '.join(sample)


class GapAnalyzer:
    def __init__(self, scanners, assets, scans, policies, tags,
                 credentials=None, networks=None):
        self.scanners    = scanners
        self.assets      = assets
        self.scans       = scans
        self.policies    = policies
        self.tags        = tags
        self.credentials = credentials or []
        self.networks    = networks    or []
        self.findings    = []
        self._counter    = 0

    def run_all_checks(self):
        logger.info("Running gap analysis checks...")
        self._check_scanner_health()
        self._check_scanner_linking()
        self._check_credential_coverage()
        self._check_credentials_configured()
        self._check_networks()
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
                evidence=_truncate_evidence([s["name"] for s in offline]),
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
                evidence=_truncate_evidence([s["name"] for s in unlinked]),
                recommendation="Re-link scanners using a valid Linking Key from Tenable.io.",
                effort="low"
            )

    def _check_credential_coverage(self):
        # Scans fantasma — nunca han corrido (status=empty)
        ghosts = [s for s in self.scans if s.get("is_ghost")]
        # Scans activos sin credenciales
        active = [s for s in self.scans if not s.get("is_ghost")]
        unauthenticated = [s for s in active if not s.get("credential_enabled")]
        total = len(self.scans)

        # Finding 1: Scans Fantasma
        if ghosts:
            ghost_pct = round(len(ghosts) / total * 100, 1)
            self._add(
                title=f"{len(ghosts)} Ghost Scan(s) — Never Executed ({ghost_pct}%)",
                category=FindingCategory.CREDENTIAL_COVERAGE,
                severity=Severity.CRITICAL,
                description=(
                    f"{len(ghosts)} of {total} scans ({ghost_pct}%) have status 'empty' — "
                    "they were created but have NEVER run. They consume scan slots, "
                    "inflate the scan count, and provide zero security coverage."
                ),
                evidence=_truncate_evidence([s["name"] for s in ghosts], max_items=5),
                recommendation=(
                    "Audit and delete ghost scans. Keep only scans with an active schedule. "
                    "Implement a scan hygiene policy: delete any scan unused for 90+ days."
                ),
                effort="medium"
            )

        # Finding 2: Scans activos sin credenciales
        if unauthenticated:
            active_total = len(active)
            pct = round(len(unauthenticated) / active_total * 100, 1) if active_total else 0
            self._add(
                title=f"{len(unauthenticated)} Active Scan(s) Without Credentials",
                category=FindingCategory.CREDENTIAL_COVERAGE,
                severity=Severity.CRITICAL if pct > 50 else Severity.HIGH,
                description=(
                    f"{len(unauthenticated)} of {active_total} active scans ({pct}%) run "
                    "unauthenticated. Unauthenticated scans detect only ~30% of vulnerabilities. "
                    f"({len(active) - len(unauthenticated)} active scans have credentials.)"
                ),
                evidence=_truncate_evidence([s["name"] for s in unauthenticated], max_items=5),
                recommendation="Configure credential sets for all internal network scans.",
                effort="high"
            )

    # ✅ NUEVO — Verifica si hay credenciales configuradas en el tenant
    def _check_credentials_configured(self):
        if not self.credentials:
            self._add(
                title="No Shared Credentials Configured",
                category=FindingCategory.CREDENTIAL_COVERAGE,
                severity=Severity.HIGH,
                description=(
                    "No shared credentials are configured in the tenant. "
                    "Without shared credentials, each scan requires individual "
                    "credential configuration, increasing operational overhead."
                ),
                evidence="0 credential sets found via credentials API.",
                recommendation=(
                    "Configure at least one Windows (domain) and one SSH credential set. "
                    "Enable Shared Credentials so all scans can inherit them automatically."
                ),
                effort="medium"
            )
        else:
            def _ctype(c):
                try:
                    return str(c.get("type", "Unknown")) if hasattr(c, "get") else str(c)
                except Exception:
                    return "Unknown"
            types = list({_ctype(c) for c in self.credentials})
            has_windows = any("windows" in _ctype(c).lower() for c in self.credentials)
            has_ssh     = any("ssh" in _ctype(c).lower() for c in self.credentials)
            missing = []
            if not has_windows:
                missing.append("Windows")
            if not has_ssh:
                missing.append("SSH/Linux")
            if missing:
                self._add(
                    title=f"Missing Credential Types: {', '.join(missing)}",
                    category=FindingCategory.CREDENTIAL_COVERAGE,
                    severity=Severity.MEDIUM,
                    description=(
                        f"Credential types {missing} are not configured. "
                        f"Only {types} credentials found ({len(self.credentials)} total). "
                        "Incomplete credential coverage reduces vulnerability detection."
                    ),
                    evidence=f"{len(self.credentials)} credential set(s): {', '.join(types)}",
                    recommendation=f"Add {' and '.join(missing)} credential sets to cover all OS types.",
                    effort="medium"
                )

    # ✅ NUEVO — Verifica configuración de redes
    def _check_networks(self):
        if not self.networks:
            return
        default_only = all(n.get("is_default", False) for n in self.networks)
        empty_networks = [n for n in self.networks if n.get("asset_count", 0) == 0
                         and not n.get("is_default")]
        if default_only and len(self.networks) == 1:
            self._add(
                title="Only Default Network Configured",
                category=FindingCategory.ASSET_COVERAGE,
                severity=Severity.MEDIUM,
                description=(
                    "Only the Default network is configured. Separate networks improve "
                    "asset segmentation, scanner assignment, and access control."
                ),
                evidence="1 network found: Default (is_default=True).",
                recommendation=(
                    "Create dedicated networks per segment (e.g., HQ, DMZ, Cloud). "
                    "Assign specific scanners to each network for better coverage."
                ),
                effort="medium"
            )
        elif empty_networks:
            names = _truncate_evidence([n["name"] for n in empty_networks])
            self._add(
                title=f"{len(empty_networks)} Network(s) With No Assets",
                category=FindingCategory.ASSET_COVERAGE,
                severity=Severity.LOW,
                description=(
                    f"{len(empty_networks)} configured network(s) have no assets assigned. "
                    "Empty networks may indicate misconfiguration or abandoned segments."
                ),
                evidence=f"Empty networks: {names}",
                recommendation="Review and clean up empty networks or assign assets.",
                effort="low"
            )

    def _check_asset_staleness(self):
        now = datetime.now(timezone.utc)

        def days_since(iso_str):
            if not iso_str:
                return 999
            try:
                return (now - datetime.fromisoformat(iso_str.replace("Z", "+00:00"))).days
            except Exception:
                return 999

        def asset_name(a):
            return (a.get("name") or a.get("fqdn") or
                    a.get("hostname") or a.get("ipv4") or "unknown")

        total = len(self.assets)

        # Tier 1: Zombie > 90 días sin actividad
        zombies = [a for a in self.assets if days_since(a.get("last_seen")) > 90]

        # Tier 2: Stale 30-90 días
        stale = [a for a in self.assets
                 if 30 < days_since(a.get("last_seen")) <= 90]

        # Tier 3: Cloud assets nunca escaneados
        cloud_unscanned = [
            a for a in self.assets
            if a.get("source") in ("CloudDiscoveryConnector", "AWS", "AZURE", "GCP")
            and not a.get("last_authenticated_scan_date")
            and not a.get("has_plugin_results")
        ]

        # Tier 4: Assets sin autenticación real (last_authenticated_scan_date=None)
        no_auth_scan = [
            a for a in self.assets
            if not a.get("last_authenticated_scan_date")
            and a.get("has_plugin_results")
        ]

        if zombies:
            pct = round(len(zombies) / total * 100, 1)
            self._add(
                title=f"{len(zombies)} Zombie Asset(s) — No Activity >90 Days ({pct}%)",
                category=FindingCategory.ASSET_COVERAGE,
                severity=Severity.CRITICAL if pct > 30 else Severity.HIGH,
                description=(
                    f"{len(zombies)} assets ({pct}%) have not been seen in 90+ days. "
                    "These zombie assets consume licenses without generating security value. "
                    "They represent either decommissioned systems or coverage blind spots."
                ),
                evidence=_truncate_evidence([asset_name(a) for a in zombies], max_items=5),
                recommendation=(
                    "Enable Asset Aging policy in Tenable (Settings > General > Asset Management). "
                    "Set auto-delete for assets not seen in 90 days. "
                    "Review if decommissioned assets should be terminated."
                ),
                effort="medium"
            )

        if stale:
            pct = round(len(stale) / total * 100, 1)
            self._add(
                title=f"{len(stale)} Stale Asset(s) — No Activity 30-90 Days ({pct}%)",
                category=FindingCategory.ASSET_COVERAGE,
                severity=Severity.MEDIUM,
                description=(
                    f"{len(stale)} assets ({pct}%) have not been seen in 30-90 days. "
                    "These may indicate intermittent connectivity or scanner coverage gaps."
                ),
                evidence=_truncate_evidence([asset_name(a) for a in stale], max_items=5),
                recommendation="Verify scanner reachability for these assets. Check scan schedules.",
                effort="low"
            )

        if cloud_unscanned:
            self._add(
                title=f"{len(cloud_unscanned)} Cloud Asset(s) Never Scanned",
                category=FindingCategory.ASSET_COVERAGE,
                severity=Severity.HIGH,
                description=(
                    f"{len(cloud_unscanned)} cloud assets were discovered via connector "
                    "but have never been scanned. Cloud assets without scan results "
                    "provide zero vulnerability intelligence."
                ),
                evidence=_truncate_evidence([asset_name(a) for a in cloud_unscanned], max_items=5),
                recommendation=(
                    "Deploy cloud-native scanners or Tenable Agents to cover cloud assets. "
                    "Enable cloud connector scanning in Tenable Cloud Security."
                ),
                effort="medium"
            )

        if no_auth_scan and len(no_auth_scan) > 3:
            pct = round(len(no_auth_scan) / total * 100, 1)
            self._add(
                title=f"{len(no_auth_scan)} Asset(s) Never Authenticated ({pct}%)",
                category=FindingCategory.ASSET_COVERAGE,
                severity=Severity.MEDIUM,
                description=(
                    f"{len(no_auth_scan)} assets ({pct}%) have plugin results but "
                    "have never had a successful authenticated scan. "
                    "Authenticated scans detect 2-3x more vulnerabilities."
                ),
                evidence=_truncate_evidence([asset_name(a) for a in no_auth_scan], max_items=5),
                recommendation="Configure and enable credential scanning for these assets.",
                effort="high"
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
            if not scan.get("name"):
                continue
            if scan.get("enabled") is False:
                continue
            last_run = scan.get("last_run")
            if not last_run:
                stale.append(scan["name"])
                continue
            try:
                last_dt = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
                if (now - last_dt).days > 30:
                    stale.append(scan["name"])
            except (ValueError, TypeError):
                stale.append(scan.get("name", "unknown"))

        if stale:
            self._add(
                title=f"{len(stale)} Scan(s) Not Run in 30+ Days",
                category=FindingCategory.SCAN_POLICY,
                severity=Severity.CRITICAL if len(stale) > 100 else Severity.HIGH,
                description=(
                    f"{len(stale)} scans have not executed in the last 30 days. "
                    "This may indicate scheduling issues or abandoned scan configurations."
                ),
                evidence=f"Sample: {_truncate_evidence(stale, max_items=5)}",
                recommendation=(
                    "Review and clean up abandoned scans. "
                    "Enable weekly schedules for all active scan policies."
                ),
                effort="medium"
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