"""8D 问题解决 Tab — D1-D8 stepper + 鱼骨图/FMEA 嵌入"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QListWidget, QListWidgetItem, QStackedWidget,
    QTableWidget, QHeaderView, QMessageBox, QCheckBox, QFileDialog,
)
from PySide6.QtCore import Qt

from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_PRIMARY_STRETCH, BUTTON_SECONDARY, FONT_12B
from analysis.quality.eight_d_engine import (
    EightDReport, D1Step, D2Step, D3Step, D4Step, D5Step, D6Step, D7Step, D8Step,
)


def _make_row(parent, label, widget):
    row = QHBoxLayout()
    row.addWidget(QLabel(label))
    row.addWidget(widget)
    parent.addLayout(row)
    return widget


class EightDTab(BaseAnalysisTab):
    def __init__(self, parent=None):
        self._project_context = None
        super().__init__(parent)
        self.report = EightDReport()
        self._w = {}
        self._setup_ui()

    def set_project_context(self, ctx):
        self._project_context = ctx

    def _setup_ui(self):
        body = QHBoxLayout(self)
        body.setContentsMargins(0, 0, 0, 0)

        left = QWidget()
        left.setFixedWidth(170)
        left.setStyleSheet("background: #1c1c26; border-right: 1px solid #3a3a48;")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(8, 12, 8, 12)
        ll.addWidget(QLabel("8D 步骤"))
        self.step_list = QListWidget()
        self.step_list.setStyleSheet(
            "QListWidget { background: transparent; border: none; } "
            "QListWidget::item { padding: 8px; } "
            "QListWidget::item:selected { background: #2a384a; }"
        )
        for code, label in EightDReport.STEP_LABELS.items():
            item = QListWidgetItem(f"{code}: {label}")
            item.setData(Qt.UserRole, code)
            self.step_list.addItem(item)
        # 先建堆叠容器再连接：直接绑定 setCurrentIndex 会立即求值 self._stack
        self._stack = QStackedWidget()
        self.step_list.currentRowChanged.connect(self._stack.setCurrentIndex)
        ll.addWidget(self.step_list)
        for text, slot in [("导出 PDF", self._export_pdf), ("导出 Markdown", self._export_md)]:
            btn = QPushButton(text)
            btn.setStyleSheet(BUTTON_SECONDARY)
            btn.clicked.connect(slot)
            ll.addWidget(btn)
        fmea_btn = QPushButton("导入 FMEA 原因")
        fmea_btn.setStyleSheet(BUTTON_SECONDARY)
        fmea_btn.setToolTip("从 FMEA 导入失效原因到 D4 鱼骨图")
        fmea_btn.clicked.connect(self._import_from_fmea)
        ll.addWidget(fmea_btn)
        ll.addStretch()
        body.addWidget(left)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(12, 12, 12, 12)
        self._w["title"] = QLineEdit()
        self._w["title"].setPlaceholderText("8D 报告标题")
        rl.addWidget(self._w["title"])
        ir = QHBoxLayout()
        ir.addWidget(QLabel("产品:"))
        self._w["product"] = QLineEdit()
        ir.addWidget(self._w["product"])
        ir.addWidget(QLabel("客户:"))
        self._w["customer"] = QLineEdit()
        ir.addWidget(self._w["customer"])
        rl.addLayout(ir)

        for i in range(8):
            self._stack.addWidget(self._build_step_page(i))
        rl.addWidget(self._stack, 1)

        save_btn = QPushButton("保存 8D 报告")
        save_btn.setFont(FONT_12B)
        save_btn.setMinimumHeight(36)
        save_btn.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        save_btn.clicked.connect(self._save)
        rl.addWidget(save_btn)
        body.addWidget(right)

    def _build_step_page(self, idx):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(6)
        code = f"D{idx + 1}"
        def add(k, v):
            self._w[k] = v

        if code == "D1":
            add("d1_leader", _make_row(lay, "团队长:", QLineEdit()))
            lay.addWidget(QLabel("成员:"))
            t = QTextEdit()
            t.setMaximumHeight(60)
            add("d1_members", t)
            lay.addWidget(t)
        elif code == "D2":
            lay.addWidget(QLabel("问题描述:"))
            t = QTextEdit()
            t.setMaximumHeight(60)
            add("d2_statement", t)
            lay.addWidget(t)
            for label, key in [("何事", "what"), ("何处", "where"), ("何时", "when"),
                               ("谁", "who"), ("为何", "why"), ("如何", "how"), ("多少", "how_many")]:
                add(f"d2_{key}", _make_row(lay, label + ":", QLineEdit()))
        elif code == "D3":
            lay.addWidget(QLabel("临时遏制措施 (ICA):"))
            t = QTextEdit()
            t.setMaximumHeight(60)
            add("d3_ica", t)
            lay.addWidget(t)
            add("d3_date", _make_row(lay, "实施日期:", QLineEdit()))
            cb = QCheckBox("措施已验证")
            add("d3_verified", cb)
            lay.addWidget(cb)
        elif code == "D4":
            root_edit = _make_row(lay, "确认根因:", QLineEdit())
            add("d4_root", root_edit)
            lay.addWidget(QLabel("5Why 分析:"))
            t = QTextEdit()
            t.setMaximumHeight(80)
            add("d4_5why", t)
            lay.addWidget(t)
            fish_label_row = QHBoxLayout()
            fish_label_row.addWidget(QLabel("鱼骨图 (拖拽标签, 滚轮缩放, 双击编辑):"))
            fish_label_row.addStretch()
            from ui.widgets.fishbone_canvas import FishboneCanvas
            from analysis.quality.fishbone import CauseNode
            canvas = FishboneCanvas()
            canvas.setMinimumHeight(220)
            branches_6m = {}
            defaults = [
                ("人员", ["培训不足", "疲劳"]),
                ("机器", ["精度下降", "维护不及时"]),
                ("材料", ["来料变异", "批次差异"]),
                ("方法", ["参数偏移", "SOP不明确"]),
                ("测量", ["量具误差", "人员差异"]),
                ("环境", ["温度波动", "振动干扰"]),
            ]
            for bname, children in defaults:
                root = CauseNode(name=bname)
                for cname in children:
                    root.children.append(CauseNode(name=cname, level=1))
                branches_6m[bname] = root
            canvas.render_fishbone(
                branches_6m, problem=root_edit.text())
            # 问题框与「确认根因」双向实时同步
            root_edit.textChanged.connect(canvas.set_problem)
            canvas.problem_edited.connect(root_edit.setText)
            add("d4_fishbone", canvas)
            lay.addLayout(fish_label_row)
            export_btn = QPushButton("导出图片")
            export_btn.setStyleSheet(BUTTON_SECONDARY)
            export_btn.setCursor(Qt.PointingHandCursor)
            export_btn.clicked.connect(self._export_d4_fishbone)
            fish_label_row.addWidget(export_btn)
            lay.addWidget(canvas)
        elif code == "D5":
            t = QTableWidget(0, 3)
            t.setHorizontalHeaderLabels(["措施", "责任人", "期限"])
            t.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            add("d5_table", t)
            lay.addWidget(t)
            br = QHBoxLayout()
            ab = QPushButton("+ 添加")
            ab.clicked.connect(lambda: t.setRowCount(t.rowCount() + 1))
            br.addWidget(ab)
            db = QPushButton("- 删除")
            db.clicked.connect(lambda: [t.removeRow(r) for r in sorted(set(i.row() for i in t.selectedIndexes()), reverse=True)])
            br.addWidget(db)
            br.addStretch()
            lay.addLayout(br)
            add("d5_verify", _make_row(lay, "验证方法:", QLineEdit()))
        elif code == "D6":
            for label, key, h in [("实施记录:", "d6_impl", 60), ("验证结果:", "d6_valid", 60)]:
                lay.addWidget(QLabel(label))
                t = QTextEdit()
                t.setMaximumHeight(h)
                add(key, t)
                lay.addWidget(t)
        elif code == "D7":
            lay.addWidget(QLabel("预防措施:"))
            t = QTextEdit()
            t.setMaximumHeight(60)
            add("d7_prev", t)
            lay.addWidget(t)
            add("d7_std", _make_row(lay, "标准/文件更新:", QLineEdit()))
            review_btn = QPushButton("检查复审需求")
            review_btn.setStyleSheet(BUTTON_SECONDARY)
            review_btn.clicked.connect(self._check_review)
            lay.addWidget(review_btn)
        elif code == "D8":
            lay.addWidget(QLabel("团队表彰:"))
            t = QTextEdit()
            t.setMaximumHeight(60)
            add("d8_recog", t)
            lay.addWidget(t)
            add("d8_date", _make_row(lay, "关闭日期:", QLineEdit()))
        lay.addStretch()
        return w

    def _text(self, key):
        w = self._w.get(key)
        return w.toPlainText() if hasattr(w, 'toPlainText') else (w.text() if w else "")

    def _export_d4_fishbone(self):
        """导出 D4 鱼骨图为高清 PNG"""
        canvas = self._w.get("d4_fishbone")
        if canvas is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出鱼骨图", "fishbone.png", "PNG 图片 (*.png)")
        if path and not canvas.export_png(path):
            QMessageBox.warning(self, "导出失败", "图片保存失败，请重试")

    def import_fmea_causes(self, fmea_items: list):
        """从 FMEA 导入失效原因到 D4 鱼骨图

        将 FMEA 的 cause 字段按 6M 分类注入鱼骨图骨架。
        """
        from analysis.quality.fishbone import CauseNode

        six_m_mapping = {
            "人员": ["培训", "技能", "经验", "疲劳", "操作", "人员"],
            "机器": ["设备", "机器", "精度", "维护", "保养", "磨损"],
            "材料": ["原料", "材料", "来料", "批次", "成分"],
            "方法": ["工艺", "参数", "SOP", "流程", "方法", "标准"],
            "测量": ["量具", "测量", "检测", "仪器", "校准"],
            "环境": ["温度", "湿度", "振动", "清洁", "环境"],
        }

        causes_by_category = {cat: [] for cat in six_m_mapping}
        for item in fmea_items:
            cause = item.get("cause", "") if isinstance(item, dict) else getattr(item, "cause", "")
            if not cause:
                continue

            matched = False
            for category, keywords in six_m_mapping.items():
                if any(kw in cause for kw in keywords):
                    causes_by_category[category].append(cause)
                    matched = True
                    break
            if not matched:
                causes_by_category["方法"].append(cause)

        branches_6m = {}
        for category, causes in causes_by_category.items():
            root = CauseNode(name=category)
            unique_causes = list(dict.fromkeys(causes))
            for cause in unique_causes[:5]:
                root.children.append(CauseNode(name=cause, level=1))
            if root.children:
                branches_6m[category] = root

        canvas = self._w.get("d4_fishbone")
        if canvas and branches_6m:
            problem = self._w.get("d4_root", QLineEdit()).text() or ""
            canvas.render_fishbone(branches_6m, problem=problem)

            QMessageBox.information(self, "导入完成",
                                    f"已从 FMEA 导入 {len(fmea_items)} 个失效原因到鱼骨图。")
        else:
            QMessageBox.information(self, "导入提示",
                                    "未找到可匹配的失效原因，或鱼骨图未加载。")

    def check_standards_update(self) -> dict:
        """检查 D7 标准更新状态，返回需要复审的信息

        Returns: {
            "has_update": bool,
            "standards_updated": str,
            "preventive_actions": str,
            "review_needed": bool,
        }
        """
        standards = self._text("d7_std")
        preventive = self._text("d7_prev")

        return {
            "has_update": bool(standards),
            "standards_updated": standards,
            "preventive_actions": preventive,
            "review_needed": bool(standards),
        }

    def _check_review(self):
        """检查 D7 复审需求并显示结果"""
        result = self.check_standards_update()
        if result["review_needed"]:
            msg = (f"标准已更新，需要复审:\n\n"
                   f"更新内容: {result['standards_updated']}\n\n"
                   f"预防措施: {result['preventive_actions'] or '(未填写)'}\n\n"
                   "请检查 FMEA 和控制计划是否需要更新。")
        else:
            msg = "未检测到标准更新，无需复审。"
        QMessageBox.information(self, "复审检查", msg)

    def _save(self):
        r = self.report
        r.title = self._w["title"].text()
        r.product = self._w["product"].text()
        r.customer = self._w["customer"].text()
        r.d1 = D1Step(team_leader=self._w["d1_leader"].text(), members=self._text("d1_members"))
        r.d2 = D2Step(problem_statement=self._text("d2_statement"), what=self._text("d2_what"),
                      where=self._text("d2_where"), when=self._text("d2_when"), who=self._text("d2_who"),
                      why=self._text("d2_why"), how=self._text("d2_how"), how_many=self._text("d2_how_many"))
        v = self._w.get("d3_verified")
        r.d3 = D3Step(ica_description=self._text("d3_ica"), implementation_date=self._text("d3_date"),
                      verified=v.isChecked() if isinstance(v, QCheckBox) else False)
        r.d4 = D4Step(root_cause=self._text("d4_root"), five_why=self._text("d4_5why"))
        t = self._w["d5_table"]
        pca = []
        for ri in range(t.rowCount()):
            a = t.item(ri, 0)
            b = t.item(ri, 1)
            c = t.item(ri, 2)
            pca.append({"action": a.text() if a else "", "responsible": b.text() if b else "",
                         "due_date": c.text() if c else ""})
        r.d5 = D5Step(pca_items=pca, verification_method=self._text("d5_verify"))
        r.d6 = D6Step(implementation_notes=self._text("d6_impl"), validation_result=self._text("d6_valid"))
        r.d7 = D7Step(preventive_actions=self._text("d7_prev"), standards_updated=self._text("d7_std"))
        r.d8 = D8Step(recognition_notes=self._text("d8_recog"), closure_date=self._text("d8_date"))
        self._sync_context()
        QMessageBox.information(self, "保存完成", "8D 报告已暂存")

    def _sync_context(self):
        """将 8D 报告写入项目上下文（按标题去重，避免反复保存堆积）"""
        if self._project_context is None:
            return
        report = self.report.to_dict()
        report["id"] = report.get("title") or "8D"
        self._project_context.upsert_eight_d_report(
            report, report_id=report["id"])

    def _import_from_fmea(self):
        """从 FMEA 导入失效原因到 D4 鱼骨图（数据源：项目上下文）"""
        fmea_items = self._project_context.fmea_items if self._project_context else []
        if not fmea_items:
            QMessageBox.information(
                self, "导入 FMEA",
                "未找到 FMEA 数据。请先在 FMEA Tab 中完成分析。")
            return
        self.import_fmea_causes(fmea_items)

    def _export_pdf(self):
        self._save()
        path, _ = QFileDialog.getSaveFileName(self, "导出 8D PDF", "8d_report.pdf", "PDF (*.pdf)")
        if not path:
            return
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            doc = SimpleDocTemplate(path, pagesize=A4)
            styles = getSampleStyleSheet()
            story = [Paragraph(f"8D Report: {self.report.title}", styles["Title"])]
            for i in range(1, 9):
                code = f"D{i}"
                step = getattr(self.report, f"d{i}")
                story.append(Paragraph(f"{code}: {EightDReport.STEP_LABELS[code]}", styles["Heading2"]))
                from xml.sax.saxutils import escape as _html_escape
                raw = str(step.__dict__).replace("{", "").replace("}", "").replace("'", "")
                content = _html_escape(raw)
                story.append(Paragraph(content, styles["BodyText"]))
                story.append(Spacer(1, 12))
            doc.build(story)
            QMessageBox.information(self, "导出完成", "PDF 已导出")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

    def _export_md(self):
        self._save()
        path, _ = QFileDialog.getSaveFileName(self, "导出 8D Markdown", "8d_report.md", "Markdown (*.md)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.report.to_markdown())
            QMessageBox.information(self, "导出完成", "Markdown 已导出")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))
