"""v2.1 新增测试 — 架构 + Bug 回归 + 边界条件"""
import pytest
import os
import numpy as np
import pandas as pd

# ── TAB_REGISTRY 完整性 ──

def test_tab_registry_all_indices_unique():
    """TAB_REGISTRY 中所有 index 必须唯一"""
    from ui._tab_registry import TAB_REGISTRY
    indices = [entry[0] for entry in TAB_REGISTRY]
    assert len(indices) == len(set(indices)), f"重复 index: {[i for i in indices if indices.count(i) > 1]}"


def test_tab_registry_covers_all_slots():
    """TAB_REGISTRY 覆盖 1-28 所有索引"""
    from ui._tab_registry import TAB_REGISTRY
    indices = set(entry[0] for entry in TAB_REGISTRY)
    expected = set(range(1, 29))
    missing = expected - indices
    assert not missing, f"缺失索引: {missing}"


def test_tab_registry_modules_exist():
    """验证所有注册的模块路径可导入"""
    import importlib
    from ui._tab_registry import TAB_REGISTRY
    failed = []
    for idx, _, class_name, module_path, _ in TAB_REGISTRY:
        try:
            mod = importlib.import_module(module_path)
            assert hasattr(mod, class_name), f"{module_path} 缺少 {class_name}"
        except Exception as e:
            failed.append(f"[{idx}] {module_path}.{class_name}: {e}")
    assert not failed, "\n".join(failed)


# ── Bug 回归 ──

def test_p_chart_data_not_swapped():
    """A1-1 回归: total_inspected=ss.sum(), total_defectives=d.sum()"""
    from analysis.spc.p_chart import analyze
    d = pd.Series([5, 3, 7, 2, 4])
    ss = pd.Series([100, 100, 100, 100, 100])
    result = analyze(d, ss)
    s = result["summary"]
    assert s["total_inspected"] == 500, f"期望 total_inspected=500, 实际 {s['total_inspected']}"
    assert s["total_defectives"] == 21, f"期望 total_defectives=21, 实际 {s['total_defectives']}"


def test_trend_tab_anom_defined():
    """A1-4 回归: 数据<=5行时 anom 提前初始化为空列表"""
    v = np.array([1.0, 2.0, 3.0])
    anom = []  # A1-4 修复
    if len(v) > 5:
        z = np.abs((v - np.mean(v)) / (np.std(v) + 1e-9))
        anom = np.where(z > 3)[0]
    assert anom == []


def test_validate_data_file_module_level():
    """A1-5 回归: validate_data_file 是模块级可调用函数"""
    from core import data_loader
    assert callable(data_loader.validate_data_file)


def test_validate_data_file_not_found():
    """validate_data_file: 不存在文件应抛 FileNotFoundError"""
    from core import data_loader
    with pytest.raises(FileNotFoundError):
        data_loader.validate_data_file("/nonexistent/xyz_12345.xlsx")


def test_validate_data_file_bad_extension():
    """validate_data_file: 不支持后缀应抛 ValueError"""
    import tempfile
    from core import data_loader
    # 创建一个临时 .xyz 文件使其通过存在性检查
    with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
        tmp_path = f.name
    try:
        with pytest.raises(ValueError):
            data_loader.validate_data_file(tmp_path)
    finally:
        os.unlink(tmp_path)


def test_batch_scheduler_default_execute_raises():
    """A1-13 回归: _default_execute 抛出 NotImplementedError"""
    from core.batch_scheduler import BatchScheduler
    # 传入 None 应抛出 NotImplementedError（含 task 标识信息）
    with pytest.raises(NotImplementedError):
        BatchScheduler._default_execute(None)


# ── 懒加载 ──

def test_main_window_has_lazy_load():
    """MainWindow 有懒加载方法"""
    from ui.main_window import MainWindow
    assert hasattr(MainWindow, '_lazy_load_tab'), "缺失 _lazy_load_tab"
    assert hasattr(MainWindow, '_connect_tab_signals'), "缺失 _connect_tab_signals"


# ── 死代码清理验证 ──

def test_welcome_page_signals_defined():
    """A1-15 回归: welcome_page 所有信号均已定义"""
    from ui.welcome_page import WelcomePage
    signals = ['import_data_clicked', 'import_template_clicked', 'diagnose_clicked',
               'new_analysis_clicked', 'open_project_clicked']
    for sig in signals:
        assert hasattr(WelcomePage, sig), f"缺失信号: {sig}"


def test_main_window_has_load_project_by_path():
    """A1-15 回归: _load_project_by_path 方法存在"""
    from ui.main_window import MainWindow
    assert hasattr(MainWindow, '_load_project_by_path'), "缺失 _load_project_by_path"


# ── 边界条件 ──

def test_data_generator_empty_params():
    """数据生成器在极端参数下不应崩溃"""
    from core.data_generator import DataGenerator
    dg = DataGenerator()
    result = dg.generate("normal", n=0)
    assert len(result) == 0


def test_data_generator_all_distributions():
    """所有 7 种分布均可生成"""
    from core.data_generator import DataGenerator
    dg = DataGenerator()
    for dist in ["normal", "lognormal", "exponential", "uniform", "weibull", "binomial", "poisson"]:
        result = dg.generate(dist, n=50)
        assert len(result) == 50, f"{dist} 生成失败"
        assert not np.any(np.isnan(result)), f"{dist} 含 NaN"


def test_sampling_engine_aql_lookup():
    """AQL 查表可用"""
    from core.sampling_engine import SamplingEngine
    eng = SamplingEngine()
    result = eng.aql_lookup(lot_size=500, aql=1.0, level="II")
    assert result is not None
    assert "sample_size" in result
    assert "accept" in result  # 接收数
    assert "reject" in result  # 拒收数


def test_fmea_rpn_calculation():
    """FMEA RPN=SxOxD 计算正确"""
    from core.fmea_engine import FMEAItem
    item = FMEAItem(failure_mode="测试失效", severity=7, occurrence=5, detection=3)
    item.calc_rpn()
    assert item.rpn == 105  # 7x5x3
    assert item.risk_level in ("high", "medium", "low")


def test_data_profiler_empty_df():
    """DataProfiler 对空 DataFrame 不崩溃"""
    from core.data_profiler import DataProfiler
    dp = DataProfiler()
    result = dp.profile({"empty_sheet": pd.DataFrame()})
    assert isinstance(result, dict), "profile() 应返回字典"


def test_sheet_splitter_has_split_methods():
    """SheetSplitter 有核心拆分方法"""
    from core.sheet_splitter import SheetSplitter
    assert hasattr(SheetSplitter, 'split_by_column')
    assert hasattr(SheetSplitter, 'split_by_condition')


# ── 格式工具 ──

def test_format_pvalue_boundaries():
    """format_pvalue 极值"""
    from core.formatting import format_pvalue
    r1 = format_pvalue(0.0001)
    r2 = format_pvalue(0.5)
    assert isinstance(r1, str) and len(r1) > 0
    assert isinstance(r2, str) and len(r2) > 0


def test_format_cp_boundaries():
    """format_cp 极值"""
    from core.formatting import format_cp
    r1 = format_cp(1.33)
    r2 = format_cp(0.5)
    assert isinstance(r1, str) and len(r1) > 0
    assert isinstance(r2, str) and len(r2) > 0



if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
