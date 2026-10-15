#!/bin/bash
# build_appimage.sh — AKIA AppImage 构建脚本
#
# 用法:
#   chmod +x build_appimage.sh
#   ./build_appimage.sh
#
# 前置条件:
#   1. Python 3.11+ 已安装
#   2. pip install -r requirements.txt -r dev-requirements.txt
#      (构建还需: pip install pyinstaller)
#   3. sudo apt install file  # appimagetool 需要
#
# 供应链说明（2026-10-15 审查修复）:
#   下载的 appimagetool 必须通过 packaging/appimagetool.sha256 校验；
#   首次固定/升级上游二进制时更新该文件（校验失败即中止，防上游资产被替换）。

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="AKIA"
BIN_NAME="akia"
APP_VERSION=$(python -c "import sys; sys.path.insert(0, '${SCRIPT_DIR}'); from config.settings import APP_VERSION; print(APP_VERSION)")
BUILD_DIR="${SCRIPT_DIR}/build"
APPDIR_DIR="${BUILD_DIR}/AppDir"
DIST_DIR="${BUILD_DIR}/${BIN_NAME}.dist"

echo "=========================================="
echo "  AKIA AppImage 构建"
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
exec "${HERE}/usr/bin/akia" "$@"
EOF
chmod +x "${APPDIR_DIR}/AppRun"

# 复制桌面文件
cp "${SCRIPT_DIR}/packaging/akia.desktop" "${APPDIR_DIR}/usr/share/applications/"
cp "${SCRIPT_DIR}/packaging/akia.desktop" "${APPDIR_DIR}/akia.desktop"

# 复制图标
if [ -f "${SCRIPT_DIR}/assets/logo.png" ]; then
    cp "${SCRIPT_DIR}/assets/logo.png" "${APPDIR_DIR}/usr/share/icons/hicolor/256x256/apps/akia.png"
    cp "${SCRIPT_DIR}/assets/logo.png" "${APPDIR_DIR}/akia.png"
fi

# ── 步骤 4: 下载 appimagetool ──────────────────────────────
echo ""
echo "[4/5] 准备 appimagetool..."
APPIMAGETOOL="${BUILD_DIR}/appimagetool"
APPIMAGETOOL_SHA_FILE="${SCRIPT_DIR}/packaging/appimagetool.sha256"

# 校验 helpers：优先 sha256sum，macOS 回退 shasum
_sha256_of() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    else
        shasum -a 256 "$1" | awk '{print $1}'
    fi
}

if [ ! -f "${APPIMAGETOOL}" ]; then
    echo "  下载 appimagetool..."
    wget -q -O "${APPIMAGETOOL}" \
        "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x "${APPIMAGETOOL}"
fi

# 强制校验（v4.4.1 供应链修复）：无 pin 文件或哈希不符 → 中止构建
if [ ! -f "${APPIMAGETOOL_SHA_FILE}" ]; then
    echo "[error] 缺少 appimagetool 校验文件: ${APPIMAGETOOL_SHA_FILE}"
    echo "        首次使用时：下载官方 appimagetool 后运行"
    echo "        sha256sum ${APPIMAGETOOL} | awk '{print \$1}' > packaging/appimagetool.sha256"
    exit 1
fi
EXPECTED=$(tr -d ' \n' < "${APPIMAGETOOL_SHA_FILE}")
ACTUAL=$(_sha256_of "${APPIMAGETOOL}")
if [ "${EXPECTED}" != "${ACTUAL}" ]; then
    echo "[error] appimagetool 校验失败（上游资产可能已变化或本地文件被替换）"
    echo "        期望: ${EXPECTED}"
    echo "        实际: ${ACTUAL}"
    echo "        确认无误后更新 packaging/appimagetool.sha256 再构建"
    rm -f "${APPIMAGETOOL}"  # 不保留未校验的二进制
    exit 1
fi
echo "  appimagetool sha256 校验通过"

# ── 步骤 5: 打包 AppImage ──────────────────────────────────
echo ""
echo "[5/5] 打包 AppImage..."
OUTPUT_FILE="${BUILD_DIR}/${APP_NAME}-${APP_VERSION}-x86_64.AppImage"
# 无 FUSE 的环境（容器/CI）用 --appimage-extract-and-run 直接解包运行
# 判定 FUSE 是否真正可用：仅有 /dev/fuse 但缺 libfuse.so.2 时
# appimagetool 仍会以 "dlopen(): error loading libfuse.so.2" 失败（v4.4.0 构建实测）。
APPIMAGETOOL_ARGS=()
if [ ! -e /dev/fuse ]; then
    echo "  未检测到 /dev/fuse → 使用 --appimage-extract-and-run"
    APPIMAGETOOL_ARGS=(--appimage-extract-and-run)
elif ! ldconfig -p 2>/dev/null | grep -q 'libfuse\.so\.2'; then
    echo "  缺少 libfuse.so.2（/dev/fuse 存在但 FUSE 运行库缺失）→ 使用 --appimage-extract-and-run"
    APPIMAGETOOL_ARGS=(--appimage-extract-and-run)
fi
ARCH=x86_64 "${APPIMAGETOOL}" "${APPIMAGETOOL_ARGS[@]}" "${APPDIR_DIR}" "${OUTPUT_FILE}"

# ── 步骤 6: 生成发布校验文件 (.sha256) ──────────────────────
OUTPUT_BASENAME=$(basename "${OUTPUT_FILE}")
SHA_FILE="${OUTPUT_FILE}.sha256"
echo "  生成 ${OUTPUT_BASENAME}.sha256 ..."
printf '%s  %s\n' "$(_sha256_of "${OUTPUT_FILE}")" "${OUTPUT_BASENAME}" > "${SHA_FILE}"

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
