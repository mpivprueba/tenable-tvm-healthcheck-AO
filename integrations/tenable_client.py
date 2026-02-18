import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from config.settings import settings


class TenableClient:
    def __init__(self):
        self.mock = settings.MOCK_MODE
        self.base_url = settings.TENABLE_API_URL
        self.headers = {
            "X-ApiKeys": (
                f"accessKey={settings.TENABLE_ACCESS_KEY};"
                f" secretKey={settings.TENABLE_SECRET_KEY}"
            ),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.mock:
            logger.warning("TenableClient: MOCK MODE active.")
        else:
            logger.info(f"TenableClient: connecting to {self.base_url}")
            self._verify_connection()

    def _verify_connection(self):
        try:
            with httpx.Client(headers=self.headers, timeout=15) as client:
                resp = client.get(f"{self.base_url}/session")
                if resp.status_code == 200:
                    data = resp.json()
                    logger.info(f"Connected as: {data.get('username', 'unknown')}")
                else:
                    logger.error(f"Auth failed: HTTP {resp.status_code}")
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
        return self._get("/scanners", "scanners")

    # ------------------------------------------------------------------
    # Assets — usa workbenches para inventario completo con paginación
    # ------------------------------------------------------------------
    def get_assets(self) -> list[dict]:
        if self.mock:
            return self._mock_assets()
        return self._get_assets_paginated()

    def _get_assets_paginated(self) -> list[dict]:
        """
        Extrae todos los assets usando /workbenches/assets con paginación.
        Devuelve lista normalizada compatible con el gap analyzer.
        """
        all_assets = []
        chunk_size = 5000
        offset = 0

        logger.info("Fetching assets from /workbenches/assets (paginated)...")

        with httpx.Client(headers=self.headers, timeout=60) as client:
            while True:
                params = {
                    "chunk_size": chunk_size,
                    "offset": offset,
                    "all_fields": 1,
                }
                try:
                    resp = client.get(
                        f"{self.base_url}/workbenches/assets",
                        params=params
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    assets = data.get("assets", [])

                    if not assets:
                        break

                    # Normalizar campos para compatibilidad con gap_analyzer
                    for asset in assets:
                        all_assets.append({
                            "id": asset.get("id", ""),
                            "fqdn": (asset.get("fqdn") or [""])[0]
                                    if isinstance(asset.get("fqdn"), list)
                                    else asset.get("fqdn", ""),
                            "ipv4": (asset.get("ipv4") or [""])[0]
                                    if isinstance(asset.get("ipv4"), list)
                                    else asset.get("ipv4", ""),
                            "last_seen": asset.get("last_seen", ""),
                            "tags": asset.get("tags", []),
                        })

                    logger.info(
                        f"Assets fetched: {len(all_assets)} "
                        f"(offset {offset})"
                    )

                    # Si devolvió menos del chunk, es la última página
                    if len(assets) < chunk_size:
                        break

                    offset += chunk_size

                except Exception as e:
                    logger.error(f"Error fetching assets at offset {offset}: {e}")
                    break

        logger.info(f"Total assets retrieved: {len(all_assets)}")
        return all_assets

    # ------------------------------------------------------------------
    # Scans — con detección correcta de credenciales
    # ------------------------------------------------------------------
    def get_scans(self) -> list[dict]:
        if self.mock:
            return self._mock_scans()
        return self._get_scans_normalized()

    def _get_scans_normalized(self) -> list[dict]:
        """
        Obtiene scans y normaliza el campo credential_enabled.
        La API devuelve credenciales en distintos campos según la versión.
        """
        raw = self._get("/scans", "scans")
        normalized = []

        for scan in raw:
            # Tenable puede indicar credenciales de varias formas
            has_credentials = (
                # Campo directo (algunas versiones)
                scan.get("credential_enabled", False)
                # Objeto credentials no vacío
                or bool(scan.get("credentials", {}))
                # Campo shared_credentials
                or bool(scan.get("shared_credentials", []))
                # uuid de template con credenciales en el nombre
                or "credenti" in (scan.get("name", "") or "").lower()
                or "cred" in (scan.get("type", "") or "").lower()
            )

            # last_modification_date como proxy de last_run si no existe
            last_run = (
                scan.get("last_modification_date")
                or scan.get("starttime")
            )
            # Convertir epoch a ISO si es número
            if isinstance(last_run, (int, float)) and last_run > 0:
                from datetime import datetime, timezone
                last_run = datetime.fromtimestamp(
                    last_run, tz=timezone.utc
                ).isoformat()

            normalized.append({
                "id": scan.get("id", ""),
                "name": scan.get("name", ""),
                "credential_enabled": has_credentials,
                "last_run": last_run,
                "asset_count": scan.get("total", 0),
                "status": scan.get("status", ""),
                "enabled": scan.get("enabled", False),
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
        return self._get("/policies", "policies")

    # ------------------------------------------------------------------
    # Tags
    # ------------------------------------------------------------------
    def get_tags(self) -> list[dict]:
        if self.mock:
            return self._mock_tags()
        return self._get("/tags/values", "values")

    # ------------------------------------------------------------------
    # Generic GET with retry
    # ------------------------------------------------------------------
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def _get(self, endpoint: str, key: str) -> list[dict]:
        try:
            with httpx.Client(headers=self.headers, timeout=30) as client:
                resp = client.get(f"{self.base_url}{endpoint}")
                resp.raise_for_status()
                data = resp.json()
                result = data.get(key, [])
                logger.info(f"GET {endpoint} → {len(result)} records")
                return result
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error on {endpoint}: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Error on {endpoint}: {e}")
            raise

    # ==================================================================
    # MOCK DATA
    # ==================================================================
    def _mock_scanners(self):
        return [
            {"id": "s-001", "name": "HQ-Scanner-01", "status": "on",
             "linked": True, "last_connect": "2024-05-01T10:00:00Z", "scan_count": 45},
            {"id": "s-002", "name": "DMZ-Scanner-01", "status": "off",
             "linked": True, "last_connect": "2024-03-10T08:00:00Z", "scan_count": 0},
            {"id": "s-003", "name": "Cloud-Scanner-AWS", "status": "on",
             "linked": True, "last_connect": "2024-05-15T12:00:00Z", "scan_count": 120},
            {"id": "s-004", "name": "Branch-Scanner-MTY", "status": "on",
             "linked": False, "last_connect": None, "scan_count": 0},
        ]

    def _mock_assets(self):
        return [
            {
                "id": f"a-{i:04d}",
                "fqdn": f"host-{i}.corp.local",
                "ipv4": f"10.0.{i//256}.{i%256}",
                "last_seen": (
                    "2024-05-15T00:00:00Z"
                    if i % 5 != 0
                    else "2024-01-01T00:00:00Z"
                ),
                "tags": (
                    [{"key": "env", "value": "production"}]
                    if i % 2 == 0
                    else []
                ),
            }
            for i in range(1, 251)
        ]

    def _mock_scans(self):
        return [
            {"id": "sc-001", "name": "Weekly Full Scan - HQ",
             "credential_enabled": True,
             "last_run": "2024-05-14T02:00:00Z", "asset_count": 180},
            {"id": "sc-002", "name": "DMZ Discovery Scan",
             "credential_enabled": False,
             "last_run": "2024-02-01T10:00:00Z", "asset_count": 30},
            {"id": "sc-003", "name": "Cloud Assets Scan",
             "credential_enabled": True,
             "last_run": "2024-05-15T03:00:00Z", "asset_count": 65},
            {"id": "sc-004", "name": "AD Servers - Credentialed",
             "credential_enabled": True,
             "last_run": "2024-05-13T01:00:00Z", "asset_count": 12},
        ]

    def _mock_policies(self):
        return [
            {"id": "p-001", "name": "Basic Network Scan", "template": "basic"},
            {"id": "p-002", "name": "Discovery Only", "template": "discovery"},
            {"id": "p-003", "name": "Credentialed Patch Audit",
             "template": "credentialed_patch_audit"},
        ]

    def _mock_tags(self):
        return [
            {"id": "t-001", "key": "env", "value": "production"},
            {"id": "t-002", "key": "env", "value": "development"},
            {"id": "t-003", "key": "owner", "value": "IT-Ops"},
        ]