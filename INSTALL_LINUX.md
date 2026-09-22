# QA-Tool Linux 安装指南

## 系统要求

- **操作系统**: 任意 x86_64 Linux（Ubuntu 22.04+ / Debian 12+ / Fedora / elementary OS 8+ 等）
- **架构**: x86_64 (amd64)
- **内存**: 4GB+ 推荐
- **磁盘空间**: 500MB+

## 安装方式

> **Linux 只发布 AppImage 一种格式**（自 v4.2.0 起不再构建 `.deb`），所有发行版通用；
> 需要系统集成可按下文自建 `.desktop` 入口。

### 方式 1: AppImage（唯一官方格式）

AppImage 是单文件分发格式，无需安装，双击即可运行。

```bash
# 1. 下载 AppImage
# 从 GitHub Releases 下载 QA-Tool-4.1.0-x86_64.AppImage

# 2. 添加执行权限
chmod +x QA-Tool-4.1.0-x86_64.AppImage

# 3. 运行
./QA-Tool-4.1.0-x86_64.AppImage
```

**可选: 集成到系统菜单**

```bash
# 移动到 /opt 目录
sudo mv QA-Tool-4.1.0-x86_64.AppImage /opt/qa-tool.AppImage

# 创建桌面入口
cat > ~/.local/share/applications/qa-tool.desktop << EOF
[Desktop Entry]
Name=QA-Tool
Exec=/opt/qa-tool.AppImage
Icon=qa-tool
Type=Application
Categories=Development;Science;
EOF

# 更新桌面数据库
update-desktop-database ~/.local/share/applications/
```

### 方式 2: 源码运行

```bash
# 1. 克隆仓库
git clone https://github.com/chrisliuu345/QA-Tool.git
cd QA-Tool

# 2. 安装依赖
pip install -r requirements.txt

# 3. 安装系统依赖（PySide6）
# Debian/Ubuntu:
sudo apt install libegl1 libgl1
# Fedora:
sudo dnf install mesa-libEGL mesa-libGL libxkbcommon libxcb xcb-util-cursor

# 4. 运行
python main.py
```

## 系统依赖

### 必需

```bash
# PySide6 运行时依赖
# Debian/Ubuntu:
sudo apt install libegl1 libgl1
# Fedora:
sudo dnf install mesa-libEGL mesa-libGL libxkbcommon libxcb xcb-util-cursor
```

### 推荐

```bash
# CJK 字体（中文显示）
# Debian/Ubuntu:
sudo apt install fonts-noto-cjk
# Fedora:
sudo dnf install google-noto-sans-cjk-fonts google-noto-sans-mono-cjk-vf-fonts

# ESP32 串口访问（如需硬件功能）
sudo usermod -aG dialout $USER
# 重新登录生效
```

### 密钥环（保存数据库密码需要）

Linux 下数据库连接密码通过系统密钥环（keyring）+ Fernet 加密保存：

```bash
# GNOME 桌面（推荐，开箱可用）
# Debian/Ubuntu:
sudo apt install gnome-keyring
# Fedora:
sudo dnf install gnome-keyring

# 无桌面环境 / 服务器场景可改用：
sudo apt install python3-keyrings.alt   # Debian/Ubuntu；或按 keyring 文档配置后端
pip install keyrings.alt                # 跨发行版（pip 方式）
```

未安装可用后端时程序仍可正常运行，但**数据库密码不会保存**（保存连接时会
弹窗提示），每次使用需重新输入；这是有意的安全设计，不会降级为明文存储。

## 构建自己的包

> 构建基于 PyInstaller（onedir），**Linux 侧仅打包 AppImage**（`.deb` 已停用，无需 `dpkg-dev`）。

### 安装构建工具

```bash
# 安装项目依赖（PyInstaller 需单独安装，未列入运行 requirements）
pip install -r requirements.txt
pip install pyinstaller

# appimagetool 需要 file / wget
# Debian/Ubuntu:
sudo apt install file wget
# Fedora:
sudo dnf install file wget
```

### 构建 AppImage

```bash
chmod +x build_appimage.sh
./build_appimage.sh

# 输出: build/QA-Tool-<版本>-x86_64.AppImage
```

## 故障排除

### 中文显示为方块

```bash
# 安装 CJK 字体
# Debian/Ubuntu:
sudo apt install fonts-noto-cjk
# Fedora:
sudo dnf install google-noto-sans-cjk-fonts google-noto-sans-mono-cjk-vf-fonts
```

### ESP32 串口权限

```bash
# 将用户加入 dialout 组
sudo usermod -aG dialout $USER

# 重新登录，或临时使用
newgrp dialout
```

### PySide6 启动失败

```bash
# 确保安装了 OpenGL 依赖
# Debian/Ubuntu:
sudo apt install libegl1 libgl1
# Fedora:
sudo dnf install mesa-libEGL mesa-libGL

# 如果使用 Wayland，尝试
export QT_QPA_PLATFORM=xcb
python main.py
```

## 版本信息

- **当前版本**: v4.1.0
- **Python**: 3.11+ (推荐 3.14)
- **Qt**: PySide6 6.5+
- **发布格式**: Linux 仅 AppImage；Windows 为 Inno Setup 安装包
- **测试**: 1798 用例 / 144 文件逐文件执行通过（2026-09-22 实测，规则见 `PYTEST_RULES.md`）

## 技术支持

- GitHub: https://github.com/chrisliuu345/QA-Tool
- Issues: https://github.com/chrisliuu345/QA-Tool/issues
