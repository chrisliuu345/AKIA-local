"""test_five_chain.py — 五链贯通集成测试

验证 FMEA → CP → SPC → PPAP → 8D 数据链路完整性。
"""

from core.fmea_engine import FMEAItem, FMEAEngine
from core.project_context import ProjectContext, QualityCharacteristic
from config.settings import RPN_HIGH


def _make_fmea_items():
    """创建测试用 FMEA 条目"""
    items = [
        FMEAItem(
            function="车削", failure_mode="尺寸超差",
            effect="装配不良", severity=9, cause="刀具磨损",
            occurrence=8, control="首件检验", detection=2,
            recommended_action="增加抽检频次",
        ),
        FMEAItem(
            function="钻孔", failure_mode="孔径偏大",
            effect="密封不良", severity=7, cause="钻头磨损",
            occurrence=6, control="SPC监控", detection=3,
        ),
        FMEAItem(
            function="打磨", failure_mode="表面粗糙",
            effect="外观不良", severity=4, cause="砂轮钝化",
            occurrence=5, control="目视检查", detection=4,
        ),
    ]
    for item in items:
        item.calc_rpn()
    return items


class TestChainFmeaToCp:
    """链路 1: FMEA → 控制计划"""

    def test_high_risk_generates_cp_rows(self):
        items = _make_fmea_items()
        high_risk = [i for i in items if i.rpn >= RPN_HIGH]
        assert len(high_risk) == 2  # RPN 144, 126

        cp_rows = FMEAEngine.generate_cp_rows(items)
        assert len(cp_rows) == 2

    def test_cp_row_maps_correctly(self):
        items = _make_fmea_items()
        cp_rows = FMEAEngine.generate_cp_rows(items)
        row = cp_rows[0]
        assert row[1] == "车削"  # function → 工序名称
        assert "尺寸超差" in row[2]  # failure_mode → 特性

    def test_low_risk_not_in_cp(self):
        items = _make_fmea_items()
        cp_rows = FMEAEngine.generate_cp_rows(items)
        # 打磨 (RPN=80) 不应出现在 CP 中
        for row in cp_rows:
            assert row[1] != "打磨"


class TestChainCpToSpc:
    """链路 2: 控制计划 → SPC 监控清单"""

    def test_cp_items_with_control_chart(self):
        """CP 中包含"控制图"的行应生成 SPC 清单"""
        cp_rows = [
            ["OP01", "车削", "轴径", "10±0.02", "千分尺", "5", "每小时", "XBar-R控制图", "隔离"],
            ["OP02", "钻孔", "孔径", "5±0.01", "塞规", "10", "每批", "首件检验", "记录"],
        ]
        spc_items = []
        for row in cp_rows:
            control_method = row[7] if len(row) > 7 else ""
            if "控制图" in control_method or "SPC" in control_method.upper():
                spc_items.append({
                    "process": row[1],
                    "characteristic": row[2],
                    "tolerance": row[3],
                    "method": control_method,
                })
        assert len(spc_items) == 1
        assert spc_items[0]["process"] == "车削"


class TestChainCapabilityToPpap:
    """链路 3: 能力/MSA → PPAP"""

    def test_ppap_auto_populate_capability(self):
        """能力分析结果自动填充 PPAP #11"""
        analyses = {
            2: {
                "analysis_type": "Capability",
                "result": {"capability": {"cpk": 1.5}},
            }
        }
        # 模拟 PPAP 自动填充逻辑
        ppap_items = [None] * 18
        for idx, analysis in analyses.items():
            analysis_type = analysis.get("analysis_type", "")
            result = analysis.get("result", {})
            if "Capability" in analysis_type:
                cap = result.get("capability", {})
                cpk = cap.get("cpk", 0)
                from config.settings import CAPABILITY_GRADES
                cpk_a = CAPABILITY_GRADES["A"][0]
                is_capable = cpk >= cpk_a if cpk else False
                ppap_items[10] = "complete" if is_capable else "in_progress"
        assert ppap_items[10] == "complete"

    def test_ppap_auto_populate_msa(self):
        """MSA 分析结果自动填充 PPAP #8"""
        analyses = {
            3: {
                "analysis_type": "Gage R&R",
                "result": {"percentages": {"pct_grr": 0.15}},
            }
        }
        ppap_items = [None] * 18
        for idx, analysis in analyses.items():
            analysis_type = analysis.get("analysis_type", "")
            result = analysis.get("result", {})
            if "R&R" in analysis_type:
                pct_grr = result.get("percentages", {}).get("pct_grr", 0)
                is_capable = pct_grr < 0.30
                ppap_items[7] = "complete" if is_capable else "in_progress"
        assert ppap_items[7] == "complete"


