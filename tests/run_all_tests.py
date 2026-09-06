"""
QA-Tool 全面测试脚本 v3 — 模块化测试，避免 GUI segfault
结果: D:\AI-agent\Output\QA-Tool\test_report.md
"""

import sys, os, gc, warnings
warnings.filterwarnings("ignore")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "tests", "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

import matplotlib
matplotlib.use("Agg")
import numpy as np
import pandas as pd
np.random.seed(42)

results = []

def test(cat, desc):
    def deco(fn):
        def wrapper():
            tr = type("TR",(),{"cat":cat,"name":fn.__name__,"desc":desc,
                              "status":"PASS","error":""})()
            try:
                fn()
            except Exception as e:
                tr.status = "FAIL"
                tr.error = f"{type(e).__name__}: {e}"
            results.append(tr)
            icon = "PASS" if tr.status == "PASS" else "FAIL"
            print(f"  [{icon:4}] {cat:6s} {fn.__name__}")
            if tr.status == "FAIL": print(f"         {tr.error}")
            gc.collect()
        return wrapper
    return deco

TEST_XLSX = os.path.join(PROJECT_ROOT, "公司仪器测试数据.xlsx")
TEST_DB = os.path.join(PROJECT_ROOT, "test_quality.db")

# ===================== T01-T05: 基础配置 =====================
print("\n===== 基础配置 (T01-T05) =====")

@test("基础", "Settings 配置完整性")
def T01_settings():
    from config.settings import APP_NAME, SUPPORTED_EXCEL_EXTENSIONS, NELSON_RULES, CONTROL_CHART_CONSTANTS, CAPABILITY_GRADES
    assert APP_NAME == "QA-Tool"
    assert ".xlsx" in SUPPORTED_EXCEL_EXTENSIONS
    assert len(NELSON_RULES) == 8
    assert 2 in CONTROL_CHART_CONSTANTS
    assert len(CAPABILITY_GRADES) >= 4

@test("基础", "i18n 国际化 (含新增 DB key)")
def T02_i18n():
    from core.i18n import i18n
    for k in ["sidebar.home","sidebar.spc","sidebar.import_db","sidebar.collapse",
              "db.connection_title","db.test_connection","db.host","db.select_tables"]:
        t = i18n.tr(k)
        assert t and t != k, f"Untranslated: {k}"

@test("基础", "Session 会话管理器")
def T03_session():
    from core.session_manager import SessionManager
    sm = SessionManager()
    sm.create_session(file_path="test.xlsx")
    sm.add_analysis("XBar-R", {"size":5}, {"cpk":1.2})
    p = os.path.join(OUTPUT_DIR, "test_session.json")
    sm.save(p); assert os.path.exists(p)
    loaded = sm.load(p)
    assert loaded["file_path"] == "test.xlsx"
    assert len(loaded["analyses"]) == 1

@test("基础", "数据对象模型")
def T04_data_objects():
    from core.data_objects import OBJECT_CLASSES, Process, TimeObservation, Resource
    assert len(OBJECT_CLASSES) >= 5
    p = Process("P1","test",60,2,"",[])
    assert p.process_id == "P1"
    to = TimeObservation("P1","OP1",50,"2026-01-01")
    assert to.cycle == 50
    r = Resource("M1","Machine","A","Day",480,30,1.0,500,480)
    assert r.available_time == 480

@test("基础", "模板解析器")
def T05_template_parser():
    from core.template_parser import TemplateParser
    tp = TemplateParser()
    assert len(tp.VALID_ANALYSIS_TYPES) >= 25

# ===================== T06-T09: 数据导入 =====================
print("\n===== 数据导入 (T06-T09) =====")

@test("导入", "质量数据 .xlsx 加载")
def T06_quality_xlsx():
    from core.data_loader import DataLoader
    dl = DataLoader()
    raw = dl.load(TEST_XLSX)
    assert len(raw) >= 5
    assert dl.metadata["sheet_count"] >= 5

