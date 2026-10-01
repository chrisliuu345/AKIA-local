"""报告模板引擎 — 加载 + 渲染 HTML 模板 (stdlib string.Template)"""

from pathlib import Path
from string import Template
from typing import Any
from datetime import datetime

from config.settings import APP_VERSION
from core.fonts import get_ui_font


TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "config" / "templates"

TEMPLATES = {
    "daily": {"name": "质量日报", "file": "daily.html"},
    "monthly_spc": {"name": "月度SPC报告", "file": "monthly_spc.html"},
    "audit": {"name": "审核报告", "file": "audit.html"},
    "8d": {"name": "8D报告", "file": "8d.html"},
    "ppap": {"name": "PPAP提交", "file": "ppap.html"},
}


def _get_font_family() -> str:
    """获取平台感知的字体族"""
    return get_ui_font()


_BUILTIN_TEMPLATES: dict[str, str] = {}


def _ensure_templates():
    """确保模板目录和文件存在"""
    global _BUILTIN_TEMPLATES
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    font_family = _get_font_family()
    
    _BUILTIN_TEMPLATES = {
        "daily": f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>质量日报</title>
<style>body{{font-family:'{font_family}',sans-serif;max-width:800px;margin:auto;padding:20px;color:#333}}
h1{{color:#1b5faa;border-bottom:2px solid #1b5faa}}h2{{color:#555}}.kpi{{display:flex;gap:20px;margin:10px 0}}
.kpi div{{flex:1;background:#f0f4f8;padding:12px;border-radius:8px;text-align:center}}
.kpi .val{{font-size:28px;font-weight:bold;color:#1b5faa}}table{{width:100%;border-collapse:collapse;margin:10px 0}}
td,th{{border:1px solid #ddd;padding:6px;text-align:center}}th{{background:#1b5faa;color:#fff}}
.footer{{color:#888;font-size:12px;margin-top:30px}}</style></head><body>
<h1>质量日报</h1><p>日期: $date | 产品: $product | 部门: $department</p>
<h2>关键指标</h2><div class="kpi">$kpi_cards</div>
<h2>分析摘要</h2>$summary_table
<div class="footer"><p>AKIA v$version · 自动生成于 $timestamp</p></div></body></html>""",

        "monthly_spc": f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>月度SPC报告</title>
<style>body{{font-family:'{font_family}',sans-serif;max-width:900px;margin:auto;padding:20px;color:#333}}
h1{{color:#1b5faa}}h2{{color:#555;border-bottom:1px solid #ddd}}table{{width:100%;border-collapse:collapse;margin:10px 0}}
td,th{{border:1px solid #ddd;padding:6px}}th{{background:#1b5faa;color:#fff}}.warn{{color:#e74c3c}}.ok{{color:#27ae60}}</style></head><body>
<h1>月度SPC统计过程控制报告</h1><p>期间: $period | 产品: $product</p>
<h2>过程能力汇总</h2>$capability_table
<h2>SPC违规统计</h2>$spc_violations
<h2>MSA评估</h2>$msa_summary
<div class="footer"><p>AKIA v$version · $timestamp</p></div></body></html>""",

        "audit": f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>审核报告</title>
<style>body{{font-family:'{font_family}',sans-serif;max-width:800px;margin:auto;padding:20px;color:#333}}
h1{{color:#1b5faa}}h2{{color:#555}}table{{width:100%;border-collapse:collapse;margin:10px 0}}
td,th{{border:1px solid #ddd;padding:6px}}th{{background:#1b5faa;color:#fff}}
.pass{{color:#27ae60}}.fail{{color:#e74c3c}}</style></head><body>
<h1>LPA分层过程审核报告</h1><p>审核日期: $date | 审核员: $auditor</p>
<h2>审核结果</h2>$audit_table
<h2>不符合项</h2>$nc_list
<div class="footer"><p>AKIA v$version · $timestamp</p></div></body></html>""",

        "8d": f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>8D报告</title>
<style>body{{font-family:'{font_family}',sans-serif;max-width:800px;margin:auto;padding:20px;color:#333}}
h1{{color:#1b5faa}}h2{{color:#555;border-bottom:1px solid #ddd}}.step{{margin:10px 0;padding:10px;background:#f8f9fa;border-radius:6px}}
.step h3{{margin:0;color:#1b5faa}}</style></head><body>
<h1>8D问题解决报告</h1><p>$title_info</p>$steps_html
<div class="footer"><p>AKIA v$version · $timestamp</p></div></body></html>""",

        "ppap": f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>PPAP提交</title>
<style>body{{font-family:'{font_family}',sans-serif;max-width:900px;margin:auto;padding:20px;color:#333}}
h1{{color:#1b5faa}}table{{width:100%;border-collapse:collapse;margin:10px 0}}
td,th{{border:1px solid #ddd;padding:6px;text-align:center}}th{{background:#1b5faa;color:#fff}}
.done{{background:#d4edda}}.pending{{background:#fff3cd}}.na{{background:#e2e3e5}}</style></head><body>
<h1>PPAP生产件批准</h1><p>$ppap_info</p><h2>提交状态</h2>$items_table
<h2>尺寸报告</h2>$dim_table
<div class="footer"><p>AKIA v$version · $timestamp</p></div></body></html>""",
    }
    
    for key, info in TEMPLATES.items():
        fpath = TEMPLATE_DIR / info["file"]
        if not fpath.exists():
            content = _BUILTIN_TEMPLATES.get(key, "")
            fpath.write_text(content, encoding="utf-8")


class ReportTemplateEngine:
    def __init__(self):
        _ensure_templates()

    def list_templates(self) -> list[dict[str, str]]:
        return [{"id": k, "name": v["name"]} for k, v in TEMPLATES.items()]

    def load_template(self, template_id: str) -> str | None:
        info = TEMPLATES.get(template_id)
        if not info:
            return None
        fpath = TEMPLATE_DIR / info["file"]
        if fpath.exists():
            return fpath.read_text(encoding="utf-8")
        return _BUILTIN_TEMPLATES.get(template_id)

    def render(self, template_id: str, context: dict[str, Any]) -> str:
        raw = self.load_template(template_id)
        if not raw:
            return "<p>模板未找到</p>"
        ctx = dict(context)
        ctx.setdefault("version", APP_VERSION)
        ctx.setdefault("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M"))
        ctx.setdefault("date", datetime.now().strftime("%Y-%m-%d"))
        placeholders = ["product", "department", "auditor", "period", "title_info",
                        "ppap_info", "kpi_cards", "summary_table", "capability_table",
                        "spc_violations", "msa_summary", "audit_table", "nc_list",
                        "items_table", "dim_table", "steps_html"]
        for ph in placeholders:
            ctx.setdefault(ph, "—")
        try:
            return Template(raw).safe_substitute(**ctx)
        except Exception as e:
            return f"<p>模板渲染错误: {e}</p>"

    def build_context(self, analyses: dict[int, dict]) -> dict[str, Any]:
        """从分析结果构建模板上下文"""
        ctx = {}
        for idx, a in analyses.items():
            atype = a.get("analysis_type", f"analysis_{idx}")
            result = a.get("result", a.get("summary", {}))
            ctx[atype] = result
        return ctx
