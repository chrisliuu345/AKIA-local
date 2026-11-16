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

### Linux 安装包的宿主依赖

Linux 发布包含三种安装包：AppImage、`.deb`、`.rpm`。AppImage 由 `bash build_appimage.sh` 构建，另外需要 `file`、`wget`，以及 `packaging/appimagetool.sha256` 所固定的 appimagetool。没有 `libfuse.so.2` 时，构建脚本改用 `--appimage-extract-and-run`。

`.deb` 与 `.rpm` 由 `bash build_deb_rpm.sh` 构建，产物位于 `dist/`。构建机先装好下表中的宿主工具。

| 工具 | 用途 | Fedora | Debian / Ubuntu |
|------|------|--------|-----------------|
| `rpmbuild` | 构建 `.rpm` | `rpm-build` | `rpm` |
| `dpkg-deb` | 构建 `.deb` | `dpkg` | `dpkg`（系统已带） |
| `fakeroot` | 以非 root 身份写入包内属主 | `fakeroot` | `fakeroot` |

Fedora：

```bash
sudo dnf install -y rpm-build dpkg fakeroot
```

Debian / Ubuntu：

```bash
sudo apt-get install -y rpm fakeroot
```

## English

Core, server, connector, and development dependencies have separate source files. `requirements.lock` is the hashed core runtime lock; `requirements-ci.lock` is the hashed full CI and packaging environment, including PyInstaller. Regenerate both with Python 3.11 as the minimum compatibility target using uv, and install with `--require-hashes`.

The packaging script collects the installed dependency closure, copies license files under `licenses/`, writes `THIRD_PARTY_NOTICES.md`, and records per-file SHA256 values in `licenses/manifest.json`.

Linux releases include an AppImage, a `.deb`, and a `.rpm`. The AppImage is built with `bash build_appimage.sh`, which also needs `file`, `wget`, and the appimagetool pin in `packaging/appimagetool.sha256`. When `libfuse.so.2` is absent, the script falls back to `--appimage-extract-and-run`.

The `.deb` and `.rpm` are built with `bash build_deb_rpm.sh`, and the packages are written to `dist/`. Install the host tools below first.

| Tool | Role | Fedora | Debian / Ubuntu |
|------|------|--------|-----------------|
| `rpmbuild` | Build the `.rpm` | `rpm-build` | `rpm` |
| `dpkg-deb` | Build the `.deb` | `dpkg` | `dpkg` (already present) |
| `fakeroot` | Record root ownership without running as root | `fakeroot` | `fakeroot` |

Fedora: `sudo dnf install -y rpm-build dpkg fakeroot`

Debian / Ubuntu: `sudo apt-get install -y rpm fakeroot`