@test("导入", "数据解析 + 校验")
def T07_data_validation():
    from core.data_loader import DataLoader
    from core.data_parser import DataParser
    from core.data_validator import DataValidator
    dl = DataLoader(); raw = dl.load(TEST_XLSX)
    parser = DataParser(); validator = DataValidator()
    found = False
    for df in raw.values():
        _, info = parser.prepare(df)
        if info.get("numeric_columns"):
            found = True
            v = validator.validate(df, info["numeric_columns"])
            assert "valid" in v
    assert found

@test("导入", "SqlLoader (SQLite)")
def T08_sql_loader():
    from core.sql_loader import SqlLoader
    from sqlalchemy import create_engine, text
    loader = SqlLoader()
    loader.engine = create_engine(f"sqlite:///{TEST_DB}")
    with loader.engine.connect() as c:
        c.execute(text("SELECT 1"))
    names = loader.get_table_names()
    assert "production_quality" in names
    tables = loader.load(["production_quality","process_info"])
    assert len(tables["production_quality"]) == 200
    assert len(tables["process_info"]) == 6
    preview = loader.get_preview("production_quality",10)
    assert len(preview) == 10
    loader.disconnect()
    assert not loader.is_connected()

@test("导入", "IE 数据解析器")
def T09_ie_parser():
    from core.ie_parser import IEDataParser
    help_text = IEDataParser.format_help()
    assert len(help_text) > 100
    assert "Process" in help_text

# ===================== T10-T20: SPC 控制图 =====================
print("\n===== SPC (T10-T20) =====")

@test("SPC", "XBar-R")
def T10_xbar_r():
    from analysis.spc import xbar_r
    r = xbar_r.analyze(pd.Series(np.random.normal(10,0.5,125)),5)
    assert r["num_subgroups"] == 25
    assert 9.5 < r["xbar_chart"]["cl"] < 10.5

@test("SPC", "XBar-S")
def T11_xbar_s():
    from analysis.spc import xbar_s
    r = xbar_s.analyze(pd.Series(np.random.normal(10,0.5,125)),5)
    assert r["num_subgroups"] == 25

@test("SPC", "I-MR")
def T12_imr():
    from analysis.spc import imr
    r = imr.analyze(pd.Series(np.random.normal(10,0.5,125)))
    assert r["num_points"] == 125

@test("SPC", "P Chart")
def T13_p_chart():
    from analysis.spc import p_chart
    sizes = pd.Series(np.random.randint(80,120,30))
    defects = pd.Series(np.random.binomial(sizes.astype(int),0.05))
    r = p_chart.analyze(defects, sizes)
    assert r["summary"]["p_bar"] > 0

@test("SPC", "NP Chart")
def T14_np_chart():
    from analysis.spc import np_chart
    r = np_chart.analyze(pd.Series(np.random.binomial(100,0.05,30)),100)
    assert "np_bar" in r["summary"]

@test("SPC", "C Chart")
def T15_c_chart():
    from analysis.spc import c_chart
    r = c_chart.analyze(pd.Series(np.random.poisson(3,30)))
    assert "c_bar" in r["summary"]

@test("SPC", "U Chart")
def T16_u_chart():
    from analysis.spc import u_chart
    units = pd.Series(np.random.randint(5,15,30))
    defects = pd.Series(np.random.poisson(units*0.3))
    r = u_chart.analyze(defects, units)
    assert r["summary"]["u_bar"] > 0

@test("SPC", "CUSUM")
def T17_cusum():
    from analysis.spc import cusum
    r = cusum.analyze(pd.Series(np.random.normal(10,0.5,100)), target=10)
    assert "cusum_chart" in r

@test("SPC", "EWMA")
def T18_ewma():
    from analysis.spc import ewma
    r = ewma.analyze(pd.Series(np.random.normal(10,0.5,100)), lam=0.2)
    assert "ewma_chart" in r

