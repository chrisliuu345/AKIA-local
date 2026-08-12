"""HTML 自包含导出 — matplotlib图表 → base64内嵌 → 单文件HTML"""

import io
import base64
from typing import Dict, Any, List
from datetime import datetime


def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight", facecolor="#181822")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def export_html(analyses: Dict[int, Dict], output_path: str, title: str = "QA-Tool 分析报告"):
    items = []
    for idx, a in analyses.items():
        atype = a.get("analysis_type", f"analysis_{idx}")
        result = a.get("result", {})
        summary = result.get("summary", "") if isinstance(result, dict) else str(result)
        items.append({"type": atype, "summary": summary})

    img_tags = ""
    # 遍历 analyses 收集图表
    for idx, a in analyses.items():
        fig = a.get("_figure") or a.get("current_figure")
        if fig:
            b64 = _fig_to_base64(fig)
            atype = a.get("analysis_type", f"chart_{idx}")
            img_tags += f'<div class="chart"><h3>{atype}</h3><img src="data:image/png;base64,{b64}" style="max-width:100%"></div>\n'

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>{title}</title>
<style>
body{{font-family:'Microsoft YaHei',sans-serif;max-width:1000px;margin:auto;padding:20px;background:#181822;color:#e1e2e6}}
h1{{color:#4da6ff;border-bottom:2px solid #3a3a48;padding-bottom:10px}}
h3{{color:#a0a3ae}}.summary{{background:#262632;padding:12px;border-radius:8px;margin:8px 0}}
.chart{{margin:16px 0;background:#1c1c26;padding:12px;border-radius:8px}}
.footer{{color:#6e7080;font-size:12px;margin-top:30px;text-align:center}}
</style></head><body>
<h1>{title}</h1>
<p>生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M")} | 分析项目: {len(items)} 项 | QA-Tool v2.3</p>
{"".join(f'<div class="summary"><b>{i["type"]}:</b> {i["summary"]}</div>' for i in items)}
{img_tags}
<div class="footer"><p>QA-Tool v2.3 · 自包含离线报告</p></div>
</body></html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path
