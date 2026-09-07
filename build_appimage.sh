#!/bin/bash
# build_appimage.sh — QA-Tool AppImage 构建脚本
#
# 用法:
#   chmod +x build_appimage.sh
#   ./build_appimage.sh
#
# 前置条件:
#   1. Python 3.11+ 已安装
#   2. pip install -r requirements.txt -r dev-requirements.txt
#      (dev-requirements 含 pyinstaller; 构建需另外 pip install pyinstaller)
#   3. sudo apt install file  # appimagetool 需要

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="QA-Tool"
BIN_NAME="qa-tool"
APP_VERSION=$(python -c "import sys; sys.path.insert(0, '${SCRIPT_DIR}'); from config.settings import APP_VERSION; print(APP_VERSION)")
BUILD_DIR="${SCRIPT_DIR}/build"
APPDIR_DIR="${BUILD_DIR}/AppDir"
DIST_DIR="${BUILD_DIR}/${BIN_NAME}.dist"

echo "=========================================="
echo "  QA-Tool AppImage 构建"
echo "  版本: ${APP_VERSION}"
echo "=========================================="

# ── 步骤 1: 清理旧构建 ──────────────────────────────────────
echo ""
echo "[1/5] 清理旧构建..."
rm -rf "${APPDIR_DIR}"

# ── 步骤 2: PyInstaller onedir 构建 ────────────────────────
echo ""
echo "[2/5] 执行 PyInstaller onedir 构建..."
cd "${SCRIPT_DIR}"
python build_pyinstaller.py --name "${BIN_NAME}"

if [ ! -d "${DIST_DIR}" ]; then
    echo "[error] 未找到 PyInstaller 输出目录: ${DIST_DIR}"
    exit 1
fi

# ── 步骤 3: 创建 AppDir 结构 ───────────────────────────────
echo ""
echo "[3/5] 创建 AppDir 结构..."
mkdir -p "${APPDIR_DIR}/usr/bin"
mkdir -p "${APPDIR_DIR}/usr/share/applications"
mkdir -p "${APPDIR_DIR}/usr/share/icons/hicolor/256x256/apps"

# 复制 PyInstaller 输出到 AppDir
cp -r "${DIST_DIR}"/* "${APPDIR_DIR}/usr/bin/"

# 创建启动脚本
cat > "${APPDIR_DIR}/AppRun" << 'EOF'
#!/bin/bash
SELF=$(readlink -f "$0")
HERE=${SELF%/*}
export PATH="${HERE}/usr/bin/:${PATH}"
exec "${HERE}/usr/bin/qa-tool" "$@"
EOF
chmod +x "${APPDIR_DIR}/AppRun"

# 复制桌面文件
cp "${SCRIPT_DIR}/packaging/qa-tool.desktop" "${APPDIR_DIR}/usr/share/applications/"
cp "${SCRIPT_DIR}/packaging/qa-tool.desktop" "${APPDIR_DIR}/qa-tool.desktop"

# 复制图标
if [ -f "${SCRIPT_DIR}/assets/logo.png" ]; then
    cp "${SCRIPT_DIR}/assets/logo.png" "${APPDIR_DIR}/usr/share/icons/hicolor/256x256/apps/qa-tool.png"
    cp "${SCRIPT_DIR}/assets/logo.png" "${APPDIR_DIR}/qa-tool.png"
fi

# ── 步骤 4: 下载 appimagetool ──────────────────────────────
echo ""
echo "[4/5] 准备 appimagetool..."
APPIMAGETOOL="${BUILD_DIR}/appimagetool"
if [ ! -f "${APPIMAGETOOL}" ]; then
    echo "  下载 appimagetool..."
    wget -q -O "${APPIMAGETOOL}" \
        "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x "${APPIMAGETOOL}"
fi

# ── 步骤 5: 打包 AppImage ──────────────────────────────────
echo ""
echo "[5/5] 打包 AppImage..."
OUTPUT_FILE="${BUILD_DIR}/${APP_NAME}-${APP_VERSION}-x86_64.AppImage"
ARCH=x86_64 "${APPIMAGETOOL}" "${APPDIR_DIR}" "${OUTPUT_FILE}"

# ── 完成 ───────────────────────────────────────────────────
echo ""
echo "=========================================="
echo "  构建成功!"
echo "  输出: ${OUTPUT_FILE}"
echo "  大小: $(du -h "${OUTPUT_FILE}" | cut -f1)"
echo "=========================================="
echo ""
echo "使用方法:"
echo "  chmod +x ${OUTPUT_FILE}"
echo "  ./${APP_NAME}-${APP_VERSION}-x86_64.AppImage"