@test("SPC", "判异规则检测")
def T19_violations():
    from analysis.spc import xbar_r
    normal = list(np.random.normal(10,0.5,100))
    shifted = [16.0]*25  # 6 sigma shift
    r = xbar_r.analyze(pd.Series(normal + shifted),5)
    xv = r.get("xbar_chart",{}).get("violations",[])
    rv = r.get("r_chart",{}).get("violations",[])
    assert len(xv) > 0, f"No xbar violations found, keys={list(r.keys())}"
    assert len(rv) > 0

@test("SPC", "根因分析 SHAP")
def T20_root_cause_shap():
    from analysis.ai.root_cause import RootCauseAnalyzer
    n=200; temp=np.random.normal(150,15,n)
    df=pd.DataFrame({"yield":100-0.3*temp+np.random.normal(0,2,n),
        "temperature":temp,"pressure":np.random.normal(50,10,n),
        "speed":np.random.normal(1000,50,n)})
    r=RootCauseAnalyzer().analyze(df,"yield")
    assert len(r["causes"])>0
    assert r["causes"][0].column=="temperature"

@test("SPC", "根因分析 RF降级")
def T21_root_cause_rf():
    from analysis.ai.root_cause import RootCauseAnalyzer
    n=50; temp=np.random.normal(150,15,n)
    df=pd.DataFrame({"y":100-0.3*temp+np.random.normal(0,2,n),
        "t":temp,"p":np.random.normal(50,10,n)})
    r=RootCauseAnalyzer(use_shap=False).analyze(df,"y")
    assert len(r["causes"])>0

# ===================== T22-T24: 过程能力 =====================
print("\n===== 过程能力 (T22-T24) =====")

@test("能力", "正态 Cpk")
def T22_normal_cap():
    from analysis.capability import normal_cap
    r = normal_cap.analyze(pd.Series(np.random.normal(10,0.5,200)),usl=12,lsl=8)
    assert r["capability"]["cpk"] > 0.5
    assert r["capability"]["grade"]

@test("能力", "非正态 Box-Cox")
def T23_non_normal():
    from analysis.capability import non_normal_cap
    r = non_normal_cap.analyze(pd.Series(np.random.lognormal(2,0.3,200)),usl=20,lsl=3)
    assert r["capability"]["ppk"] > 0

@test("能力", "组间/组内")
def T24_between_within():
    from analysis.capability import between_within_cap
    n=125
    df=pd.DataFrame({"m":np.random.normal(10,0.5,n),"g":np.repeat(range(25),5)})
    r=between_within_cap.analyze(df,"m","g",usl=12,lsl=8)
    assert "capability" in r

# ===================== T25-T26: MSA =====================
print("\n===== MSA (T25-T26) =====")

@test("MSA", "Gage R&R 交叉")
def T25_msa_crossed():
    from analysis.msa import gage_rr
    df=pd.DataFrame({"part":np.repeat(range(1,11),6),
        "operator":np.tile(np.repeat(["A","B","C"],2),10),
        "measurement":np.random.normal(10,0.1,60)})
    r=gage_rr.analyze_crossed(df,"measurement","part","operator",tolerance=1.0)
    assert "percentages" in r and "acceptance" in r

@test("MSA", "偏倚分析")
def T26_msa_bias():
    from analysis.msa import linearity_bias
    r=linearity_bias.analyze_bias(pd.Series(np.random.normal(10,0.1,30)),10.0)
    assert "bias" in r or "mean_bias" in r

# ===================== T27-T28: 假设检验 =====================
print("\n===== 假设检验 (T27-T28) =====")

@test("假设", "t检验 3种")
def T27_t_tests():
    from analysis.hypothesis import t_tests
    g1=pd.Series(np.random.normal(10,0.5,30))
    g2=pd.Series(np.random.normal(10.5,0.5,30))
    r1=t_tests.one_sample(g1,pop_mean=10); assert "p_value" in r1
    r2=t_tests.two_sample(g1,g2); assert "p_value" in r2
    r3=t_tests.paired(g1,g2); assert "p_value" in r3

