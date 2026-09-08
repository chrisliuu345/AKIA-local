#!/bin/bash
# build_deb.sh — QA-Tool .deb 包构建脚本
#
# 用法:
#   chmod +x build_deb.sh
#   ./build_deb.sh
#
# 前置条件:
#   1. Python 3.11+ 已安装
#   2. pip install -r requirements.txt -r dev-requirements.txt
#      (dev-requirements 含 pyinstaller; 构建需另外 pip install pyinstaller)
#   3. sudo apt install dpkg-dev

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="qa-tool"
APP_VERSION=$(python -c "import sys; sys.path.insert(0, '${SCRIPT_DIR}'); from config.settings import APP_VERSION; print(APP_VERSION)")
DEB_DIR="${SCRIPT_DIR}/build/${APP_NAME}_${APP_VERSION}_amd64"
DIST_DIR="${SCRIPT_DIR}/build/${APP_NAME}.dist"

echo "=========================================="
echo "  QA-Tool .deb 包构建"
echo "  版本: ${APP_VERSION}"
echo "=========================================="

# ── 步骤 1: 清理旧构建 ──────────────────────────────────────
echo ""
echo "[1/4] 清理旧构建..."
rm -rf "${DEB_DIR}"

# ── 步骤 2: PyInstaller onedir 构建 ────────────────────────
echo ""
echo "[2/4] 执行 PyInstaller onedir 构建..."
cd "${SCRIPT_DIR}"
python build_pyinstaller.py --name "${APP_NAME}"

if [ ! -d "${DIST_DIR}" ]; then
    echo "[error] 未找到 PyInstaller 输出目录: ${DIST_DIR}"
    exit 1
fi

# ── 步骤 3: 创建 deb 包结构 ────────────────────────────────
echo ""
echo "[3/4] 创建 deb 包结构..."
mkdir -p "${DEB_DIR}/DEBIAN"
mkdir -p "${DEB_DIR}/opt/qa-tool/bin"
mkdir -p "${DEB_DIR}/opt/qa-tool/share"
mkdir -p "${DEB_DIR}/usr/share/applications"
mkdir -p "${DEB_DIR}/usr/share/icons/hicolor/256x256/apps"

# 复制 PyInstaller 输出 (qa-tool 可执行 + _internal/)
cp -r "${DIST_DIR}"/* "${DEB_DIR}/opt/qa-tool/bin/"

# 复制控制文件(版本号动态注入)
mkdir -p "${DEB_DIR}/DEBIAN"
sed "s/^Version: .*/Version: ${APP_VERSION}/" \
    "${SCRIPT_DIR}/packaging/deb/DEBIAN/control" > "${DEB_DIR}/DEBIAN/control"
cp "${SCRIPT_DIR}/packaging/deb/DEBIAN/postinst" "${DEB_DIR}/DEBIAN/"
cp "${SCRIPT_DIR}/packaging/deb/DEBIAN/postrm" "${DEB_DIR}/DEBIAN/"
chmod 755 "${DEB_DIR}/DEBIAN/postinst"
chmod 755 "${DEB_DIR}/DEBIAN/postrm"

# 复制桌面文件和图标
cp "${SCRIPT_DIR}/packaging/qa-tool.desktop" "${DEB_DIR}/usr/share/applications/"
if [ -f "${SCRIPT_DIR}/assets/logo.png" ]; then
    cp "${SCRIPT_DIR}/assets/logo.png" "${DEB_DIR}/usr/share/icons/hicolor/256x256/apps/qa-tool.png"
fi

# ── 步骤 4: 打包 .deb ──────────────────────────────────────
echo ""
echo "[4/4] 打包 .deb..."
# dpkg-deb 要求 control 目录权限 <= 755; 统一目录为 755 防 ACL/umask 干扰
find "${DEB_DIR}" -type d -exec chmod 755 {} +
OUTPUT_FILE="${SCRIPT_DIR}/build/${APP_NAME}_${APP_VERSION}_amd64.deb"
dpkg-deb --build "${DEB_DIR}" "${OUTPUT_FILE}"

# ── 完成 ───────────────────────────────────────────────────
echo ""
echo "=========================================="
echo "  构建成功!"
echo "  输出: ${OUTPUT_FILE}"
echo "  大小: $(du -h "${OUTPUT_FILE}" | cut -f1)"
echo "=========================================="
echo ""
echo "安装方法:"
echo "  sudo dpkg -i ${APP_NAME}_${APP_VERSION}_amd64.deb"
echo "  sudo apt install -f  # 修复依赖（如有）"
echo ""
echo "卸载方法:"
echo "  sudo dpkg -r ${APP_NAME}"
