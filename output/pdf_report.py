"""
PDF 报告生成器 — 基于 reportlab，可靠中文渲染
"""
import os
from datetime import datetime
from typing import Dict, Any, List
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, HRFlowable,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from config.settings import APP_NAME, APP_VERSION
from core.i18n import i18n
from output.base_report_engine import BaseReportEngine


def _find_cjk_fonts():
    """Robustly locate and register Chinese fonts for PDF.

    Priorities (best → fallback):
      1. 微软雅黑 (msyh.ttc) — regular=idx0, bold=idx1
      2. 黑体 (simhei.ttf) — single weight
      3. 宋体 (simsun.ttc) — regular only
      4. Noto Sans SC / Noto Serif SC
      5. STSong-Light (built-in CID font with limited coverage)
    """
    font_dir = "C:/Windows/Fonts"

    candidates = [
        # (regular_path, regular_index, bold_path, bold_index)   indexed by ttc subfontIndex
        (os.path.join(font_dir, "msyh.ttc"), 0, os.path.join(font_dir, "msyh.ttc"), 1),
        (os.path.join(font_dir, "msyh.ttc"), 0, os.path.join(font_dir, "msyhbd.ttf"), 0),
        (os.path.join(font_dir, "simhei.ttf"), 0, os.path.join(font_dir, "simhei.ttf"), 0),
        (os.path.join(font_dir, "simsun.ttc"), 0, os.path.join(font_dir, "simsun.ttc"), 0),
        (os.path.join(font_dir, "NotoSansSC-VF.ttf"), 0, os.path.join(font_dir, "NotoSansSC-VF.ttf"), 0),
        (os.path.join(font_dir, "NotoSansSC-Regular.ttf"), 0, os.path.join(font_dir, "NotoSansSC-Bold.ttf"), 0),
    ]

    for reg_path, reg_idx, bold_path, bold_idx in candidates:
        if not os.path.exists(reg_path):
            continue
        try:
            fname = "CNFont"
            fname_bold = "CNFontBold"

            if reg_path.endswith(".ttc"):
                pdfmetrics.registerFont(TTFont(fname, reg_path, subfontIndex=reg_idx))
            else:
                pdfmetrics.registerFont(TTFont(fname, reg_path))

            if bold_path == reg_path and bold_idx == reg_idx:
                pdfmetrics.registerFont(TTFont(fname_bold, reg_path, subfontIndex=bold_idx)) if bold_path.endswith(".ttc") else pdfmetrics.registerFont(TTFont(fname_bold, bold_path))
            elif os.path.exists(bold_path):
                if bold_path.endswith(".ttc"):
                    pdfmetrics.registerFont(TTFont(fname_bold, bold_path, subfontIndex=bold_idx))
                else:
                    pdfmetrics.registerFont(TTFont(fname_bold, bold_path))
            else:
                fname_bold = fname

            return fname, fname_bold
        except Exception:
            continue

    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        return "STSong-Light", "STSong-Light"
    except Exception:
        return "Helvetica", "Helvetica-Bold"