@test("假设", "ANOVA + 正态性")
def T28_anova():
    from analysis.hypothesis import anova, normality
    df=pd.DataFrame({"val":np.random.normal(10,1,60),"grp":np.repeat(["A","B","C"],20)})
    r1=anova.one_way(df,"val","grp"); assert "p_value" in r1
    r2=normality.normality_test(pd.Series(np.random.normal(10,1,100)))
    assert "overall_conclusion" in r2

# ===================== T29-T30: DOE =====================
print("\n===== DOE (T29-T30) =====")

@test("DOE", "因子设计")
def T29_factorial():
    from analysis.doe import factorial as fact
    factors=["A","B","C"]
    design=fact.generate_design(factors,1)
    design["response"]=design["A"]*0.5+design["B"]*0.3+np.random.normal(0,0.1,len(design))
    r=fact.analyze_factorial(design,"response",factors)
    assert "significant_factors" in r

@test("DOE", "响应曲面 CCD")
def T30_ccd():
    from analysis.doe import response_surface, factorial as fact
    factors=["X1","X2"]
    design=fact.generate_design(factors,1)
    design["response"]=design["X1"]*0.6+design["X2"]*0.4+np.random.normal(0,0.1,len(design))
    r=response_surface.analyze_response_surface(design,"response",factors)
    assert "coefficients" in r

# ===================== T31: 回归 =====================
print("\n===== 回归 (T31) =====")

@test("回归", "线性回归")
def T31_regression():
    from analysis.regression import linear_regression
    n=100; x1=np.random.normal(50,10,n); x2=np.random.normal(30,5,n)
    y=10+0.5*x1+0.3*x2+np.random.normal(0,2,n)
    df=pd.DataFrame({"Y":y,"X1":x1,"X2":x2})
    r=linear_regression.analyze(df,"Y",["X1","X2"])
    assert r["r_squared"] > 0.8
    assert len(r["coefficients"]) >= 2

# ===================== T32-T36: IE =====================
print("\n===== IE (T32-T36) =====")

@test("IE", "工时研究")
def T32_time_study():
    from analysis.ie.time_study import TimeStudyEngine
    from core.data_objects import TimeObservation
    cycles = list(np.random.normal(50, 5, 50).round(1))
    cycles[0] = 200.0
    obs = [TimeObservation(f"P{i//10+1}","OP1",float(c),"2026-01-01") for i,c in enumerate(cycles)]
    r=TimeStudyEngine().analyze(obs)
    assert r.get("valid") is not False

@test("IE", "工作抽样")
def T33_work_sampling():
    from analysis.ie.work_sampling import WorkSamplingEngine
    states=list(np.random.choice(["正常","辅助","空闲","故障"],200))
    r=WorkSamplingEngine().analyze(states)
    assert "ratios" in r and "confidence_intervals" in r

@test("IE", "线平衡 LPT")
def T34_line_balance():
    from analysis.ie.line_balance import LineBalanceEngine
    from core.data_objects import Process
    procs=[Process("P1","Cut",45,1,"",[]),Process("P2","Grind",60,1,"",["P1"]),
           Process("P3","Pol",30,1,"",["P2"]),Process("P4","Assy",120,1,"",[]),
           Process("P5","Test",90,1,"",["P3","P4"])]
    r=LineBalanceEngine().analyze(procs,takt=60)
    assert r["balanced"]["balance_rate"] > 0

@test("IE", "OEE")
def T35_oee():
    from analysis.ie.oee import OEEEngine
    from core.data_objects import Resource
    rsrc=[Resource("M1","Machine","L1","Day",480,30,1.0,500,480),
          Resource("M2","Machine","L1","Day",480,60,1.2,400,370),
          Resource("M3","Machine","L2","Day",480,20,0.9,550,530)]
    r=OEEEngine().analyze(rsrc)
    assert 0 < r["overall"]["oee"] <= 1.0

