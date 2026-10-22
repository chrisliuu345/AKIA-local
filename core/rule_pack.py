"""Versioned, non-executable rule packs for sampling, judgement, and quality."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

RULE_PACK_SCHEMA_VERSION = "1.0"
MAX_RULE_PACK_BYTES = 1_000_000
RULE_CATEGORIES = ("sampling", "judgement", "quality")
RULE_TYPES = ("threshold", "categorical", "configuration")
SEVERITIES = ("error", "warning", "info")
THRESHOLD_OPERATORS = (">", ">=", "<", "<=", "==", "!=", "between")
CATEGORICAL_OPERATORS = ("==", "!=", "in", "not_in")

_ID_RE = re.compile(r"^[a-z][a-z0-9_.-]{1,63}$")


def _is_number(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        number = float(value)
    except (OverflowError, TypeError, ValueError):
        return False
    return math.isfinite(number)


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False)


def _fingerprint(payload: dict[str, Any]) -> str:
    digest = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
    return f"rulepack-hash-v1:{digest}"


@dataclass
class Rule:
    """One declarative rule; no expressions or code are evaluated."""

    id: str
    category: str
    type: str
    name: str = ""
    description: str = ""
    metric: str = ""
    operator: str = ""
    value: Any = None
    severity: str = "error"
    message: str = ""
    settings: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.id = str(self.id or "").strip().lower()
        self.category = str(self.category or "").strip().lower()
        self.type = str(self.type or "").strip().lower()
        self.name = str(self.name or self.id).strip()
        self.description = str(self.description or "").strip()
        self.metric = str(self.metric or "").strip()
        self.operator = str(self.operator or "").strip()
        self.severity = str(self.severity or "error").strip().lower()
        self.message = str(self.message or "").strip()
        if not _ID_RE.fullmatch(self.id):
            raise ValueError(
                f"规则 id 非法: {self.id!r}（需为小写字母开头、2-64 位 [a-z0-9_.-]）")
        if self.category not in RULE_CATEGORIES:
            raise ValueError(
                f"未知规则类别: {self.category!r}（可选 {list(RULE_CATEGORIES)}）")
        if self.type not in RULE_TYPES:
            raise ValueError(
                f"未知规则类型: {self.type!r}（可选 {list(RULE_TYPES)}）")
        if self.severity not in SEVERITIES:
            raise ValueError(
                f"未知规则严重度: {self.severity!r}（可选 {list(SEVERITIES)}）")
        if self.type == "configuration":
            if not isinstance(self.settings, dict) or not self.settings:
                raise ValueError(f"配置规则 {self.id} 需要非空 settings 对象")
            if self.metric or self.operator:
                raise ValueError(f"配置规则 {self.id} 不应设置 metric/operator")
            return
        if not self.metric:
            raise ValueError(f"规则 {self.id} 缺少 metric")
        if self.value is None:
            raise ValueError(f"规则 {self.id} 缺少 value")
        if self.type == "threshold":
            if self.operator not in THRESHOLD_OPERATORS:
                raise ValueError(
                    f"阈值规则 {self.id} 运算符非法: {self.operator!r}")
            if self.operator == "between":
                if (not isinstance(self.value, list) or len(self.value) != 2
                        or not all(_is_number(item) for item in self.value)):
                    raise ValueError(f"between 规则 {self.id} 的 value 必须是两个数值")
                if float(self.value[0]) > float(self.value[1]):
                    raise ValueError(f"between 规则 {self.id} 的下界不能大于上界")
            elif not _is_number(self.value):
                raise ValueError(f"阈值规则 {self.id} 的 value 必须是有限数值")
        else:
            if self.operator not in CATEGORICAL_OPERATORS:
                raise ValueError(
                    f"分类规则 {self.id} 运算符非法: {self.operator!r}")
            if self.operator in ("in", "not_in") and not isinstance(self.value, list):
                raise ValueError(f"{self.operator} 规则 {self.id} 的 value 必须是数组")
        if not self.message:
            self.message = f"{self.name} 未满足"

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "category": self.category,
            "type": self.type,
            "name": self.name,
            "description": self.description,
            "severity": self.severity,
            "message": self.message,
        }
        if self.type == "configuration":
            payload["settings"] = dict(self.settings)
        else:
            payload.update({
                "metric": self.metric,
                "operator": self.operator,
                "value": self.value,
            })
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Rule:
        if not isinstance(data, dict):
            raise ValueError("规则必须是 JSON 对象")
        allowed = {
            "id", "category", "type", "name", "description", "metric",
            "operator", "value", "severity", "message", "settings",
        }
        unknown = sorted(set(data) - allowed)
        if unknown:
            raise ValueError(f"规则包含未知字段: {', '.join(unknown)}")
        return cls(**data)

    def evaluate(self, metrics: dict[str, Any]) -> dict[str, Any]:
        base = {
            "rule_id": self.id,
            "category": self.category,
            "type": self.type,
            "severity": self.severity,
        }
        if self.type == "configuration":
            return {**base, "status": "configured", "message": self.message}
        if self.metric not in metrics:
            return {
                **base, "status": "skipped", "metric": self.metric,
                "message": f"指标 {self.metric} 未提供",
            }
        actual = metrics[self.metric]
        try:
            passed = self._matches(actual)
        except (TypeError, ValueError) as exc:
            return {
                **base, "status": "fail", "metric": self.metric,
                "actual": actual, "expected": self.value,
                "message": f"{self.message}: {exc}",
            }
        return {
            **base, "status": "pass" if passed else "fail",
            "metric": self.metric, "actual": actual,
            "expected": {"operator": self.operator, "value": self.value},
            "message": "" if passed else self.message,
        }

    def _matches(self, actual: Any) -> bool:
        if self.type == "threshold":
            if not _is_number(actual):
                raise ValueError("实际值不是有限数值")
            number = float(actual)
            if self.operator == "between":
                low, high = (float(item) for item in self.value)
                return low <= number <= high
            target = float(self.value)
            if self.operator == ">":
                return number > target
            if self.operator == ">=":
                return number >= target
            if self.operator == "<":
                return number < target
            if self.operator == "<=":
                return number <= target
            if self.operator == "==":
                return number == target
            return number != target

        if self.operator == "==":
            return actual == self.value
        if self.operator == "!=":
            return actual != self.value
        matched = actual in self.value
        return matched if self.operator == "in" else not matched


@dataclass
class RulePack:
    """A portable, versioned collection of declarative rules."""

    id: str
    name: str
    version: str
    rules: list[Rule]
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    fingerprint: str = ""
    schema_version: str = RULE_PACK_SCHEMA_VERSION

    def __post_init__(self) -> None:
        self.id = str(self.id or "").strip().lower()
        self.name = str(self.name or "").strip()
        self.version = str(self.version or "").strip()
        self.description = str(self.description or "").strip()
        if self.schema_version != RULE_PACK_SCHEMA_VERSION:
            raise ValueError(
                f"不支持的规则包 schema 版本: {self.schema_version}")
        if not _ID_RE.fullmatch(self.id):
            raise ValueError(
                f"规则包 id 非法: {self.id!r}（需为小写字母开头、2-64 位 [a-z0-9_.-]）")
        if not self.name or not self.version:
            raise ValueError("规则包 name/version 不能为空")
        if not isinstance(self.rules, list) or not self.rules:
            raise ValueError("规则包至少包含一条规则")
        if not all(isinstance(rule, Rule) for rule in self.rules):
            raise ValueError("rules 仅接受 Rule 对象")
        ids = [rule.id for rule in self.rules]
        if len(ids) != len(set(ids)):
            raise ValueError("规则包内规则 id 必须唯一")
        if not isinstance(self.metadata, dict):
            raise ValueError("metadata 必须是对象")
        expected = _fingerprint(self._payload())
        if self.fingerprint and self.fingerprint != expected:
            raise ValueError("规则包 fingerprint 与内容不一致")
        self.fingerprint = expected

    def _payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "metadata": self.metadata,
            "rules": [rule.to_dict() for rule in self.rules],
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RulePack:
        if not isinstance(data, dict):
            raise ValueError("规则包必须是 JSON 对象")
        allowed = {
            "schema_version", "id", "name", "version", "description",
            "metadata", "rules", "fingerprint",
        }
        unknown = sorted(set(data) - allowed)
        if unknown:
            raise ValueError(f"规则包包含未知字段: {', '.join(unknown)}")
        raw_rules = data.get("rules")
        if not isinstance(raw_rules, list):
            raise ValueError("rules 必须是数组")
        return cls(
            schema_version=str(data.get("schema_version")
                               or RULE_PACK_SCHEMA_VERSION),
            id=str(data.get("id") or ""),
            name=str(data.get("name") or ""),
            version=str(data.get("version") or ""),
            description=str(data.get("description") or ""),
            metadata=dict(data.get("metadata") or {}),
            rules=[Rule.from_dict(item) for item in raw_rules],
            fingerprint=str(data.get("fingerprint") or ""),
        )

    @classmethod
    def load(cls, path: str | Path) -> RulePack:
        source = Path(path).expanduser()
        size = source.stat().st_size
        if size > MAX_RULE_PACK_BYTES:
            raise ValueError(
                f"规则包过大: {size} bytes（上限 {MAX_RULE_PACK_BYTES}）")
        return cls.from_dict(json.loads(source.read_text(encoding="utf-8")))

    def save(self, path: str | Path) -> Path:
        target = Path(path).expanduser()
        target.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2,
                       sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8")
        return target

    def evaluate(self, metrics: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(metrics, dict):
            raise ValueError("metrics 必须是对象")
        results = [rule.evaluate(metrics) for rule in self.rules]
        failures = [item for item in results if item["status"] == "fail"]
        errors = [item for item in failures if item["severity"] == "error"]
        warnings = [item for item in failures if item["severity"] == "warning"]
        skipped = [item for item in results if item["status"] == "skipped"]
        return {
            "schema_version": RULE_PACK_SCHEMA_VERSION,
            "pack_id": self.id,
            "pack_version": self.version,
            "fingerprint": self.fingerprint,
            "ok": not errors,
            "total": len(results),
            "passed": sum(item["status"] == "pass" for item in results),
            "failed": len(failures),
            "errors": len(errors),
            "warnings": len(warnings),
            "skipped": len(skipped),
            "missing_metrics": sorted({item["metric"] for item in skipped}),
            "results": results,
        }
