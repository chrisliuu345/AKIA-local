"""
会话管理器 — 保存/恢复分析状态、历史记录管理
"""

import json
import os
from datetime import datetime
from typing import Any


class SessionManager:
    """分析会话持久化管理"""

    def __init__(self, default_dir: str = ""):
        self.sessions_dir = default_dir or os.path.join(os.path.expanduser("~"), ".qa_tool_sessions")
        self.current_session: dict[str, Any] = {}
        self.history: list[dict[str, Any]] = []
        os.makedirs(self.sessions_dir, exist_ok=True)

    def create_session(self, name: str = "", file_path: str = "") -> str:
        # 会话 ID 精确到秒；同一秒内连续创建会撞 ID 导致 save() 互相覆盖，
        # 因此与磁盘上已有文件去重（首个仍保持 YYYYmmdd_HHMMSS 格式）
        base_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_id = base_id
        suffix = 1
        while os.path.exists(os.path.join(self.sessions_dir, f"session_{session_id}.json")):
            suffix += 1
            session_id = f"{base_id}_{suffix}"
        self.current_session = {
            "session_id": session_id,
            "name": name or f"分析会话_{session_id}",
            "created_at": datetime.now().isoformat(),
            "file_path": file_path,
            "file_name": os.path.basename(file_path) if file_path else "",
            "analyses": [],
            "config": {},
        }
        return session_id

    def add_analysis(self, analysis_type: str, params: dict[str, Any], result: dict[str, Any]) -> None:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "analysis_type": analysis_type,
            "params": params,
            "result": result,
        }
        if self.current_session:
            self.current_session.setdefault("analyses", []).append(entry)
        self.history.append(entry)

    def set_analyses(self, analyses: dict[int, dict[str, Any]]) -> None:
        """整体写入内存分析结果快照 (键为 Tab 索引, JSON 序列化为字符串键)"""
        if self.current_session:
            self.current_session["analysis_snapshot"] = {str(k): v for k, v in analyses.items()}

    def get_analyses(self) -> dict[int, dict[str, Any]]:
        """读取分析结果快照并还原 int 键"""
        snap = self.current_session.get("analysis_snapshot", {}) if self.current_session else {}
        return {int(k): v for k, v in snap.items()}

    def save(self, file_path: str | None = None) -> str:
        if not file_path:
            sid = self.current_session.get("session_id", datetime.now().strftime("%Y%m%d_%H%M%S"))
            file_path = os.path.join(self.sessions_dir, f"session_{sid}.json")
        self.current_session["saved_at"] = datetime.now().isoformat()
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.current_session, f, indent=2, ensure_ascii=False, default=str)
        return file_path

    def load(self, file_path: str) -> dict[str, Any]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"会话文件不存在: {file_path}")
        with open(file_path, encoding="utf-8") as f:
            self.current_session = json.load(f)
        return self.current_session

    def list_sessions(self) -> list[dict[str, str]]:
        sessions = []
        if os.path.exists(self.sessions_dir):
            for fname in os.listdir(self.sessions_dir):
                if fname.endswith(".json"):
                    fpath = os.path.join(self.sessions_dir, fname)
                    try:
                        with open(fpath, encoding="utf-8") as f:
                            data = json.load(f)
                        sessions.append({
                            "file": fpath,
                            "name": data.get("name", fname),
                            "session_id": data.get("session_id", ""),
                            "created_at": data.get("created_at", ""),
                            "file_name": data.get("file_name", ""),
                            "analysis_count": len(data.get("analyses", [])),
                        })
                    except Exception:
                        pass
        sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return sessions

    def clear_session(self) -> None:
        self.current_session = {}

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.history[-limit:]

    def set_config(self, key: str, value: Any) -> None:
        if self.current_session:
            self.current_session.setdefault("config", {})[key] = value

    def get_config(self, key: str, default: Any = None) -> Any:
        if self.current_session:
            return self.current_session.get("config", {}).get(key, default)
        return default
