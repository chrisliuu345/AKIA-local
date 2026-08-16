"""HTML 自包含导出 — matplotlib图表 → base64内嵌 → 单文件HTML"""

import html as _html
import io
import base64
from typing import Dict, List
from datetime import datetime
from io import BytesIO

from config.settings import APP_VERSION, CHART_COLORS


def _fig_to_base64(fig) -> str:
    with io.BytesIO() as buf:
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight",
                    facecolor=CHART_COLORS.get("background", "#181822"))
        buf.seek(0)
        return base64.b64encode(buf.read()).decode()


def export_html(analyses: List[Dict], charts: Dict[str, bytes] = None,
                output_path: str = "", title: str = "QA-Tool 分析报告") -> str:
    items = []
    for a in analyses:
        atype = a.get("analysis_type", "?")
        result = a.get("result", {})
        summary = result.get("summary", "") if isinstance(result, dict) else str(result)
        items.append({"type": _html.escape(atype), "summary": _html.escape(str(summary)[:200])})

    img_tags = ""
    if charts:
        for label, buf in charts.items():
            if hasattr(buf, 'getvalue'):
                data = buf.getvalue()
            else:
                data = buf
            b64 = base64.b64encode(data).decode()
            img_tags += f'<div class="chart"><h3>{_html.escape(label)}</h3><img src="data:image/png;base64,{b64}" style="max-width:100%"></div>\n'

    safe_title = _html.escape(title)
    html_doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>{safe_title}</title>
<style>
body{{font-family:'Microsoft YaHei',sans-serif;max-width:1000px;margin:auto;padding:20px;background:#181822;color:#e1e2e6}}
h1{{color:#4da6ff;border-bottom:2px solid #3a3a48;padding-bottom:10px}}
h3{{color:#a0a3ae}}.summary{{background:#262632;padding:12px;border-radius:8px;margin:8px 0}}
.chart{{margin:16px 0;background:#1c1c26;padding:12px;border-radius:8px}}
.footer{{color:#6e7080;font-size:12px;margin-top:30px;text-align:center}}
</style></head><body>
<h1>{safe_title}</h1>
<p>生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M")} | 分析项目: {len(items)} 项 | QA-Tool v{APP_VERSION}</p>
{"".join(f'<div class="summary"><b>{i["type"]}:</b> {i["summary"]}</div>' for i in items)}
{img_tags}
<div class="footer"><p>QA-Tool v{APP_VERSION} · 自包含离线报告</p></div>
</body></html>"""

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_doc)
    return html_doc
