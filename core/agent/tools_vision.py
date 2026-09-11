"""QAM Harness Vision 工具（v3.8.0 P3）— 视频时间研究 / 工作抽样。

设计:
  - 复用 `analysis/vision` 真引擎（与界面同源），不重写统计逻辑；
  - 无 Qt、无 cv2 硬依赖：模块可导入，缺依赖时工具返回安装指引；
  - 工具在 AgentWorker 线程内同步执行，默认限制采样帧率与分析时长，
    避免长视频把对话卡住（上限 30 分钟素材）。
"""
from __future__ import annotations

from pathlib import Path

from core.agent.tools import AgentContext, ToolRegistry, ToolResult

MAX_DURATION_S = 1800.0
DEFAULT_DURATION_S = 600.0


def _as_bool(value, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in ("0", "false", "no", "off", "否")


def _as_roi(value):
    if value in (None, "", [], ()):
        return None
    if isinstance(value, (list, tuple)) and len(value) == 4:
        return tuple(int(float(v)) for v in value)
    parts = [p.strip() for p in str(value).replace("，", ",").split(",")]
    if len(parts) != 4:
        raise ValueError("roi 需为 x,y,w,h 四个整数")
    return tuple(int(float(p)) for p in parts)


def _bounds(sample_fps, max_seconds):
    fps = min(30.0, max(0.5, float(sample_fps or 5.0)))
    seconds = min(MAX_DURATION_S, max(1.0, float(max_seconds or DEFAULT_DURATION_S)))
    return fps, seconds


def _build_config(args: dict):
    from analysis.vision.session import VisionConfig

    fps, seconds = _bounds(args.get("sample_fps", 5.0),
                           args.get("max_seconds", DEFAULT_DURATION_S))
    return VisionConfig(
        sample_fps=fps, width=int(args.get("width", 640) or 640),
        roi=_as_roi(args.get("roi")),
        max_seconds=seconds,
        process_id=str(args.get("process_id") or "视频工序"),
        operator=str(args.get("operator") or "视频观测"),
        prefer_mediapipe=_as_bool(args.get("prefer_mediapipe"), True),
    )


def _run(args: dict):
    from analysis.vision.session import run_vision_session

    raw = args.get("path")
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        raise ValueError("path 不能为空（本地视频文件路径，或 synthetic 演示源）")
    if isinstance(raw, str):
        source = raw.strip()
        if source not in ("synthetic", "demo") and not Path(source).exists():
            raise FileNotFoundError(f"视频文件不存在: {source}")
    else:
        source = raw                          # 允许直接传 FrameSource（测试/嵌入）
    return run_vision_session(source, _build_config(args))


def _describe(result) -> str:
    ratios = " · ".join(f"{k} {v:.1f}%" for k, v in
                        sorted(result.ratios_labeled.items(),
                               key=lambda kv: kv[1], reverse=True))
    lines = [
        f"视频分析完成: 时长 {result.duration_s:.1f}s，处理 {result.frames} 帧"
        f"（处理速度 {result.processed_fps:.1f} FPS，单帧均值 "
        f"{result.latency.get('avg_ms', 0):.1f}ms / P95 "
        f"{result.latency.get('p95_ms', 0):.1f}ms）",
        f"后端: {result.backend}" + ("（骨架关键点）" if result.model_ready
                                     else "（运动特征降级）"),
        f"状态占比: {ratios or '无有效状态段'}",
        f"作业周期: {len(result.cycles)} 个"
        + (f"（均值 {_mean_cycle(result):.1f}s）" if result.cycles else ""),
    ]
    if result.truncated:
        lines.append("提示: 已达分析时长上限，仅统计前段素材")
    for warning in result.warnings[:2]:
        lines.append(f"提示: {warning}")
    return "\n".join(lines)


def _mean_cycle(result) -> float:
    if not result.cycles:
        return 0.0
    return sum(c.duration_s for c in result.cycles) / len(result.cycles)


def register_vision_tools(reg: ToolRegistry,
                          ctx: AgentContext | None = None) -> ToolRegistry:
    """把 Vision 工具注册进注册表（由 build_default_registry 调用）。"""

    @reg.tool("vision_status", "Vision 能力状态",
              "检测 Vision 依赖与姿态模型是否就绪：OpenCV / MediaPipe / "
              "pose_landmarker_lite.task 模型路径与当前后端（骨架或运动特征）",
              category="视觉", returns="available/cv2/mediapipe/pose_model/backend")
    def _vision_status(context: AgentContext):
        from analysis.vision import backend_info

        info = backend_info()
        if not info["available"]:
            return ToolResult("vision_status", ok=False, data=info,
                              error=f"Vision 不可用：未安装 OpenCV。安装: "
                                    f"{info['install_hint']}")
        model = "已就绪" if info["pose_model"] else "未下载（当前运动特征降级）"
        text = (f"Vision 可用 · 后端: {info['backend']}\n"
                f"OpenCV: {'✓' if info['cv2'] else '✗'} · "
                f"MediaPipe: {'✓' if info['mediapipe'] else '✗'} · "
                f"姿态模型: {model}\n模型路径: {info['pose_model_path'] or '—'}")
        return ToolResult("vision_status", data=info, text=text)

    @reg.tool("vision_analyze_video", "视频动作分析",
              "分析本地视频或摄像头录像: 识别工作/空闲/走动/搬运/离岗状态占比与"
              "作业周期。支持 synthetic 演示源；默认 5 FPS 采样、最长 10 分钟",
              {"path": "视频文件路径（或 synthetic 演示源）",
               "sample_fps": "采样帧率(默认5, 上限30)",
               "max_seconds": "最长分析时长秒(默认600, 上限1800)",
               "process_id": "工序名(可选)", "operator": "作业员(可选)",
               "roi": "分析区域 x,y,w,h(可选)",
               "prefer_mediapipe": "是否优先骨架识别(默认 true)"},
              category="视觉", returns="backend/ratios/cycles/latency/warnings")
    def _analyze(context: AgentContext, path: str = "", sample_fps: float = 5.0,
                 max_seconds: float = DEFAULT_DURATION_S, process_id: str = "",
                 operator: str = "", roi=None, prefer_mediapipe=True):
        result = _run({"path": path, "sample_fps": sample_fps,
                       "max_seconds": max_seconds, "process_id": process_id,
                       "operator": operator, "roi": roi,
                       "prefer_mediapipe": prefer_mediapipe})
        data = result.to_dict()
        data["mean_cycle_s"] = round(_mean_cycle(result), 3)
        return ToolResult("vision_analyze_video", data=data, text=_describe(result))

    @reg.tool("vision_time_study", "视频标准工时",
              "从视频作业周期自动计算标准工时: 平均时间 → 正常时间 → 标准工时"
              "（评定系数/宽放率/节拍可调），与工时研究 Tab 同引擎",
              {"path": "视频文件路径", "sample_fps": "采样帧率(默认5)",
               "max_seconds": "最长分析秒数(默认600)",
               "rating": "评定系数(默认1.0)", "allowance_pct": "宽放率%(默认12)",
               "takt_time": "节拍秒(可选)", "process_id": "工序名(可选)",
               "operator": "作业员(可选)", "prefer_mediapipe": "优先骨架(默认true)"},
              category="视觉", returns="cycles/avg_time/normal_time/standard_time")
    def _vision_time_study(context: AgentContext, path: str = "",
                           sample_fps: float = 5.0,
                           max_seconds: float = DEFAULT_DURATION_S,
                           rating: float = 1.0, allowance_pct: float = 12.0,
                           takt_time=None, process_id: str = "",
                           operator: str = "", prefer_mediapipe=True):
        from analysis.ie.time_study import TimeStudyEngine

        result = _run({"path": path, "sample_fps": sample_fps,
                       "max_seconds": max_seconds, "process_id": process_id,
                       "operator": operator,
                       "prefer_mediapipe": prefer_mediapipe})
        observations = result.to_time_observations()
        if not observations:
            return ToolResult("vision_time_study", ok=False,
                              data=result.to_dict(),
                              error="未识别到作业周期：可提高 sample_fps、"
                                    "提供姿态模型，或用 roi 聚焦作业区域后重试")
        takt = float(takt_time) if takt_time not in (None, "", 0) else None
        analysis = TimeStudyEngine.analyze(
            observations, rating=float(rating or 1.0),
            allowance_pct=float(allowance_pct or 0.0), takt_time=takt)
        row = analysis["results"][0]
        text = (f"视频标准工时（{row['cycles']} 个周期，后端 {result.backend}）: "
                f"平均 {row['avg_time']:.2f}s → 正常 {row['normal_time']:.2f}s "
                f"→ 标准 {row['standard_time']:.2f}s"
                f"（评定 {row['rating']}，宽放 {row['allowance_pct']}%）")
        if takt:
            cap = row["capability"]
            text += (f"\n节拍 {takt:.1f}s: "
                     f"{'可满足' if cap.get('can_meet_takt') else '不满足'}"
                     f"（余量 {cap.get('margin', 0):.1f}s）")
        return ToolResult("vision_time_study",
                          data={"time_study": analysis,
                                "vision": result.to_dict()}, text=text)

    @reg.tool("vision_work_sampling", "视频工作抽样",
              "把视频动作状态段转成工作抽样: 各状态占比 + 置信区间 + 工时利用率，"
              "与工作抽样 Tab 同引擎（工作/空闲/走动/搬运/离岗）",
              {"path": "视频文件路径", "sample_fps": "采样帧率(默认5)",
               "max_seconds": "最长分析秒数(默认600)",
               "confidence": "置信水平(默认0.95)",
               "per_second": "每秒抽样点数(默认1)",
               "prefer_mediapipe": "优先骨架(默认true)"},
              category="视觉", returns="ratios/confidence_intervals/utilization")
    def _vision_work_sampling(context: AgentContext, path: str = "",
                              sample_fps: float = 5.0,
                              max_seconds: float = DEFAULT_DURATION_S,
                              confidence: float = 0.95, per_second: float = 1.0,
                              prefer_mediapipe=True):
        from analysis.ie.work_sampling import WorkSamplingEngine
        from analysis.vision.action import VISION_STATUSES

        result = _run({"path": path, "sample_fps": sample_fps,
                       "max_seconds": max_seconds,
                       "prefer_mediapipe": prefer_mediapipe})
        labels = result.to_work_sampling_labels(per_second=float(per_second or 1.0))
        if not labels:
            return ToolResult("vision_work_sampling", ok=False,
                              error="视频未产生有效动作状态段")
        ratios = WorkSamplingEngine.calculate_ratios(labels, statuses=VISION_STATUSES)
        intervals = WorkSamplingEngine.confidence_intervals(
            ratios, confidence=float(confidence or 0.95))
        utilization = WorkSamplingEngine.calculate_utilization(ratios)
        parts = []
        for key, info in ratios["ratios"].items():
            ci = intervals.get(key, {})
            parts.append(f"{info['label']} {info['pct']:.1f}%"
                         f"（CI {ci.get('ci_low_pct', 0):.1f}~"
                         f"{ci.get('ci_high_pct', 0):.1f}%）")
        text = (f"视频工作抽样: 样本 {ratios['_total']} 点\n"
                + " · ".join(parts)
                + f"\n有效工时利用率: {utilization['productive_pct']:.1f}%"
                  f"（含搬运；走动/等待/离岗不计）")
        return ToolResult("vision_work_sampling",
                          data={"vision": result.to_dict(), "ratios": ratios,
                                "confidence_intervals": intervals,
                                "utilization": utilization}, text=text)

    return reg