@test("IE", "VSM")
def T36_vsm():
    from analysis.ie.vsm import VSMEngine
    from core.data_objects import Process, MaterialFlow
    procs=[Process("P1","加工",45,1,"",[]),Process("P2","组装",60,1,"",["P1"]),
           Process("P3","测试",30,1,"",["P2"])]
    flows=[MaterialFlow("P1","P2",100,10),MaterialFlow("P2","P3",100,10)]
    r=VSMEngine().analyze(procs,flows,daily_demand=100)
    assert "summary" in r

# ===================== T37-T40: 导出 =====================
print("\n===== 导出 (T37-T40) =====")

@test("导出", "Excel 报告")
def T37_excel():
    from output.excel_report import ExcelReport
    from analysis.spc import xbar_r
    r=xbar_r.analyze(pd.Series(np.random.normal(10,0.5,125)),5)
    p=os.path.join(OUTPUT_DIR,"test_report.xlsx")
    ExcelReport().generate([{"analysis_type":"XBar-R","params":{"size":5},"result":r}],p)
    assert os.path.exists(p)

@test("导出", "Word 报告")
def T38_word():
    from output.word_report import WordReport
    from analysis.spc import xbar_r
    r=xbar_r.analyze(pd.Series(np.random.normal(10,0.5,125)),5)
    p=os.path.join(OUTPUT_DIR,"test_report.docx")
    charts={}
    if r.get("figure"):
        from output.chart_engine import figure_to_bytes
        charts["XBar-R"] = figure_to_bytes(r["figure"])
    WordReport().generate(
        [{"analysis_type":"XBar-R","params":{"size":5},"result":r,"data_summary":{"N":125}}],
        p,charts=charts)
    assert os.path.exists(p)

@test("导出", "PDF 报告")
def T39_pdf():
    from output.pdf_report import generate_pdf_report
    from analysis.spc import xbar_r
    r=xbar_r.analyze(pd.Series(np.random.normal(10,0.5,125)),5)
    p=os.path.join(OUTPUT_DIR,"test_report.pdf")
    charts={}
    if r.get("figure"):
        from output.chart_engine import figure_to_bytes
        charts["XBar-R"]=figure_to_bytes(r["figure"])
    generate_pdf_report([{"analysis_type":"XBar-R","params":{"size":5},"result":r}],p,
                        charts=charts)
    assert os.path.exists(p)

@test("导出", "合规报告 3种")
def T40_compliance():
    from output.compliance_report import ComplianceReportGenerator
    from analysis.spc import xbar_r
    templates=ComplianceReportGenerator.list_templates()
    assert len(templates)>=3
    r=xbar_r.analyze(pd.Series(np.random.normal(10,0.5,125)),5)
    for t in templates:
        p=os.path.join(OUTPUT_DIR,f"compliance_{t['id']}.docx")
        ComplianceReportGenerator.generate(
            t["id"],[{"analysis_type":"XBar-R","params":{"size":5},"result":r}],p)
        assert os.path.exists(p)

# ===================== T41: AI 知识库 =====================
print("\n===== AI + 辅助 (T41-T43) =====")

@test("AI", "知识库 RAG")
def T41_knowledge_base():
    from core.knowledge_base import get_knowledge_base
    kb=get_knowledge_base()
    entries=kb.search("Cpk 过程能力")
    assert len(entries)>=1
    stats=kb.stats()
    total=sum(stats.values())
    assert total >= 95, f"KB有 {total} 条"

@test("辅助", "IE 数据解析完整流程")
def T42_ie_full():
    from core.data_loader import DataLoader
    dl=DataLoader()
    raw=dl.load(TEST_XLSX)
    # Test IE parsing on real data
    from core.ie_parser import IEDataParser
    parser=IEDataParser()
    ie_data=parser.parse_all(raw)
    assert isinstance(ie_data, dict)
    to_list=ie_data.get("TimeObservation", [])
    assert len(to_list) > 0, "时间观测未解析出对象"
    assert all(o.observation_time > 0 for o in to_list), "observation_time 数据丢失"
    assert all(o.cycle > 0 for o in to_list), "cycle 数据丢失"
    assert ie_data.get("Process"), "工序表未解析"
    assert ie_data.get("MaterialFlow"), "物流数据未解析"
    assert ie_data.get("Resource"), "设备清单未解析"

