"""
PDF 报告生成器 — 基于 reportlab，可靠中文渲染
"""
import os
from datetime import datetime
from typing import Any
from xml.sax.saxutils import escape
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
from core.fonts import get_pdf_font_paths, get_pdf_font_candidates


def _find_cjk_fonts():
    """Robustly locate and register Chinese fonts for PDF.

    Platform-aware font detection:
      - Windows: msyh.ttc, simhei.ttf, simsun.ttc
      - Linux: Noto Sans CJK SC, WenQuanYi
      - macOS: PingFang, STHeiti
    """
    font_dirs = get_pdf_font_paths()
    font_candidates = get_pdf_font_candidates()

    for font_dir in font_dirs:
        for font_name in font_candidates:
            font_path = os.path.join(font_dir, font_name)
            if not os.path.exists(font_path):
                continue
            try:
                fname = "CNFont"
                fname_bold = "CNFontBold"

                if font_path.endswith(".ttc"):
                    pdfmetrics.registerFont(TTFont(fname, font_path, subfontIndex=0))
                    try:
                        pdfmetrics.registerFont(TTFont(fname_bold, font_path, subfontIndex=1))
                    except Exception:  # noqa: BLE001 - 粗体子字体注册失败：退回常规字重
                        fname_bold = fname
                else:
                    pdfmetrics.registerFont(TTFont(fname, font_path))
                    fname_bold = fname

                return fname, fname_bold
            except Exception:  # noqa: BLE001 - 该字体文件不可用：尝试下一个候选字体
                continue

    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        return "STSong-Light", "STSong-Light"
    except Exception:  # noqa: BLE001 - 内置 CJK 字体不可用：退回 Helvetica（无中文）
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
        analyses: list[dict[str, Any]],
        output_path: str,
        title: str = "",
        subtitle: str = "",
        charts: dict[str, bytes] | None = None,
        watermark: str = "",
    ) -> str:
        if not title:
            title = i18n.tr("report.title")
        doc = SimpleDocTemplate(
            output_path, pagesize=A4,
            leftMargin=2 * cm, rightMargin=2 * cm,
            topMargin=2 * cm, bottomMargin=2 * cm,
        )
        self.story = []
        S = self._get_styles()

        self._add_title_page(title, subtitle, S)
        self.story.append(PageBreak())

        self._add_overview(analyses, S)
        self.story.append(PageBreak())

        for i, atype, params, result in self.iter_analyses(analyses):

            self.story.append(Paragraph(f"{i+1}. {escape(atype)}", S["h1"]))

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
                    try:
                        img = Image(BytesIO(charts[chart_key]), width=14 * cm, height=9 * cm)
                        self.story.append(Spacer(1, 0.4 * cm))
                        self.story.append(img)
                    except Exception:  # noqa: BLE001 - 单张图表嵌入失败：跳过该图不中断报告
                        pass

            self.story.append(Spacer(1, 0.6 * cm))

        self.story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#cccccc")))
        footer_text, _ = self.footers(trace=self.credential_trace(analyses))
        self.story.append(Paragraph(footer_text, S["meta"]))

        if watermark:
            def _wm(canvas, doc):
                canvas.saveState()
                canvas.setFont("Helvetica", 40)
                canvas.setFillColor(HexColor("#888888"), alpha=0.08)
                canvas.drawString(3*cm, 14*cm, watermark)
                canvas.restoreState()
            doc.build(self.story, onFirstPage=_wm, onLaterPages=_wm)
        else:
            doc.build(self.story)
        return output_path

    def _add_title_page(self, title: str, subtitle: str, S: dict):
        self.story.append(Spacer(1, 5 * cm))
        self.story.append(Paragraph(escape(title), S["title"]))
        if subtitle:
            self.story.append(Paragraph(escape(subtitle), S["subtitle"]))
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

    def _add_analysis_detail(self, result: dict, S: dict):
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
            pv = result.get("p_value")
            try:
                pv_text = f"{pv:.4f}"
            except (TypeError, ValueError):
                pv_text = str(pv)
            text = f'<font color="{color}"><b>{msg}</b></font>  (P-value = {pv_text})'
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

    def _add_kv_table(self, title: str, params: dict, S: dict):
        self.story.append(Paragraph(title, S["h2"]))
        rows = [["参数", "值"]]
        rows += [[str(k), str(v)] for k, v in params.items()]
        col_w = [5 * cm, 11 * cm]
        self._draw_table(rows, col_w, S)
        self.story.append(Spacer(1, 0.3 * cm))

    def _draw_table(self, data: list[list[str]], col_widths: list[float],
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
    analyses: list[dict[str, Any]],
    output_path: str,
    title: str = "",
    subtitle: str = "",
    charts: dict[str, bytes] | None = None,
    watermark: str = "",
) -> str:
    """Convenience wrapper: generate a PDF report with optional watermark."""
    return PDFReport().generate(analyses, output_path, title, subtitle, charts, watermark)
