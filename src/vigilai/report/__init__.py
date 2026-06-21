"""Brazil PL 2338/2023 compliance reporting for vigilAI (Phase 7).

COMPL-AI ships no report aggregation; this package adds a thin aggregator that reads Inspect
run logs and emits a per-``brazil_article`` compliance summary with an EU↔Brazil side-by-side.
"""

from vigilai.report.brazil_report import build_brazil_report
from vigilai.report.brazil_report import BrazilComplianceReport
from vigilai.report.brazil_report import EU_BRAZIL_PAIRS


__all__ = ["build_brazil_report", "BrazilComplianceReport", "EU_BRAZIL_PAIRS"]