class PDFReport(BaseReportEngine):
    """生成 PDF 质量分析报告"""

    def __init__(self):
        super().__init__()
        self.font_name, self.font_bold = _find_cjk_fonts()
        self._styles = {}

    def _get_styles(self):
        fn = self.font_name
        fb = self.font_bold
        if not self._styles:
            self._styles = {
                "title": ParagraphStyle(
                    "PDFTitle", fontName=fb, fontSize=24, leading=30,
                    alignment=TA_CENTER, spaceAfter=24, textColor=HexColor("#1b5faa"),
                ),
                "subtitle": ParagraphStyle(
                    "PDFSubtitle", fontName=fn, fontSize=14, leading=20,
                    alignment=TA_CENTER, spaceAfter=12, textColor=HexColor("#555555"),
                ),
                "h1": ParagraphStyle(
                    "PDFH1", fontName=fb, fontSize=16, leading=22,
                    spaceBefore=20, spaceAfter=10, textColor=HexColor("#1b5faa"),
                ),
                "h2": ParagraphStyle(
                    "PDFH2", fontName=fb, fontSize=13, leading=18,
                    spaceBefore=14, spaceAfter=6, textColor=HexColor("#333333"),
                ),
                "body": ParagraphStyle(
                    "PDFBody", fontName=fn, fontSize=10, leading=16,
                    spaceBefore=4, spaceAfter=4,
                ),
                "meta": ParagraphStyle(
                    "PDFMeta", fontName=fn, fontSize=9, leading=14,
                    alignment=TA_LEFT, textColor=HexColor("#888888"),
                ),
            }
        return self._styles

    def generate(
        self,
        analyses: List[Dict[str, Any]],
        output_path: str,
        title: str = "",
        subtitle: str = "",
        charts: Dict[str, bytes] = None,
        watermark: str = "",
    ) -> str:
        if not title:
            title = i18n.tr("report.title")
        doc = SimpleDocTemplate(
            output_path, pagesize=A4,
            leftMargin=2 * cm, rightMargin=2 * cm,
            topMargin=2 * cm, bottomMargin=2 * cm,
        )
        # 水印回调
        if watermark:
            def _wm(canvas, doc):
                canvas.saveState()
                canvas.setFont("Helvetica", 40)
                canvas.setFillColor(HexColor("#888888"), alpha=0.08)
                canvas.drawString(3*cm, 14*cm, watermark)
                canvas.restoreState()
            doc.build(self.story, onFirstPage=_wm, onLaterPages=_wm)
            return output_path

        self.story = []
        S = self._get_styles()

        self._add_title_page(title, subtitle, S)
        self.story.append(PageBreak())

        self._add_overview(analyses, S)
        self.story.append(PageBreak())

        for i, atype, params, result in self.iter_analyses(analyses):

            self.story.append(Paragraph(f"{i+1}. {atype}", S["h1"]))

            if params:
                self._add_kv_table("分析参数", params, S)

            self._add_analysis_detail(result, S)

            if charts:
                chart_key = None
                for key in charts:
                    if atype in key or key in atype:
                        chart_key = key
                        break
                if chart_key is None and charts:
                    keys = list(charts.keys())
                    if i < len(keys):
                        chart_key = keys[i]

                if chart_key and charts[chart_key]:
                    from io import BytesIO
                    from reportlab.lib.utils import ImageReader
                    try:
                        img = Image(BytesIO(charts[chart_key]), width=14 * cm, height=9 * cm)
                        self.story.append(Spacer(1, 0.4 * cm))
                        self.story.append(img)
                    except Exception:
                        pass

            self.story.append(Spacer(1, 0.6 * cm))

        self.story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#cccccc")))
        footer_text, _ = self.footers()
        self.story.append(Paragraph(footer_text, S["meta"]))

        doc.build(self.story)
        return output_path

    def _add_title_page(self, title: str, subtitle: str, S: dict):
        self.story.append(Spacer(1, 5 * cm))
        self.story.append(Paragraph(title, S["title"]))
        if subtitle:
            self.story.append(Paragraph(subtitle, S["subtitle"]))
        self.story.append(Spacer(1, 3 * cm))
        self.story.append(Paragraph(f"{i18n.tr('report.generated_by')} {APP_NAME} v{APP_VERSION}", S["body"]))
        self.story.append(Paragraph(f"{i18n.tr('report.date')}: {datetime.now().strftime('%Y-%m-%d')}", S["body"]))

    def _add_overview(self, analyses, S):
        self.story.append(Paragraph(i18n.tr("report.summary_title"), S["h1"]))
        self.story.append(Spacer(1, 0.3 * cm))

        headers = [i18n.tr("report.index"), i18n.tr("report.analysis_type"), i18n.tr("report.conclusion")]
        data = [headers]
        for i, analysis in enumerate(analyses):
            atype = analysis.get("analysis_type", analysis.get("chart_type", ""))
            conclusion = self.extract_conclusion(analysis.get("result", {}))
            data.append([str(i + 1), atype, conclusion])

        col_w = [1.2 * cm, 9 * cm, 5.8 * cm]
        self._draw_table(data, col_w, S, header_bg="#1b5faa")

    def _add_analysis_detail(self, result: Dict, S: dict):
        if "capability" in result:
            cap = result["capability"]
            rows = [
                ["指标", "Cp", "Cpk", "Pp", "Ppk", "PPM", "等级"],
                [
                    "值",
                    str(cap.get("cp", "-")),
                    str(cap.get("cpk", "-")),
                    str(cap.get("pp", "-")),
                    str(cap.get("ppk", "-")),
                    str(cap.get("ppm_total", "-")),
                    str(cap.get("grade", "-")),
                ],
            ]
            col_w = [2.5 * cm] + [2.2 * cm] * 6
            self._draw_table(rows, col_w, S, header_bg="#1b5faa")

        if "percentages" in result:
            pct = result["percentages"]
            rows = [
                ["指标", "%GRR (TV)", "%GRR (Tol)", "NDC", "判定"],
                [
                    "值",
                    f"{pct.get('grr_pct_tv', '-')}%",
                    f"{pct.get('grr_pct_tol', '-')}%",
                    str(result.get("ndc", "-")),
                    result.get("acceptance", {}).get("message", "-"),
                ],
            ]
            col_w = [3 * cm, 3 * cm, 3 * cm, 2.5 * cm, 4.5 * cm]
            self._draw_table(rows, col_w, S, header_bg="#1b5faa")

        if "p_value" in result:
            sig = result.get("is_significant", False)
            color = "#1b5faa" if sig else "#d62728"
            msg = i18n.tr("report.significant") if sig else i18n.tr("report.not_significant")
            text = f'<font color="{color}"><b>{msg}</b></font>  (P-value = {result["p_value"]:.4f})'
            self.story.append(Paragraph(text, S["body"]))

        if "model" in result:
            m = result["model"]
            rows = [
                ["指标", "R²", "Adj R²", "F", "样本数"],
                ["值", f"{m.get('r_squared', '-'):.4f}", f"{m.get('adj_r_squared', '-'):.4f}",
                 f"{m.get('f_statistic', '-'):.2f}", str(m.get('n', '-'))],
            ]
            col_w = [3 * cm] + [3.25 * cm] * 4
            self._draw_table(rows, col_w, S, header_bg="#1b5faa")

    def _add_kv_table(self, title: str, params: Dict, S: dict):
        self.story.append(Paragraph(title, S["h2"]))
        rows = [["参数", "值"]]
        rows += [[str(k), str(v)] for k, v in params.items()]
        col_w = [5 * cm, 11 * cm]
        self._draw_table(rows, col_w, S)
        self.story.append(Spacer(1, 0.3 * cm))

    def _draw_table(self, data: List[List[str]], col_widths: List[float],
                    S: dict, header_bg: str = "#1b5faa"):
        tbl = Table(data, colWidths=col_widths, repeatRows=1)
        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), HexColor(header_bg)),
            ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 0), (-1, 0), self.font_bold),
            ("FONTNAME", (0, 1), (-1, -1), self.font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
        ]
        if len(data) > 2:
            style_cmds.append(("ROWBACKGROUNDS", (0, 1), (-1, -1),
                               [HexColor("#f8f9fa"), HexColor("#ffffff")]))
        tbl.setStyle(TableStyle(style_cmds))
        self.story.append(tbl)
        self.story.append(Spacer(1, 0.4 * cm))


def generate_pdf_report(
    analyses: List[Dict[str, Any]],
    output_path: str,
    title: str = "",
    subtitle: str = "",
    charts: Dict[str, bytes] = None,
    watermark: str = "",
) -> str:
    """Convenience wrapper: generate a PDF report with optional watermark."""
    return PDFReport().generate(analyses, output_path, title, subtitle, charts, watermark)
