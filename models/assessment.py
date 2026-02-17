from dataclasses import dataclass
from typing import List

@dataclass
class Finding:
    title: str
    severity: str
    description: str

@dataclass
class Assessment:
    customer: str
    findings: List[Finding]
