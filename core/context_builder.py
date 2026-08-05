"""LLM 上下文构建器 — 将分析结果转换为结构化提示"""

from typing import Dict, Any, List
from datetime import datetime


class ContextBuilder:
    MAX_HISTORY = 20

    def __init__(self):
        self.history: List[Dict[str, str]] = []

    def build(self, analyses: Dict[int, dict], file_name: str = "") -> str:
        parts = []
        if file_name:
            parts.append(f"数据文件: {file_name}")

        parts.append(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        parts.append("")

        for idx, analysis in sorted(analyses.items()):
            atype = analysis.get("analysis_type", "未知")
            params = analysis.get("params", {})
            result = analysis.get("result", {})

            parts.append(f"## 分析{idx}: {atype}")
            if params:
                parts.append(f"参数: {', '.join(f'{k}={v}' for k, v in params.items() if k != 'factors')}")

            cap = result.get("capability", {})
            if cap:
                parts.append(f"过程能力: Cp={cap.get('cp','-')}, Cpk={cap.get('cpk','-')}, "
                            f"PPM={cap.get('ppm_total','-')}, 等级={cap.get('grade','-')}")

            pct = result.get("percentages", {})
            if pct:
                parts.append(f"GRR分析: %GRR={pct.get('grr_pct_tv','-')}%, "
                            f"NDC={result.get('ndc','-')}, 判定={result.get('acceptance',{}).get('message','-')}")

            if "p_value" in result:
                sig = "显著" if result.get("is_significant") else "不显著"
                parts.append(f"假设检验: p={result.get('p_value','-')}, 结论={sig}")

            model = result.get("model", {})
            if model:
                parts.append(f"回归模型: R²={model.get('r_squared','-')}, "
                            f"Adj R²={model.get('adj_r_squared','-')}")

            violations = result.get("violations", [])
            if violations:
                parts.append(f"异常点: {len(violations)} 个")

            parts.append("")

        return "\n".join(parts)

    def build_prompt(self, analyses: Dict[int, dict], user_question: str,
                     file_name: str = "") -> str:
        context = self.build(analyses, file_name)

        history_text = ""
        for h in self.history[-6:]:
            history_text += f"用户: {h['user']}\n助手: {h['assistant']}\n\n"

        return (
            "你是一个专业质量分析助手(质量工程师/六西格玛黑带)。"
            "基于以下实际分析数据回答用户问题。如果数据不足，请诚实说明。\n\n"
            f"{context}\n"
            f"{'--- 对话历史 ---\n' + history_text if history_text else ''}"
            f"用户问题: {user_question}"
        )

    def add_to_history(self, user_msg: str, assistant_msg: str):
        self.history.append({"user": user_msg, "assistant": assistant_msg})
        if len(self.history) > self.MAX_HISTORY:
            self.history = self.history[-self.MAX_HISTORY:]

    def clear_history(self):
        self.history.clear()
