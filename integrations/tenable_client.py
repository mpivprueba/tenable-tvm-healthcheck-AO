from datetime import datetime, timezone
from loguru import logger
from config.settings import settings


class TenableClient:
    def __init__(self):
        self.mock = settings.MOCK_MODE

        if self.mock:
            logger.warning("TenableClient: MOCK MODE active.")
            self._tvm = None
        else:
            from tenable.io import TenableIO
            logger.info(f"TenableClient: connecting to {settings.TENABLE_API_URL}")
            self._tvm = TenableIO(
                access_key=settings.TENABLE_ACCESS_KEY,
                secret_key=settings.TENABLE_SECRET_KEY,
            )
            self._verify_connection()

    def _verify_connection(self):
        try:
            resp = self._tvm.get("session")
            data = resp.json()
            logger.info(f"Connected as: {data.get('username', 'unknown')}")
        except Exception as e:
            logger.error(f"Cannot reach Tenable API: {e}")
            raise ConnectionError(
                "Cannot connect to Tenable. Check your API keys and network."
            )

    # ------------------------------------------------------------------
    # Scanners
    # ------------------------------------------------------------------
    def get_scanners(self) -> list[dict]:
        if self.mock:
            return self._mock_scanners()

        scanners = []
        for s in self._tvm.scanners.list():
            scanners.append({
                "id":           s.get("id", ""),
                "name":         s.get("name", ""),
                "status":       s.get("status", "off"),
                "linked":       s.get("linked", 1) == 1,
                "last_connect": s.get("last_connect"),
                "scan_count":   s.get("scan_count", 0),
            })
        logger.info(f"GET /scanners → {len(scanners)} records")
        return scanners

    # ------------------------------------------------------------------
    # Assets — paginado via pyTenable
    # ------------------------------------------------------------------
    def get_assets(self) -> list[dict]:
        if self.mock:
            return self._mock_assets()

        logger.info("Fetching assets from /workbenches/assets (paginated)...")
        all_assets = []
        for asset in self._tvm.workbenches.assets():
            fqdn = asset.get("fqdn", [])
            ipv4 = asset.get("ipv4", [])
            all_assets.append({
                "id":        asset.get("id", ""),
                "fqdn":      fqdn[0] if isinstance(fqdn, list) and fqdn else str(fqdn),
                "hostname":  asset.get("hostname", [""])[0] if asset.get("hostname") else "",
                "ipv4":      ipv4[0] if isinstance(ipv4, list) and ipv4 else str(ipv4),
                "last_seen": asset.get("last_seen", ""),
                "tags":      asset.get("tags", []),
            })

        logger.info(f"Assets fetched: {len(all_assets)} (offset 0)")
        logger.info(f"Total assets retrieved: {len(all_assets)}")
        return all_assets

    # ------------------------------------------------------------------
    # Scans
    # ------------------------------------------------------------------
    def get_scans(self) -> list[dict]:
        if self.mock:
            return self._mock_scans()
        return self._get_scans_normalized()

    def _get_scans_normalized(self) -> list[dict]:
        normalized = []
        for scan in self._tvm.scans.list():
            has_credentials = (
                scan.get("credential_enabled", False)
                or bool(scan.get("credentials", {}))
                or bool(scan.get("shared_credentials", []))
                or "credenti" in (scan.get("name", "") or "").lower()
                or "cred" in (scan.get("type", "") or "").lower()
            )
            last_run = scan.get("last_modification_date") or scan.get("starttime")
            if isinstance(last_run, (int, float)) and last_run > 0:
                last_run = datetime.fromtimestamp(last_run, tz=timezone.utc).isoformat()

            normalized.append({
                "id":                 scan.get("id", ""),
                "name":               scan.get("name", ""),
                "credential_enabled": has_credentials,
                "last_run":           last_run,
                "asset_count":        scan.get("total", 0),
                "status":             scan.get("status", ""),
                "enabled":            scan.get("enabled", False),
            })

        logger.info(
            f"Scans normalized: {len(normalized)} total, "
            f"{sum(1 for s in normalized if s['credential_enabled'])} with credentials"
        )
        return normalized

    # ------------------------------------------------------------------
    # Policies
    # ------------------------------------------------------------------
    def get_policies(self) -> list[dict]:
        if self.mock:
            return self._mock_policies()

        policies = list(self._tvm.policies.list())
        logger.info(f"GET /policies → {len(policies)} records")
        return policies

    # ------------------------------------------------------------------
    # Tags
    # ------------------------------------------------------------------
    def get_tags(self) -> list[dict]:
        if self.mock:
            return self._mock_tags()

        tags = list(self._tvm.tags.list())
        logger.info(f"GET /tags/values → {len(tags)} records")
        return tags

    # ------------------------------------------------------------------
    # ✅ NUEVO — Credentials
    # ------------------------------------------------------------------
    def get_credentials(self) -> list[dict]:
        if self.mock:
            return self._mock_credentials()

        credentials = []
        for cred in self._tvm.credentials.list():
            # Normalizar a dict simple — pyTenable devuelve Box objects
            cred_type = ""
            try:
                cred_type = str(cred.get("type", "") or "")
            except Exception:
                pass
            credentials.append({
                "id":   str(cred.get("id", "") or ""),
                "name": str(cred.get("name", "") or ""),
                "type": cred_type,
            })
        logger.info(f"GET /credentials → {len(credentials)} records")
        return credentials
    
    # ------------------------------------------------------------------
    # ✅ NUEVO — Networks
    # ------------------------------------------------------------------
    def get_networks(self) -> list[dict]:
        if self.mock:
            return self._mock_networks()

        networks = []
        for net in self._tvm.networks.list():
            networks.append({
                "id":              net.get("uuid", ""),
                "name":            net.get("name", ""),
                "description":     net.get("description", ""),
                "scanner_count":   net.get("scanner_count", 0),
                "asset_count":     net.get("asset_count", 0),
                "is_default":      net.get("is_default", False),
            })
        logger.info(f"GET /networks → {len(networks)} records")
        return networks

    # ==================================================================
    # MOCK DATA
    # ==================================================================
    def _mock_scanners(self):
        return [
            {"id": "s-001", "name": "HQ-Scanner-01",      "status": "on",  "linked": True,  "last_connect": "2024-05-01T10:00:00Z", "scan_count": 45},
            {"id": "s-002", "name": "DMZ-Scanner-01",     "status": "off", "linked": True,  "last_connect": "2024-03-10T08:00:00Z", "scan_count": 0},
            {"id": "s-003", "name": "Cloud-Scanner-AWS",  "status": "on",  "linked": True,  "last_connect": "2024-05-15T12:00:00Z", "scan_count": 120},
            {"id": "s-004", "name": "Branch-Scanner-MTY", "status": "on",  "linked": False, "last_connect": None,                  "scan_count": 0},
        ]

    def _mock_assets(self):
        return [
            {
                "id":        f"a-{i:04d}",
                "fqdn":      f"host-{i}.corp.local",
                "hostname":  f"host-{i}",
                "ipv4":      f"10.0.{i//256}.{i%256}",
                "last_seen": "2024-05-15T00:00:00Z" if i % 5 != 0 else "2024-01-01T00:00:00Z",
                "tags":      [{"key": "env", "value": "production"}] if i % 2 == 0 else [],
            }
            for i in range(1, 251)
        ]

    def _mock_scans(self):
        return [
            {"id": "sc-001", "name": "Weekly Full Scan - HQ",    "credential_enabled": True,  "last_run": "2024-05-14T02:00:00Z", "asset_count": 180},
            {"id": "sc-002", "name": "DMZ Discovery Scan",       "credential_enabled": False, "last_run": "2024-02-01T10:00:00Z", "asset_count": 30},
            {"id": "sc-003", "name": "Cloud Assets Scan",        "credential_enabled": True,  "last_run": "2024-05-15T03:00:00Z", "asset_count": 65},
            {"id": "sc-004", "name": "AD Servers - Credentialed","credential_enabled": True,  "last_run": "2024-05-13T01:00:00Z", "asset_count": 12},
        ]

    def _mock_policies(self):
        return [
            {"id": "p-001", "name": "Basic Network Scan",        "template": "basic"},
            {"id": "p-002", "name": "Discovery Only",            "template": "discovery"},
            {"id": "p-003", "name": "Credentialed Patch Audit",  "template": "credentialed_patch_audit"},
        ]

    def _mock_tags(self):
        return [
            {"id": "t-001", "key": "env",   "value": "production"},
            {"id": "t-002", "key": "env",   "value": "development"},
            {"id": "t-003", "key": "owner", "value": "IT-Ops"},
        ]

    def _mock_credentials(self):
        return [
            {"id": "cr-001", "name": "Windows Domain Admin", "type": "Windows",  "description": "Domain admin for HQ servers"},
            {"id": "cr-002", "name": "Linux SSH Key",         "type": "SSH",      "description": "SSH key for Linux fleet"},
            {"id": "cr-003", "name": "DB Read-Only",          "type": "Database", "description": "Read-only DB credentials"},
        ]

    def _mock_networks(self):
        return [
            {"id": "net-001", "name": "Default",     "description": "Default network", "scanner_count": 2, "asset_count": 180, "is_default": True},
            {"id": "net-002", "name": "DMZ",         "description": "DMZ segment",     "scanner_count": 1, "asset_count": 30,  "is_default": False},
            {"id": "net-003", "name": "Cloud-AWS",   "description": "AWS network",     "scanner_count": 1, "asset_count": 65,  "is_default": False},
        ]