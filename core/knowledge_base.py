"""AI 知识库 — TF-IDF 离线检索 + LLM 上下文增强

零重依赖轻量 RAG：字符 n-gram TF-IDF + 余弦相似度。
- 中文无需分词（char analyzer 对 CJK 友好）
- 加载失败静默降级，不影响主程序
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


CATEGORY_LABELS = {
    "terminology": "术语",
    "standard": "标准",
    "table": "判定表",
    "six_sigma": "六西格玛",
}


class KnowledgeEntry:
    __slots__ = ("id", "title", "category", "keywords", "content", "extra", "score")

    def __init__(self, raw: Dict[str, Any], default_category: str):
        self.id = raw.get("id", "")
        self.title = raw.get("title", "")
        self.category = raw.get("category", default_category)
        self.keywords = raw.get("keywords", [])
        self.content = raw.get("content", "")
        self.extra = {
            k: v for k, v in raw.items()
            if k not in ("id", "title", "category", "keywords", "content")
        }
        self.score = 0.0

    def search_text(self) -> str:
        parts = [self.title, self.title, " ".join(self.keywords), self.content]
        if "formula" in self.extra:
            parts.append(str(self.extra["formula"]))
        return " ".join(p for p in parts if p)

    def category_label(self) -> str:
        return CATEGORY_LABELS.get(self.category, self.category)

    def format_brief(self) -> str:
        """供 LLM prompt 注入的紧凑格式"""
        text = f"【{self.category_label()}】{self.title}\n{self.content}"
        if "formula" in self.extra:
            text += f"\n公式: {self.extra['formula']}"
        if "thresholds" in self.extra:
            th = self.extra["thresholds"]
            text += "\n判定: " + "; ".join(f"{k}→{v}" for k, v in th.items())
        return text

    def format_full(self) -> str:
        """供 UI 展示的完整格式"""
        parts = [self.format_brief()]
        tv = self.extra.get("typical_values")
        if tv:
            parts.append("典型值: " + "; ".join(f"{k}: {v}" for k, v in tv.items()))
        td = self.extra.get("table_data")
        if td:
            cols = td.get("columns", [])
            parts.append(" | ".join(cols))
            for row in td.get("rows", []):
                parts.append(" | ".join(str(c) for c in row))
        ra = self.extra.get("related_analyses")
        if ra:
            parts.append("相关分析: " + ", ".join(ra))
        refs = self.extra.get("references")
        if refs:
            parts.append("参考: " + "; ".join(refs))
        return "\n".join(parts)


class KnowledgeBase:
    """内置质量标准/术语/判定表知识库，支持离线检索与 LLM 上下文增强"""

    DATA_DIR = Path(__file__).resolve().parent.parent / "config" / "knowledge"
    FILES = ("terminology.json", "standards.json", "tables.json", "six_sigma.json")

    def __init__(self, data_dir: Optional[Path] = None):
        self.entries: List[KnowledgeEntry] = []
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.matrix = None
        self.available = False
        try:
            self.load_all(Path(data_dir) if data_dir else self.DATA_DIR)
        except Exception:
            self.entries = []

    def load_all(self, data_dir: Path):
        raw_entries: List[KnowledgeEntry] = []
        for fname in self.FILES:
            fpath = data_dir / fname
            if not fpath.exists():
                continue
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            default_cat = fname.split(".")[0]
            for item in data.get("entries", []):
                raw_entries.append(KnowledgeEntry(item, default_cat))

        if not raw_entries:
            return

        self.entries = raw_entries
        corpus = [e.search_text() for e in self.entries]
        self.vectorizer = TfidfVectorizer(
            analyzer="char",
            ngram_range=(1, 2),
            sublinear_tf=True,
            lowercase=True,
            max_features=30000,
        )
        self.matrix = self.vectorizer.fit_transform(corpus)
        self.available = True

    def search(self, query: str, top_k: int = 5,
               category: Optional[str] = None,
               min_score: float = 0.02) -> List[KnowledgeEntry]:
        """语义检索，返回按相似度排序的条目（score 已写入 entry）"""
        if not self.available or not query.strip():
            return []

        q = self.vectorizer.transform([query.strip()])
        sims = cosine_similarity(q, self.matrix).ravel()

        order = sims.argsort()[::-1]
        results: List[KnowledgeEntry] = []
        for idx in order:
            if sims[idx] < min_score:
                break
            entry = self.entries[idx]
            if category and entry.category != category:
                continue
            entry.score = float(sims[idx])
            results.append(entry)
            if len(results) >= top_k:
                break
        return results

    def get_entry(self, entry_id: str) -> Optional[KnowledgeEntry]:
        for e in self.entries:
            if e.id == entry_id:
                return e
        return None

    def stats(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for e in self.entries:
            counts[e.category] = counts.get(e.category, 0) + 1
        return counts

    def enrich_prompt(self, base_prompt: str, question: str, top_k: int = 3) -> str:
        """将相关知识注入 LLM prompt（在问题之前插入参考段落）"""
        hits = self.search(question, top_k=top_k)
        if not hits:
            return base_prompt
        ref = "\n\n".join(h.format_brief() for h in hits)
        marker = "用户问题:"
        if marker in base_prompt:
            head, tail = base_prompt.rsplit(marker, 1)
            return f"{head}--- 知识库参考（优先依据以下内容作答）---\n{ref}\n\n{marker}{tail}"
        return f"{base_prompt}\n\n--- 知识库参考 ---\n{ref}"

    def offline_answer(self, question: str, top_k: int = 3) -> Optional[str]:
        """LLM 离线时用检索结果直接作答；无匹配返回 None"""
        hits = self.search(question, top_k=top_k)
        if not hits:
            return None
        parts = ["【知识库】已为您检索内置知识库（离线模式）：\n"]
        for i, h in enumerate(hits, 1):
            parts.append(f"━━ 【{i}】{h.title}（{h.category_label()}，相关度 {h.score:.2f}）━━")
            parts.append(h.format_full())
            parts.append("")
        return "\n".join(parts)


_kb_instance: Optional[KnowledgeBase] = None


def get_knowledge_base() -> KnowledgeBase:
    """全局单例（加载一次，全应用复用）"""
    global _kb_instance
    if _kb_instance is None:
        _kb_instance = KnowledgeBase()
    return _kb_instance
