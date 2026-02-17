"""
Collector layer.
In production this will call Tenable APIs.
For now it pulls from mock data.
"""

from src.data.mock_data import get_assets, get_vulnerabilities


class VMCollector:

    def collect(self):
        assets = get_assets()
        vulns = get_vulnerabilities()

        return {
            "assets": assets,
            "vulnerabilities": vulns
        }
