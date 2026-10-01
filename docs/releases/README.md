# 发布记录（docs/releases）

发布说明与 payload 统一放在本目录**并入版本库**（不再放 gitignored 的 `TEMP/`，
避免模板散落丢失）。每个版本一个文件：`vX.Y.Z.md`，内容包含：

1. 发布形态（源码 prerelease / 打包）与交付物清单；
2. 本版要点（对齐 `ROADMAP.md` 的版本要点章节）；
3. 门禁证据：`python tools/release_check.py` 的输出摘要（版本一致性 / ruff /
   逐文件回归用例数 / 性能基线 8 项）；
4. 已知限制与遗留项（指向 `PLAN_vX.Y.Z.md` 或路线图）。

## 模板

```markdown
# vX.Y.Z 发布说明（<源码 prerelease | 打包>）

## 交付物
- GitHub Source zip / tar.gz（tag `vX.Y.Z`，标记 pre-release）
- （如打包）AKIA-X.Y.Z-x86_64.AppImage

## 要点
- …

## 门禁证据（tools/release_check.py）
- 版本一致性：通过（四端 + 文档产物名）
- ruff：全库零告警
- 逐文件回归：N 文件 / M 用例（沙箱外复跑清单见 CI 日志）
- 性能基线：8 项在 tolerance ×4 内（冷启动 / 百万行导入 / 5k 图 / 5k ML /
  SPC 10 万 / SPC 100 万 / MSA 10 万 / ML 10 万）

## 已知限制
- …
```

## 已有记录

- `v4.2.0.md` — 算法可信度与深度（2026-09-22 源码 prerelease；2026-09-23 追加
  Linux AppImage 打包与 GitHub Release 交付，含 SHA256 与冒烟证据）
