"""BaseReportEngine — 所有报告生成器的共享逻辑"""

from collections.abc import Iterator
from datetime import datetime

from config.settings import APP_NAME, APP_VERSION
from core.i18n import i18n


class BaseReportEngine:
    """Excel / Word / PDF 报告器的共享基类"""

    @staticmethod
    def iter_analyses(analyses: list[dict]) -> Iterator[tuple[int, str, dict, dict]]:
        for i, analysis in enumerate(analyses):
            atype = analysis.get("analysis_type",
                       analysis.get("chart_type", f"分析_{i+1}"))
            params = analysis.get("params", {})
            result = analysis.get("result", {})
            yield i, atype, params, result

    @staticmethod
    def footers(trace: str = "") -> tuple[str, str]:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        suffix = f"  |  {i18n.tr('report.trace_code')}: {trace}" if trace else ""
        return (
            f"{i18n.tr('report.generated_time')}: {ts}  |  {APP_NAME} v{APP_VERSION}{suffix}",
            f"{i18n.tr('report.date')}: {datetime.now().strftime('%Y-%m-%d')}",
        )

    @staticmethod
    def credential_trace(analyses: list[dict]) -> str:
        """由各分析记录内的凭证生成 12 位追溯码（无凭证时返回空串）。"""
        from core.evidence import credential_trace_code

        return credential_trace_code(
            [(analysis or {}).get("credential") for analysis in analyses])

    @staticmethod
    def extract_conclusion(result: dict) -> str:
        acceptance = result.get("acceptance", {})
        if acceptance.get("message"):
            return acceptance["message"]
        cap = result.get("capability", {})
        if cap.get("grade"):
            return f"{cap['grade']}"
        if "p_value" in result:
            return i18n.tr("report.significant") if result.get("is_significant") else i18n.tr("report.not_significant")
        model = result.get("model", {})
        if model:
            r2 = model.get("r_squared", 0)
            return f"R² = {r2:.3f}"
        return "-"

    @staticmethod
    def extract_key_result(result: dict) -> str:
        cap = result.get("capability", {})
        if cap:
            cpk = cap.get("cpk", cap.get("ppk", ""))
            grade = cap.get("grade", "")
            if cpk or grade:
                return f"Cpk={cpk} {grade}"
        percentages = result.get("percentages", {})
        if percentages.get("grr_pct_tv"):
            return f"GRR%={percentages['grr_pct_tv']}%"
        if "p_value" in result:
            sig = "显著" if result.get("is_significant") else "不显著"
            return f"p={result['p_value']:.4f} {sig}"
        return ""

    @staticmethod
    def classify_analysis_type(analysis: dict) -> str:
        atype = analysis.get("analysis_type", analysis.get("chart_type", ""))
        result = analysis.get("result", {})
        if "percentages" in result or "acceptance" in result:
            return "msa"
        if "capability" in result:
            return "capability"
        if "model" in result:
            return "regression"
        cl = atype.lower() if atype else ""
        for kw in ["spc", "xbar", "imr", "chart", "cusum", "ewma", "控制图"]:
            if kw in cl:
                return "spc"
        for kw in ["anova", "t_test", "t-test", "检验", "hypothesis"]:
            if kw in cl:
                return "hypothesis"
        for kw in ["doe", "factorial", "design", "实验"]:
            if kw in cl:
                return "doe"
        return "other"

    @staticmethod
    def safe_name(name: str, max_len: int = 31) -> str:
        import re
        safe = re.sub(r'[\[\]:*?/\\]', '_', name)
        return safe[:min(len(safe), max_len)]

    @staticmethod
    def param_rows(params: dict) -> list[tuple[str, str]]:
        return [(str(k), str(v)) for k, v in params.items()]