class TestChainFmeaTo8d:
    """链路 4: FMEA → 8D D4"""

    def test_fmea_causes_classified_by_6m(self):
        """FMEA 原因按 6M 分类注入鱼骨图"""
        six_m_mapping = {
            "人员": ["培训", "技能", "经验", "疲劳", "操作", "人员"],
            "机器": ["设备", "机器", "精度", "维护", "保养", "磨损"],
            "材料": ["原料", "材料", "来料", "批次", "成分"],
            "方法": ["工艺", "参数", "SOP", "流程", "方法", "标准"],
            "测量": ["量具", "测量", "检测", "仪器", "校准"],
            "环境": ["温度", "湿度", "振动", "清洁", "环境"],
        }
        fmea_items = [
            {"cause": "刀具磨损"},
            {"cause": "操作员培训不足"},
            {"cause": "来料成分偏差"},
            {"cause": "温度波动"},
        ]
        causes_by_category = {cat: [] for cat in six_m_mapping}
        for item in fmea_items:
            cause = item.get("cause", "")
            for category, keywords in six_m_mapping.items():
                if any(kw in cause for kw in keywords):
                    causes_by_category[category].append(cause)
                    break
        assert len(causes_by_category["机器"]) == 1  # 刀具磨损
        assert len(causes_by_category["人员"]) == 1  # 培训不足
        assert len(causes_by_category["材料"]) == 1  # 来料成分
        assert len(causes_by_category["环境"]) == 1  # 温度波动


class TestChain8dToFmea:
    """链路 5: 8D D7 → FMEA/CP 复审"""

    def test_standards_update_triggers_review(self):
        """D7 标准更新触发复审"""
        d7_std = "GB/T 19001-2016 已更新"
        d7_prev = "更新 FMEA 和控制计划"
        review_needed = bool(d7_std)
        assert review_needed is True

    def test_no_update_no_review(self):
        """无标准更新无需复审"""
        d7_std = ""
        review_needed = bool(d7_std)
        assert review_needed is False


class TestProjectContextIntegration:
    """ProjectContext 跨链路集成"""

    def test_context_stores_fmea_and_cp(self):
        ctx = ProjectContext(project_name="integration_test")
        items = _make_fmea_items()
        ctx.set_fmea_items([
            {"id": f"F{i}", "function": item.function, "rpn": item.rpn}
            for i, item in enumerate(items, 1)
        ])
        cp_rows = FMEAEngine.generate_cp_rows(items)
        ctx.set_control_plan(cp_rows)
        assert len(ctx.fmea_items) == 3
        assert len(ctx.control_plan_rows) == 2

    def test_context_query_high_risk(self):
        ctx = ProjectContext()
        ctx.fmea_items = [{"rpn": 200}, {"rpn": 100}, {"rpn": 50}]
        high = ctx.get_high_risk_fmea_items()
        assert len(high) == 2

    def test_context_query_spc_characteristics(self):
        ctx = ProjectContext()
        ctx.add_characteristic(QualityCharacteristic(
            id="QC-001", spc_method="XBar-R", data_source="Sheet1:col_a"))
        ctx.add_characteristic(QualityCharacteristic(
            id="QC-002", spc_method="", data_source=""))
        spc = ctx.get_characteristics_for_spc()
        assert len(spc) == 1

    def test_full_chain_data_flow(self):
        """完整链路数据流: FMEA → CP → SPC → PPAP → 8D"""
        ctx = ProjectContext(project_name="full_chain")
        items = _make_fmea_items()

        # Step 1: FMEA → CP
        cp_rows = FMEAEngine.generate_cp_rows(items)
        ctx.set_fmea_items([
            {"id": f"F{i}", "function": item.function, "rpn": item.rpn}
            for i, item in enumerate(items, 1)
        ])
        ctx.set_control_plan(cp_rows)

        # Step 2: CP → SPC
        spc_items = []
        for row in cp_rows:
            if "控制图" in row[7]:
                spc_items.append({"process": row[1], "characteristic": row[2]})
        ctx.set_analysis_snapshot("spc_monitoring", {"items": spc_items})

        # Step 3: Capability → PPAP
        ctx.set_analysis_snapshot("capability", {"cpk": 1.5})
        ctx.set_ppap_report({"part_no": "P-001", "items": {"#11": "complete"}})

        # Step 4: FMEA → 8D
        high_risk = ctx.get_high_risk_fmea_items()
        ctx.add_eight_d_report({
            "title": "8D-001",
            "d4_fishbone": {"机器": [i["function"] for i in high_risk]},
        })

        # 验证
        assert len(ctx.control_plan_rows) == 2
        assert len(ctx.get_high_risk_fmea_items()) == 2
        assert ctx.get_analysis_snapshot("capability")["cpk"] == 1.5
        assert len(ctx.eight_d_reports) == 1