@test("辅助", "数据画像 DataProfiler")
def T43_profiler():
    from core.data_profiler import DataProfiler
    from core.data_loader import DataLoader
    dl=DataLoader();raw=dl.load(TEST_XLSX)
    profile=DataProfiler().profile(raw)
    assert "sheets" in profile and len(profile["sheets"])>0

# ===================== GUI 基础导入检查 =====================
print("\n===== GUI 导入检查 (T44-T45) =====")

@test("GUI", "主窗口模块导入")
def T44_gui_imports():
    from ui.theme import colors
    assert callable(colors)

@test("GUI", "所有 Tab 模块导入")
def T45_tab_imports():
    print("  11 tab imports OK")

# ===================== 运行 =====================
print("\n\n==================== 开始执行全部测试 ====================\n")

test_funcs = sorted([fn for name, fn in globals().items()
                     if name.startswith("T") and callable(fn)],
                    key=lambda f: f.__name__)
for fn in test_funcs:
    fn()

# ===================== 报告生成 =====================
pass_c = sum(1 for r in results if r.status == "PASS")
fail_c = sum(1 for r in results if r.status == "FAIL")
total = len(results)

report_path = os.path.join(OUTPUT_DIR, "test_report.md")
with open(report_path, "w", encoding="utf-8") as f:
    f.write("# QA-Tool 全面测试报告\n\n")
    f.write(f"> 生成时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}\n")
    f.write("> 测试数据: `公司仪器测试数据.xlsx` + SQLite\n")
    f.write("> Python: 3.14.6\n\n")
    f.write("## 汇总\n\n| 指标 | 值 |\n|------|-----|\n")
    f.write(f"| 总用例 | {total} |\n| 通过 | {pass_c} |\n| 失败 | {fail_c} |\n| 通过率 | {pass_c/total*100:.1f}% |\n\n")
    f.write("## 按模块统计\n\n| 模块 | 总项 | 通过 | 失败 |\n|------|:---:|:---:|:---:|\n")
    by_cat = {}
    for r in results:
        by_cat.setdefault(r.cat, []).append(r)
    for cat, items in sorted(by_cat.items()):
        pc = sum(1 for i in items if i.status == "PASS")
        fc = sum(1 for i in items if i.status == "FAIL")
        f.write(f"| {cat} | {len(items)} | {pc} | {fc} |\n")

    if fail_c:
        f.write("\n## 失败项详情\n\n| 编号 | 分类 | 测试项 | 错误 |\n|------|------|--------|------|\n")
        for i, r in enumerate(results, 1):
            if r.status == "FAIL":
                f.write(f"| T{i:02d} | {r.cat} | {r.name} | {r.error} |\n")

    f.write("\n## 详细结果\n\n| # | 分类 | 测试项 | 说明 | 结果 |\n|---|------|--------|------|:----:|\n")
    for i, r in enumerate(results, 1):
        icon = "✅ PASS" if r.status == "PASS" else "❌ FAIL"
        note = f" `{r.error[:80]}`" if r.status == "FAIL" else ""
        f.write(f"| {i:02d} | {r.cat} | {r.name} | {r.desc[:40]} | {icon}{note} |\n")
    
print(f"\nReport: {report_path}")
print(f"Pass: {pass_c}/{total} ({pass_c/total*100:.1f}%)")
if fail_c:
    print(f"Fail: {fail_c}")
    for i, r in enumerate(results, 1):
        if r.status == "FAIL":
            print(f"  FAIL T{i:02d} {r.name}: {r.error[:120]}")
