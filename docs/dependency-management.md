# Dependency and Release Management

## 中文

### 依赖分层

| 文件 | 用途 |
|------|------|
| `requirements.txt` | 桌面端核心运行时 |
| `requirements-server.txt` | 可选实时看板 |
| `requirements-connectors.txt` | 可选工业连接器 |
| `dev-requirements.txt` | 测试、静态检查和供应链审计工具 |
| `requirements.lock` | 核心运行时哈希锁 |
| `requirements-ci.lock` | CI 全量环境哈希锁（核心 + 可选组件 + 开发/打包工具） |

### 更新锁文件

使用 `uv` 以 Python 3.11 作为最低兼容目标重新解析依赖：

```bash
.venv/bin/pip install "uv>=0.13,<0.14"
.venv/bin/uv pip compile --generate-hashes --python-version 3.11 \
  --constraint constraints-known-good.txt \
  --output-file requirements.lock requirements.txt
.venv/bin/uv pip compile --generate-hashes --python-version 3.11 \
  --constraint constraints-known-good.txt \
  --output-file requirements-ci.lock requirements-ci.in
```

`constraints-known-good.txt` 固定已经过完整回归的 Qt、pandas、SQLAlchemy、FastAPI 等关键版本，避免锁文件自动跨主版本。CI 与应用安装必须使用 `--require-hashes`。不要手工编辑锁文件；升级依赖时先修改对应 `.txt`/`.in` 或约束文件，再重新生成并运行完整门禁。

### 许可证

打包脚本会从实际安装环境收集依赖闭包和许可证文本：

```bash
python tools/collect_licenses.py \
  --requirements requirements.txt \
  --requirements requirements-server.txt \
  --requirements requirements-connectors.txt \
  --allow-missing \
  --output build/third_party_licenses \
  --notice build/THIRD_PARTY_NOTICES.md
```

产物包含 `licenses/` 与 `THIRD_PARTY_NOTICES.md`；`licenses/manifest.json` 记录每个许可证文件的 SHA256。

## English

Core, server, connector, and development dependencies have separate source files. `requirements.lock` is the hashed core runtime lock; `requirements-ci.lock` is the hashed full CI and packaging environment, including PyInstaller. Regenerate both with Python 3.11 as the minimum compatibility target using uv, and install with `--require-hashes`.

The packaging script collects the installed dependency closure, copies license files under `licenses/`, writes `THIRD_PARTY_NOTICES.md`, and records per-file SHA256 values in `licenses/manifest.json`.
