"""
Mock data simulating Tenable VM API responses.
Used during development before API integration.
"""

def get_assets():
    return [
        {"id": "A1", "hostname": "server01", "criticality": "high"},
        {"id": "A2", "hostname": "workstation22", "criticality": "medium"},
        {"id": "A3", "hostname": "legacy-db", "criticality": "critical"},
    ]


def get_vulnerabilities():
    return [
        {"asset_id": "A1", "severity": "critical", "name": "OpenSSL RCE"},
        {"asset_id": "A1", "severity": "high", "name": "SMB Signing Disabled"},
        {"asset_id": "A2", "severity": "medium", "name": "Outdated Chrome"},
        {"asset_id": "A3", "severity": "critical", "name": "Unsupported OS"},
        {"asset_id": "A3", "severity": "critical", "name": "Weak Cipher"},
    ]
