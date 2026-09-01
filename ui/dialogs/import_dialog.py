"""数据导入对话框 — 文件选择 + 模式感知 + 格式校验"""

import os
from typing import Tuple

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QFileDialog,
    QGroupBox, QHeaderView, QDialogButtonBox, QMessageBox,
)
from PySide6.QtGui import QFont

from config.settings import SUPPORTED_EXCEL_EXTENSIONS, MAX_PREVIEW_ROWS
from core.excel_utils import read_excel_auto
from ui.theme import colors as theme_colors
from ui.font_config import get_ui_font


class ImportDialog(QDialog):
    def __init__(self, parent=None, mode: str = "quality"):
        super().__init__(parent)
        self.mode = mode
        self.file_path = ""
        self.sheet_names = []
        self._error_message = ""
        self._ie_summary = ""
        self._has_numeric = True
        self._setup_ui()

    def _setup_ui(self):
        tc = theme_colors()
        mode_color = "#1b5faa" if self.mode == "quality" else "#27ae60"
        mode_label = "工作表数据" if self.mode == "quality" else "IE 分析数据"

        self.setWindowTitle(f"导入{mode_label}")
        self.setStyleSheet(f"background-color: {tc['bg_body']};")
        self.setMinimumSize(800, 500)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        mode_badge = QLabel(f"  {mode_label}  ")
        mode_badge.setFont(QFont(get_ui_font(), 10, QFont.Bold))
        mode_badge.setStyleSheet(
            f"background-color: {mode_color}; color: white; border-radius: 4px; padding: 4px 8px;"
        )
        header_layout.addWidget(mode_badge)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        file_group = QGroupBox("选择文件")
        file_layout = QHBoxLayout(file_group)
        self.file_label = QLabel("未选择文件")
        self.file_label.setStyleSheet(f"color: {tc['text_dim']};")
        file_layout.addWidget(self.file_label, 1)
        browse_btn = QPushButton("浏览...")
        browse_btn.setMinimumSize(80, 30)
        browse_btn.clicked.connect(self._on_browse)
        file_layout.addWidget(browse_btn)
        layout.addWidget(file_group)

        self.info_label = QLabel("")
        self.info_label.setFont(QFont(get_ui_font(), 9))
        self.info_label.setStyleSheet(f"color: {tc['text_secondary']}; padding: 2px 6px;")
        layout.addWidget(self.info_label)

        hint_group = QGroupBox("格式说明")
        hint_layout = QVBoxLayout(hint_group)
        self.hint_label = QLabel(self._get_format_hint())
        self.hint_label.setWordWrap(True)
        self.hint_label.setFont(QFont(get_ui_font(), 9))
        self.hint_label.setStyleSheet(f"color: {tc['text_secondary']}; padding: 4px;")
        hint_layout.addWidget(self.hint_label)
        layout.addWidget(hint_group)

        preview_group = QGroupBox("数据预览 (前100行)")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_table = QTableWidget()
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.preview_table.setMinimumHeight(200)
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setStyleSheet(
            f"QTableWidget {{ background: {tc['bg_card']}; color: {tc['text_primary']}; "
            f"gridline-color: {tc['border_light']}; border: 1px solid {tc['border_light']}; }}"
            f"QHeaderView::section {{ background: {tc['bg_table_header']}; color: {tc['text_primary']}; "
            f"padding: 4px 8px; border: 1px solid {tc['border_light']}; }}"
        )
        preview_layout.addWidget(self.preview_table)
        layout.addWidget(preview_group, 1)

        self.status_label = QLabel(self._get_default_status())
        self.status_label.setStyleSheet(f"color: {tc['text_secondary']};")
        layout.addWidget(self.status_label)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _get_format_hint(self) -> str:
        if self.mode == "quality":
            return "支持任意含数值列的 Excel 文件。\n第一行建议为表头，数据列为数字。自动识别测量列、规格限、分组列。"
        hints = [
            "支持以下数据表格式（Sheet名含关键词可自动识别）：",
            "",
        ]
        from core.data_objects import OBJECT_CLASSES
        type_labels = {
            "Process": "工序表", "TimeObservation": "时间观测",
            "QualityRecord": "质量记录", "MaterialFlow": "物流", "Resource": "资源",
        }
        for obj_type, label in type_labels.items():
            cls = OBJECT_CLASSES.get(obj_type)
            if cls:
                hints.append(f"  {label}:  {cls.format_example()}")
        hints.append("")
        hints.append("列名支持模糊匹配（中英文均可），Sheet名称建议包含关键词。")
        return "\n".join(hints)

    def _get_default_status(self) -> str:
        if self.mode == "quality":
            return "请选择 Excel 文件 (.xlsx/.xls) — 工作表数据"
        return "请选择 Excel 文件 (.xlsx/.xls) — 需含工序表/时间观测等 IE 数据"

    def _on_browse(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择数据文件", "",
            "Excel 文件 (*.xlsx *.xls *.xlsm);;所有文件 (*.*)",
        )
        if file_path:
            try:
                import pandas as pd
                ext = os.path.splitext(file_path)[1].lower()
                if ext not in SUPPORTED_EXCEL_EXTENSIONS:
                    self.status_label.setText(f"不支持的文件格式: {ext}")
                    return

                xl = None
                if ext == ".xls":
                    for eng in ["calamine", "xlrd"]:
                        try:
                            xl = pd.ExcelFile(file_path, engine=eng)
                            break
                        except Exception:
                            continue
                    if xl is None:
                        raise ValueError("无法读取 .xls 文件，请安装: pip install python-calamine")
                else:
                    xl = pd.ExcelFile(file_path, engine="openpyxl")
                self.file_path = file_path
                self.sheet_names = list(xl.sheet_names)
                self.file_label.setText(os.path.basename(file_path))
                self.file_label.setStyleSheet("")

                total_rows = 0
                for s in self.sheet_names:
                    try:
                        if hasattr(xl, 'book') and hasattr(xl.book, 'get_sheet_by_name'):
                            total_rows += xl.book.get_sheet_by_name(s).max_row or 0
                        else:
                            total_rows += len(xl.parse(s))
                    except Exception:
                        total_rows += 0
                info_parts = [
                    f"工作表: {len(self.sheet_names)} 个  ({', '.join(self.sheet_names[:6])}"
                    f"{' ...' if len(self.sheet_names) > 6 else ''})  |  估算总行数: ~{total_rows}"
                ]

                if self.mode == "ie":
                    self._detect_ie_format()
                    if self._ie_summary:
                        info_parts.append(self._ie_summary)

                self.info_label.setText("\n".join(info_parts))

                if self.sheet_names:
                    self._load_preview(self.sheet_names[0])

                self.status_label.setText(
                    f"已选择: {os.path.basename(file_path)} | "
                    f"{len(self.sheet_names)} 个工作表"
                )
            except Exception as e:
                self.status_label.setText(f"加载失败: {str(e)}")

    def _detect_ie_format(self):
        try:
            raw = {}
            for sname in self.sheet_names[:10]:
                raw[sname] = read_excel_auto(self.file_path, sheet_name=sname,
                                             nrows=50, dtype=str)
            from core.ie_parser import IEDataParser
            parser = IEDataParser()
            ie_data = parser.parse_all(raw)
            if ie_data:
                parts = []
                for obj_type, objects in ie_data.items():
                    type_labels = {
                        "Process": "工序表", "TimeObservation": "时间观测",
                        "QualityRecord": "质量记录", "MaterialFlow": "物流", "Resource": "资源",
                    }
                    label = type_labels.get(obj_type, obj_type)
                    parts.append(f"{label}: {len(objects)} 条")
                self._ie_summary = "检测到: " + " | ".join(parts)
                self._has_numeric = True
            else:
                self._ie_summary = "未检测到 IE 数据格式"
                self._has_numeric = False
        except Exception:
            self._ie_summary = "格式检测异常"
            self._has_numeric = False

    def _load_preview(self, sheet_name: str):
        if not self.file_path:
            return
        try:
            import pandas as pd
            ext = os.path.splitext(self.file_path)[1].lower()
            if ext == ".xls":
                df = None
                for eng in ["calamine", "xlrd"]:
                    try:
                        df = pd.read_excel(self.file_path, sheet_name=sheet_name,
                                           nrows=MAX_PREVIEW_ROWS, engine=eng)
                        break
                    except Exception:
                        continue
                if df is None:
                    return
            else:
                df = pd.read_excel(self.file_path, sheet_name=sheet_name,
                                   nrows=MAX_PREVIEW_ROWS, engine="openpyxl")
            self.preview_table.setRowCount(min(MAX_PREVIEW_ROWS, len(df)))
            self.preview_table.setColumnCount(len(df.columns))
            self.preview_table.setHorizontalHeaderLabels([str(c) for c in df.columns])
            for i in range(min(MAX_PREVIEW_ROWS, len(df))):
                for j, col in enumerate(df.columns):
                    val = str(df.iloc[i, j]) if pd.notna(df.iloc[i, j]) else ""
                    self.preview_table.setItem(i, j, QTableWidgetItem(val[:50]))
        except Exception as e:
            self.status_label.setText(f"预览失败: {str(e)}")

    def _on_accept(self):
        self._error_message = ""
        if not self.file_path:
            self._error_message = "请先选择一个文件"
            self.reject()
            return

        valid = self._validate_quality() if self.mode == "quality" else self._validate_ie()
        if not valid:
            ret = QMessageBox.warning(
                self, "格式校验",
                f"{self._error_message}\n\n是否仍然尝试导入？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if ret != QMessageBox.Yes:
                return

        self.accept()

    def _validate_quality(self) -> bool:
        try:
            from core.data_parser import DataParser
            parser = DataParser()
            for sname in self.sheet_names[:5]:
                df = read_excel_auto(self.file_path, sheet_name=sname,
                                     nrows=100, dtype=str)
                if len(df) < 2:
                    continue
                try:
                    _, info = parser.prepare(df)
                except Exception:
                    continue
                numeric = info.get("numeric_columns", [])
                if numeric:
                    self._has_numeric = True
                    return True
            self._has_numeric = False
            self._error_message = (
                "未检测到数值列。\n\n"
                "质量分析需要至少一列数值数据。\n\n"
                "请检查：\n"
                "1. Excel 第一行是否为表头\n"
                "2. 数据列是否包含数字（非文本）\n"
                "3. 是否有 *** / N/A / none 等非数值标记"
            )
            return False
        except Exception as e:
            self._error_message = f"文件读取失败: {str(e)}"
            return False

    def _validate_ie(self) -> bool:
        try:
            raw = {}
            for sname in self.sheet_names:
                raw[sname] = read_excel_auto(self.file_path, sheet_name=sname,
                                             nrows=100, dtype=str)
            from core.ie_parser import IEDataParser
            parser = IEDataParser()
            ie_data = parser.parse_all(raw)
            if ie_data:
                self._has_numeric = True
                return True
            self._has_numeric = False
            self._error_message = IEDataParser.format_help()
            return False
        except Exception as e:
            self._error_message = f"格式检测失败: {str(e)}"
            return False

    def get_selection(self) -> Tuple[str, list]:
        return self.file_path, self.sheet_names

    @property
    def error_message(self) -> str:
        return self._error_message

    @property
    def has_data(self) -> bool:
        return self._has_numeric
