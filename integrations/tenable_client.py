from loguru import logger
from config.settings import settings

class TenableClient:
    def __init__(self):
        self.mock = settings.MOCK_MODE
        if self.mock:
            logger.warning("TenableClient: MOCK MODE active.")

    def get_scanners(self):
        if self.mock:
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

    def get_assets(self):
        if self.mock:
            return [
                {"id": f"a-{i:04d}", "fqdn": f"host-{i}.corp.local",
                 "ipv4": f"10.0.{i//256}.{i%256}",
                 "last_seen": "2024-05-15T00:00:00Z" if i % 5 != 0 else "2024-01-01T00:00:00Z",
                 "tags": [{"key": "env", "value": "production"}] if i % 2 == 0 else []}
                for i in range(1, 251)
            ]

    def get_scans(self):
        if self.mock:
            return [
                {"id": "sc-001", "name": "Weekly Full Scan - HQ",
                 "credential_enabled": True, "last_run": "2024-05-14T02:00:00Z", "asset_count": 180},
                {"id": "sc-002", "name": "DMZ Discovery Scan",
                 "credential_enabled": False, "last_run": "2024-02-01T10:00:00Z", "asset_count": 30},
                {"id": "sc-003", "name": "Cloud Assets Scan",
                 "credential_enabled": True, "last_run": "2024-05-15T03:00:00Z", "asset_count": 65},
                {"id": "sc-004", "name": "AD Servers - Credentialed",
                 "credential_enabled": True, "last_run": "2024-05-13T01:00:00Z", "asset_count": 12},
            ]

    def get_policies(self):
        if self.mock:
            return [
                {"id": "p-001", "name": "Basic Network Scan", "template": "basic"},
                {"id": "p-002", "name": "Discovery Only", "template": "discovery"},
                {"id": "p-003", "name": "Credentialed Patch Audit",
                 "template": "credentialed_patch_audit"},
            ]

    def get_tags(self):
        if self.mock:
            return [
                {"id": "t-001", "key": "env", "value": "production"},
                {"id": "t-002", "key": "env", "value": "development"},
                {"id": "t-003", "key": "owner", "value": "IT-Ops"},
            ]