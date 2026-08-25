"""代码审查修复回归测试 — 每项修复对应一个测试类

覆盖: P0 统计正确性 bug (1-5) + P1 工程问题 (6-12)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd


# ── P0-1: XBar-R 的 Xbar 图 Nelson 规则 σ 必须除以 √n ────────────────
class TestXbarRNelsonSigma:
    def test_xbar_r_detects_violation_like_xbar_s(self):
        """回归: 子组均值超出 3σ/√n 时 XBar-R 与 XBar-S 判异一致"""
        from analysis.spc import xbar_r, xbar_s

        np.random.seed(7)
        n_sub, sg = 8, 5
        data = []
        for k in range(n_sub):
            base = 10.0 + (1.35 if k == 4 else 0.0)
            data.extend(base + np.array([-1.0, -0.5, 0.0, 0.5, 1.0]))
        series = pd.Series(data)

        r = xbar_r.analyze(series, subgroup_size=sg)
        s = xbar_s.analyze(series, subgroup_size=sg)
        rv = r["xbar_chart"]["violations"]
        sv = s["xbar_chart"]["violations"]

        assert rv, "XBar-R 应检出超出 3σ/√n 的子组(修复前 sigma_hat 未除 √n 会漏报)"
        assert sv, "XBar-S 应检出超出 3σ/√n 的子组"
        r_pts = {x["point"] for x in rv}
        s_pts = {x["point"] for x in sv}
        assert r_pts == s_pts, f"判异不一致: XBar-R={r_pts} XBar-S={s_pts}"

    def test_xbar_r_no_false_positive_near_limit(self):
        """回归: 子组均值在 3σ/√n 以内时不应违规(σ 口径过大导致过度宽容/不报警)"""
        from analysis.spc import xbar_r

        # 偏移 2.8σ_xbar (小于 3σ_xbar), 不应触发规则1
        sg = 5
        data = []
        for k in range(8):
            base = 10.0 + (0.8 if k == 4 else 0.0)  # 0.8 < 3/√5 ≈ 1.342 (σ≈1 时)
            data.extend(base + np.array([-1.0, -0.5, 0.0, 0.5, 1.0]))
        r = xbar_r.analyze(pd.Series(data), subgroup_size=sg)
        r1 = [x for x in r["xbar_chart"]["violations"] if x["rule"] == 1]
        assert r1 == [], f"2.8σ_xbar 偏移不应触发规则1: {r1}"


# ── P0-2: 非正态能力 Box-Cox/Johnson 规格限变换 ─────────────────────
class TestNonNormalCapTransform:
    @staticmethod
    def _manual_boxcox(value, lam, shift):
        x = value + shift
        return (x ** lam - 1) / lam if lam != 0 else np.log(x)

    def test_boxcox_spec_limit_with_shift(self):
        """回归: 含非正数数据时规格限必须加 shift 再变换"""
        from analysis.capability import non_normal_cap

        np.random.seed(11)
        data = pd.Series(np.random.lognormal(0, 0.4, 200) - 5)
        assert (data <= 0).any(), "测试数据需含非正数以触发 shift"
        usl, lsl = 6.0, -3.0
        r = non_normal_cap.analyze(data, usl=usl, lsl=lsl, method="box_cox")
        lam = r["transform_param"]
        shift = abs(data.min()) + 0.001
        usl_t = self._manual_boxcox(usl, lam, shift)
        lsl_t = self._manual_boxcox(lsl, lam, shift)
        std_t = r["summary"]["transformed_std"]
        exp_pp = (usl_t - lsl_t) / (6 * std_t)
        assert abs(r["capability"]["pp"] - exp_pp) < 0.01, (
            f"规格限变换未加 shift: pp={r['capability']['pp']} 期望={exp_pp}")

    def test_boxcox_no_shift_positive_data(self):
        """回归: 全正数据 shift=0, 规格限直接变换"""
        from analysis.capability import non_normal_cap

        np.random.seed(12)
        data = pd.Series(np.random.normal(10.0, 2.0, 300))
        usl, lsl = 16.0, 4.0
        r = non_normal_cap.analyze(data, usl=usl, lsl=lsl, method="box_cox")
        lam = r["transform_param"]
        usl_t = self._manual_boxcox(usl, lam, 0.0)
        lsl_t = self._manual_boxcox(lsl, lam, 0.0)
        std_t = r["summary"]["transformed_std"]
        exp_pp = (usl_t - lsl_t) / (6 * std_t)
        assert abs(r["capability"]["pp"] - exp_pp) < 0.01

    def test_johnson_spec_limit_scaled(self):
        """回归: Johnson(z-score) 规格限按同一标准化参数变换"""
        from analysis.capability import non_normal_cap

        np.random.seed(13)
        data = pd.Series(np.random.lognormal(0.5, 0.6, 300))
        usl, lsl = 8.0, 0.5
        r = non_normal_cap.analyze(data, usl=usl, lsl=lsl, method="johnson")
        mean, std = data.mean(), data.std(ddof=1)
        usl_t = (usl - mean) / std
        lsl_t = (lsl - mean) / std
        exp_pp = (usl_t - lsl_t) / 6.0  # z-score 后 std_t == 1
        assert abs(r["capability"]["pp"] - exp_pp) < 0.01

    def test_single_sided_spec_limit(self):
        """回归: 仅单侧规格限时计算单边 pp/ppk"""
        from analysis.capability import non_normal_cap

        np.random.seed(14)
        data = pd.Series(np.random.lognormal(0, 0.3, 200) + 10)
        r = non_normal_cap.analyze(data, usl=22.0, lsl=None, method="box_cox")
        cap = r["capability"]
        assert "ppu" in cap and "usl" in cap and "lsl" not in cap
        assert cap["ppk"] == cap["pp"]
        r2 = non_normal_cap.analyze(data, usl=None, lsl=5.0, method="box_cox")
        cap2 = r2["capability"]
        assert "ppl" in cap2 and "lsl" in cap2 and "usl" not in cap2
        assert cap2["ppk"] == cap2["pp"]


# ── P0-3: two_sample 的 Levene 检验死代码 → 三态 equal_var ────────────
class TestTwoSampleEqualVar:
    def test_auto_pooled_when_variances_equal(self):
        """回归: 方差齐时 None 自动选择 pooled (equal_variance_assumed=True)"""
        from analysis.hypothesis.t_tests import two_sample

        np.random.seed(21)
        g1 = pd.Series(np.random.normal(10, 1.0, 60))
        g2 = pd.Series(np.random.normal(10.5, 1.0, 60))
        r = two_sample(g1, g2, equal_var=None)
        assert r["equal_variance_assumed"] is True
        assert r["levene_p_value"] > 0.05

    def test_auto_welch_when_variances_unequal(self):
        """回归: 方差不齐时 None 自动选择 Welch (equal_variance_assumed=False)"""
        from analysis.hypothesis.t_tests import two_sample

        np.random.seed(22)
        g1 = pd.Series(np.random.normal(10, 1.0, 60))
        g2 = pd.Series(np.random.normal(10, 8.0, 60))
        r = two_sample(g1, g2, equal_var=None)
        assert r["equal_variance_assumed"] is False
        assert r["levene_p_value"] < 0.05

    def test_explicit_value_respected(self):
        """回归: 显式 True/False 尊重用户选择, 不被 Levene 覆盖"""
        from analysis.hypothesis.t_tests import two_sample

        np.random.seed(23)
        g1 = pd.Series(np.random.normal(10, 1.0, 60))
        g2 = pd.Series(np.random.normal(10, 8.0, 60))
        r = two_sample(g1, g2, equal_var=True)
        assert r["equal_variance_assumed"] is True
        r2 = two_sample(g1, g2, equal_var=False)
        assert r2["equal_variance_assumed"] is False

    def test_default_auto(self):
        """回归: 不传 equal_var 时默认自动选择"""
        from analysis.hypothesis.t_tests import two_sample

        np.random.seed(24)
        g1 = pd.Series(np.random.normal(10, 1.0, 60))
        g2 = pd.Series(np.random.normal(10.5, 1.0, 60))
        r = two_sample(g1, g2)
        assert "equal_variance_assumed" in r

# ── P0-4: Weibull 2P-MLE 必须使用含删失的完整似然 ───────────────────
class TestWeibullCensoredFit:
    def test_2p_mle_loglik_improves_with_censored(self):
        """回归: 有右删失时 2P MLE 应最大化完整似然(旧实现只拟合失效点)"""
        from scipy import stats as sp_stats
        from analysis.reliability.weibull import WeibullAnalyzer

        rng = np.random.default_rng(42)
        failures = rng.weibull(1.5, 20) * 100.0
        censor_limit = 50.0
        raw_censor = rng.weibull(1.5, 20) * 100.0
        censored = (raw_censor <= censor_limit).astype(float)  # 1=失效 0=删失
        censored_times = np.minimum(raw_censor, censor_limit)

        all_times = np.concatenate([failures, censored_times])
        cen_all = np.concatenate([np.ones(len(failures)), censored])

        out = WeibullAnalyzer().analyze(all_times.tolist(), censored=cen_all.tolist())
        assert out["error"] is None
        res = out["result"]
        assert res.method == "2P-MLE"

        # 旧行为: 仅失效数据的 scipy MLE 参数
        beta_old, _, eta_old = sp_stats.weibull_min.fit(failures, floc=0)
        ll_old = WeibullAnalyzer._weibull_loglik(
            float(beta_old), float(eta_old), 0.0,
            np.asarray(all_times, float), np.asarray(cen_all, int))

        assert res.loglik >= ll_old - 1e-6, "含删失 MLE 的 loglik 应不低于仅失效拟合"
        assert abs(res.beta - float(beta_old)) > 1e-4, "删失数据应改变拟合参数"
        assert res.beta > 0 and res.eta > 0

    def test_2p_mle_no_censoring_matches_scipy(self):
        """回归: 无删失时含删失 MLE 与 scipy 直接拟合结果一致(数值容差内)"""
        from scipy import stats as sp_stats
        from analysis.reliability.weibull import WeibullAnalyzer

        rng = np.random.default_rng(7)
        times = rng.weibull(2.0, 50) * 80.0
        out = WeibullAnalyzer().analyze(times.tolist())
        res = out["result"]

        beta_expected, _, eta_expected = sp_stats.weibull_min.fit(times, floc=0)
        assert abs(res.beta - float(beta_expected)) < 0.05
        assert abs(res.eta - float(eta_expected)) < 0.05
# ── P1-7: batch_scheduler.py 工作线程泄漏 ─────────────
class TestBatchWorkerCleanup:
    def test_workers_list_empties_after_tasks_finish(self, tmp_path, monkeypatch):
        """回归: 任务完成后 _workers 应清空(修复前只增不减)"""
        import time
        from PySide6.QtCore import QCoreApplication
        from core import batch_scheduler as bs_mod

        app = QCoreApplication.instance() or QCoreApplication([])
        monkeypatch.setattr(bs_mod.BatchScheduler, "TASKS_FILE", str(tmp_path / "tasks.json"))
        ran = []
        sched = bs_mod.BatchScheduler(execute_fn=lambda task: ran.append(task.id))
        t1 = bs_mod.BatchTask(name="t1")
        t2 = bs_mod.BatchTask(name="t2")
        sched.add_task(t1)
        sched.add_task(t2)
        sched.run_now(t1.id)
        sched.run_now(t2.id)
        assert len(sched._workers) == 2
        deadline = time.monotonic() + 10
        while sched._workers and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.05)
        assert sorted(ran) == sorted([t1.id, t2.id]), "两个任务都应执行"
        assert sched._workers == [], f"完成后 _workers 应清空, 剩余 {len(sched._workers)}"

    def test_on_task_finished_removes_only_matching_worker(self, tmp_path, monkeypatch):
        """回归: _on_task_finished 只移除对应 id 的 worker"""
        from core import batch_scheduler as bs_mod

        monkeypatch.setattr(bs_mod.BatchScheduler, "TASKS_FILE", str(tmp_path / "tasks.json"))
        sched = bs_mod.BatchScheduler(execute_fn=lambda t: None)
        t = bs_mod.BatchTask(name="t1", id="abc")
        sched.tasks["abc"] = t
        sched._workers.append(bs_mod._WorkerThread(t, lambda x: None))
        sched._on_task_finished("abc", True, "")
        assert sched._workers == []

        w2 = bs_mod._WorkerThread(bs_mod.BatchTask(name="t2", id="def"), lambda x: None)
        sched._workers.append(w2)
        sched._on_task_finished("other", True, "")
        assert len(sched._workers) == 1, "不匹配的 worker 不应被移除"

    def test_in_flight_guard_skips_duplicate(self, tmp_path, monkeypatch):
        """C06: 任务已在执行时 _execute_task 跳过重复启动"""
        from core import batch_scheduler as bs_mod

        monkeypatch.setattr(bs_mod.BatchScheduler, "TASKS_FILE", str(tmp_path / "tasks.json"))
        ran = []
        sched = bs_mod.BatchScheduler(execute_fn=lambda task: ran.append(task.id))
        t = bs_mod.BatchTask(name="t1")
        sched.add_task(t)
        sched._running.add(t.id)
        sched._execute_task(t)
        assert ran == [], "in-flight 任务不应重复启动"

    def test_on_task_finished_clears_running(self, tmp_path, monkeypatch):
        """C06: 任务结束后 _running 中移除对应 id"""
        from core import batch_scheduler as bs_mod

        monkeypatch.setattr(bs_mod.BatchScheduler, "TASKS_FILE", str(tmp_path / "tasks.json"))
        sched = bs_mod.BatchScheduler(execute_fn=lambda t: None)
        t = bs_mod.BatchTask(name="t1", id="abc")
        sched.tasks["abc"] = t
        sched._running.add("abc")
        sched._on_task_finished("abc", True, "")
        assert "abc" not in sched._running

    def test_daily_window_scales_with_interval(self, tmp_path, monkeypatch):
        """W94: daily 窗口 = max(30, 2×轮询周期), 60s 轮询不因抖动错过目标"""
        from datetime import datetime
        from core import batch_scheduler as bs_mod

        monkeypatch.setattr(bs_mod.BatchScheduler, "TASKS_FILE", str(tmp_path / "tasks.json"))
        sched = bs_mod.BatchScheduler(execute_fn=lambda t: None)
        t = bs_mod.BatchTask(name="t1", id="d1", schedule="daily@10:00")
        # 60s 轮询: 窗口放大到 120s (2×interval), 差 5s 应触发
        sched._poll_interval_ms = 60000
        assert sched._should_run(t, datetime(2026, 8, 20, 10, 0, 5)) is True
        # 差 150s > 窗口 120s → 不触发
        assert sched._should_run(t, datetime(2026, 8, 20, 10, 2, 30)) is False
        # 默认 30s 轮询: 窗口放宽到 60s (2×interval, 原 30s 窗口防抖动)
        sched._poll_interval_ms = 30000
        assert sched._should_run(t, datetime(2026, 8, 20, 10, 0, 29)) is True
        assert sched._should_run(t, datetime(2026, 8, 20, 10, 1, 1)) is False

    def test_kstest_skipped_for_constant_large_data(self):
        """W92: >5000 行近常数数据不跑 kstest (scale≈0 退化), p_value=None"""
        import pandas as pd
        from core.data_validator import DataValidator
        dv = DataValidator()
        df = pd.DataFrame({"m": [5.0] * 6000})
        res = dv.validate(df, ["m"])
        s = res["summary"]["m"]
        assert s["normality_p_value"] is None
        assert s["is_normal"] is False
# ── P1-8: waterfall 图非默认索引错位 ──────────────────
class TestWaterfallIndex:
    def test_waterfall_non_default_index(self):
        """回归: 非默认 DataFrame 索引不应 IndexError 且标签顺序正确"""
        from analysis.charts.chart_generator import _build_waterfall
        import matplotlib
        matplotlib.use("Agg")
        df = pd.DataFrame({"类别": ["A", "B", "C", "D", "E"],
                           "数值": [10.0, -3.0, 5.0, 8.0, 2.0]})
        df.index = [100, 101, 102, 103, 104]  # 非默认索引
        fig = _build_waterfall({"df": df, "columns": ["类别", "数值"]}, {})
        ax = fig.axes[0]
        labels = [t.get_text() for t in ax.get_xticklabels()]
        assert labels == ["A", "B", "C", "D", "E"], f"标签错位: {labels}"
        import matplotlib.pyplot as plt
        plt.close(fig)

    def test_waterfall_skips_nan_non_default_index(self):
        """回归: 含 NaN 行且非默认索引时不错位"""
        from analysis.charts.chart_generator import _build_waterfall
        import matplotlib
        matplotlib.use("Agg")
        df = pd.DataFrame({"类别": ["A", "B", "C", "D", "E", "F"],
                           "数值": [10.0, float("nan"), -3.0, 5.0, float("nan"), 8.0]})
        df.index = [50, 51, 52, 53, 54, 55]
        fig = _build_waterfall({"df": df, "columns": ["类别", "数值"]}, {})
        ax = fig.axes[0]
        labels = [t.get_text() for t in ax.get_xticklabels()]
        assert labels == ["A", "C", "D", "F"], f"NaN 行未正确跳过: {labels}"
        import matplotlib.pyplot as plt
        plt.close(fig)
# ── P1-9: plant_compare 多规格列归属 ─────────────────────
class TestPlantCompareSpecs:
    def _write_xlsx(self, tmp_path, df, name="p.xlsx"):
        p = tmp_path / name
        df.to_excel(str(p), index=False)
        return str(p)

    def test_single_spec_pair_merged(self, tmp_path):
        from core.plant_compare import summarize_plant
        df = pd.DataFrame({
            "测量值": [10.0, 11.0, 9.0, 10.5, 10.2, 9.8, 10.3, 10.1, 10.4, 9.9],
            "USL": [12.0] * 10,
            "LSL": [8.0] * 10,
        })
        out = summarize_plant(self._write_xlsx(tmp_path, df), column="测量值")
        assert out["error"] is None
        assert out["usl"] == 12.0 and out["lsl"] == 8.0
        assert out["cpk"] is not None
        assert out.get("spec_warning") is None

    def test_multiple_spec_pairs_skipped(self, tmp_path):
        from core.plant_compare import summarize_plant
        df = pd.DataFrame({
            "测量值": [10.0, 11.0, 9.0, 10.5, 10.2, 9.8, 10.3, 10.1, 10.4, 9.9],
            "长度USL": [12.0] * 10, "长度LSL": [8.0] * 10,
            "宽度USL": [15.0] * 10, "宽度LSL": [5.0] * 10,
        })
        out = summarize_plant(self._write_xlsx(tmp_path, df), column="测量值")
        assert out["error"] is None
        assert out["usl"] is None and out["lsl"] is None
        assert out["cpk"] is None
        assert "spec_warning" in out
# ── P1-10: 合规模板占位符替换 ─────────────────────
class TestCompliancePlaceholders:
    def test_fill_placeholders_replaces_all(self):
        from output.compliance_report import _fill_placeholders
        from config.settings import APP_VERSION
        text = "报告 {{file_name}} / {{timestamp}} / {{version}}"
        out = _fill_placeholders(text, "Q1.xlsx")
        assert "{{" not in out and "}}" not in out
        assert "Q1.xlsx" in out
        assert APP_VERSION in out

    def test_fill_placeholders_empty_text(self):
        from output.compliance_report import _fill_placeholders
        assert _fill_placeholders(None) is None
        assert _fill_placeholders("") == ""

    def test_generate_title_no_leftover_placeholders(self, tmp_path, monkeypatch):
        import json
        import docx
        from output import compliance_report
        tdir = tmp_path / "templates"
        tdir.mkdir()
        (tdir / "t.json").write_text(
            json.dumps({"name": "合规报告 {{file_name}}", "format": "docx",
                        "standard": "TEST", "sections": []}, ensure_ascii=False),
            encoding="utf-8")
        monkeypatch.setattr(compliance_report, "TEMPLATES_DIR", str(tdir))
        out = tmp_path / "r.docx"
        ret = compliance_report.ComplianceReportGenerator.generate("t", [], str(out), file_name="Q1.xlsx")
        assert ret == str(out) and out.exists() and out.stat().st_size > 0
        texts = [p.text for p in docx.Document(str(out)).paragraphs]
        assert any("Q1.xlsx" in t and "{{" not in t for t in texts), texts[:5]


# ── P1-11: WordReport 图表参数统一收 bytes (兼容 BytesIO) ───────────
class TestWordReportChartTypes:
    def _make_png_bytes(self):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from output.chart_engine import figure_to_bytes
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        buf = figure_to_bytes(fig)
        plt.close(fig)
        return buf

    def test_word_report_accepts_bytes(self, tmp_path):
        from output.word_report import WordReport
        buf = self._make_png_bytes()
        analyses = [{"analysis_type": "spc", "params": {},
                     "result": {"chart_type": "XBar-R", "summary": {}}}]
        out = WordReport().generate(analyses, str(tmp_path / "b.docx"),
                                    charts={"spc": buf.getvalue()})
        assert os.path.exists(out) and os.path.getsize(out) > 0

    def test_word_report_accepts_bytesio_backward_compat(self, tmp_path):
        from output.word_report import WordReport
        buf = self._make_png_bytes()
        analyses = [{"analysis_type": "spc", "params": {},
                     "result": {"chart_type": "XBar-R", "summary": {}}}]
        out = WordReport().generate(analyses, str(tmp_path / "io.docx"),
                                    charts={"spc": buf})
        assert os.path.exists(out) and os.path.getsize(out) > 0

    def test_same_bytes_feed_pdf_report(self, tmp_path):
        from output.pdf_report import generate_pdf_report
        buf = self._make_png_bytes()
        analyses = [{"analysis_type": "spc", "params": {},
                     "result": {"chart_type": "XBar-R", "summary": {}}}]
        out = generate_pdf_report(analyses, str(tmp_path / "r.pdf"),
                                  charts={"spc": buf.getvalue()})
        assert os.path.exists(out) and os.path.getsize(out) > 0


# ── P1-12: 包级导出补全 冒烟测试 ──
class TestExportsSmoke:

    def test_hypothesis_exports_nonparametric(self):
        from analysis.hypothesis import nonparametric
        assert hasattr(nonparametric, "mann_whitney")
        assert hasattr(nonparametric, "kruskal_wallis")

    def test_ie_exports_line_balance_oee_vsm(self):
        from analysis.ie import LineBalanceEngine, OEEEngine, VSMEngine
        assert hasattr(LineBalanceEngine, "analyze")
        assert hasattr(OEEEngine, "analyze")
        assert hasattr(VSMEngine, "analyze")

    def test_reliability_exports_alt_and_result_types(self):
        from dataclasses import fields
        from analysis.reliability import (ALTEngine, WeibullResult,
                                          MTBFResult)
        assert hasattr(ALTEngine, "arrhenius_life")
        assert hasattr(ALTEngine, "inverse_power_law")
        assert "beta" in {f.name for f in fields(WeibullResult)}
        assert "mtbf" in {f.name for f in fields(MTBFResult)}