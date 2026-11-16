#!/bin/bash
# build_deb_rpm.sh — 从 PyInstaller onedir 构建 Linux .deb 与 .rpm
#
# 用法:
#   bash build_deb_rpm.sh
#
# 前置条件:
#   1. Python 3.11+，且已安装 requirements.txt 与 PyInstaller
#   2. dpkg-deb（Debian/Ubuntu 自带；Fedora 软件包名为 dpkg）
#   3. rpmbuild（Debian/Ubuntu 软件包名为 rpm；Fedora 软件包名为 rpm-build）
#
# 产物:
#   dist/AKIA-<version>-amd64.deb
#   dist/AKIA-<version>-x86_64.rpm
#   以及同名 .sha256
#
# 安装布局与 packaging/akia.desktop 一致：程序在 /opt/akia/bin/akia，
# /usr/bin/akia 只是转去执行该路径。PyInstaller 按可执行文件的真实路径
# 查找 _internal，不能把 /usr/bin/akia 做成指向二进制的符号链接。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="AKIA"
BIN_NAME="akia"
APP_VERSION=$(python -c "import sys; sys.path.insert(0, '${SCRIPT_DIR}'); from config.settings import APP_VERSION; print(APP_VERSION)")
ONEDIR="${SCRIPT_DIR}/build/${BIN_NAME}.dist"
DIST_OUT="${SCRIPT_DIR}/dist"
DESKTOP_FILE="${SCRIPT_DIR}/packaging/akia.desktop"
ICON_FILE="${SCRIPT_DIR}/assets/logo.png"
NOTICE_FILE="${SCRIPT_DIR}/build/THIRD_PARTY_NOTICES.md"

DEB_FILE="${DIST_OUT}/${APP_NAME}-${APP_VERSION}-amd64.deb"
RPM_FILE="${DIST_OUT}/${APP_NAME}-${APP_VERSION}-x86_64.rpm"

# 宿主仍要提供的库：Qt 会在运行时 dlopen 它们，冻结包里没有。
# 名称与 CI 的 Qt 离屏运行库一致。
DEB_DEPENDS="libc6 (>= 2.34), zlib1g, libglib2.0-0t64 | libglib2.0-0, libgl1, libegl1, libfontconfig1, libfreetype6, libxkbcommon0, libdbus-1-3t64 | libdbus-1-3, libx11-6, libxcb1"
RPM_REQUIRES="glibc zlib glib2 mesa-libGL mesa-libEGL fontconfig freetype libxkbcommon dbus-libs libX11 libxcb"

echo "=========================================="
echo "  AKIA .deb / .rpm 构建"
echo "  版本: ${APP_VERSION}"
echo "=========================================="

for cmd in python dpkg-deb rpmbuild; do
    if ! command -v "${cmd}" >/dev/null 2>&1; then
        echo "[error] 缺少宿主工具: ${cmd}"
        echo "        安装方法见 docs/dependency-management.md"
        exit 1
    fi
done

if [ ! -f "${DESKTOP_FILE}" ]; then
    echo "[error] 缺少桌面文件: ${DESKTOP_FILE}"
    exit 1
fi
if [ ! -f "${ICON_FILE}" ]; then
    echo "[error] 缺少图标: ${ICON_FILE}"
    exit 1
fi

if [ ! -d "${ONEDIR}" ]; then
    echo ""
    echo "[1/4] 未找到 onedir，先执行 PyInstaller..."
    python "${SCRIPT_DIR}/build_pyinstaller.py" --name "${BIN_NAME}"
else
    echo ""
    echo "[1/4] 使用已有 onedir: ${ONEDIR}"
fi

if [ ! -x "${ONEDIR}/${BIN_NAME}" ]; then
    echo "[error] 未找到可执行文件: ${ONEDIR}/${BIN_NAME}"
    exit 1
fi
if [ ! -f "${NOTICE_FILE}" ]; then
    echo "[error] 缺少第三方归属: ${NOTICE_FILE}"
    echo "        先完成一次 PyInstaller 构建，以生成 THIRD_PARTY_NOTICES.md"
    exit 1
fi

_sha256_of() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    else
        shasum -a 256 "$1" | awk '{print $1}'
    fi
}

WORK="$(mktemp -d /tmp/akia-linux-pkg-XXXX)"
STAGE="${WORK}/root"
cleanup() {
    rm -rf "${WORK}"
}
trap cleanup EXIT

echo ""
echo "[2/4] 组装安装根（权限在 Unix 文件系统上归一，避免 NTFS 的 0777）..."
mkdir -p \
    "${STAGE}/opt/akia/bin" \
    "${STAGE}/usr/bin" \
    "${STAGE}/usr/share/applications" \
    "${STAGE}/usr/share/icons/hicolor/256x256/apps" \
    "${STAGE}/usr/share/doc/akia"
cp -a "${ONEDIR}/." "${STAGE}/opt/akia/bin/"
cat > "${STAGE}/usr/bin/akia" << 'EOF'
#!/bin/sh
exec /opt/akia/bin/akia "$@"
EOF
cp "${DESKTOP_FILE}" "${STAGE}/usr/share/applications/akia.desktop"
cp "${ICON_FILE}" "${STAGE}/usr/share/icons/hicolor/256x256/apps/akia.png"
cp "${SCRIPT_DIR}/LICENSE" "${SCRIPT_DIR}/NOTICE" "${NOTICE_FILE}" "${STAGE}/usr/share/doc/akia/"

python - "${STAGE}" << 'PY'
import os
import sys

stage = sys.argv[1]
leaked = []
for dirpath, dirnames, filenames in os.walk(stage, followlinks=False):
    os.chmod(dirpath, 0o755)
    for name in filenames:
        path = os.path.join(dirpath, name)
        if os.path.islink(path):
            continue
        if name == "user_config.json":
            leaked.append(path)
            continue
        with open(path, "rb") as handle:
            magic = handle.read(4)
        if magic == b"\x7fELF" and ".so" not in name:
            os.chmod(path, 0o755)
        else:
            os.chmod(path, 0o644)
if leaked:
    print("[error] 安装根含本机 user_config.json，已中止:", file=sys.stderr)
    for path in leaked:
        print(f"        {path}", file=sys.stderr)
    sys.exit(1)
default_cfg = os.path.join(stage, "opt/akia/bin/_internal/user_config.default.json")
if not os.path.isfile(default_cfg):
    print(f"[error] 缺少默认配置: {default_cfg}", file=sys.stderr)
    sys.exit(1)
PY
chmod 755 "${STAGE}/usr/bin/akia"

echo ""
echo "[3/4] 构建 .deb ..."
mkdir -p "${STAGE}/DEBIAN"
INSTALLED_KB="$(du -sk "${STAGE}" | awk '{print $1}')"
cat > "${STAGE}/DEBIAN/control" << EOF
Package: akia
Version: ${APP_VERSION}
Section: science
Priority: optional
Architecture: amd64
Maintainer: AKIA contributors <https://github.com/chrisliuu345/AKIA-local>
Homepage: https://github.com/chrisliuu345/AKIA-local
Installed-Size: ${INSTALLED_KB}
Depends: ${DEB_DEPENDS}
Description: Open-source personal IE and quality analysis
 AKIA is a local-first desktop application for industrial engineering
 and quality analysis.
EOF
cat > "${STAGE}/DEBIAN/postinst" << 'EOF'
#!/bin/sh
set -e
if [ "$1" = "configure" ] || [ -z "${1:-}" ]; then
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database -q /usr/share/applications || true
    fi
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -q /usr/share/icons/hicolor || true
    fi
fi
EOF
cat > "${STAGE}/DEBIAN/postrm" << 'EOF'
#!/bin/sh
set -e
if [ "$1" = "remove" ] || [ "$1" = "purge" ]; then
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database -q /usr/share/applications || true
    fi
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -q /usr/share/icons/hicolor || true
    fi
fi
EOF
chmod 755 "${STAGE}/DEBIAN/postinst" "${STAGE}/DEBIAN/postrm"
mkdir -p "${DIST_OUT}"
dpkg-deb --root-owner-group -Zxz -z3 --build "${STAGE}" "${DEB_FILE}"

# DEBIAN 只属于 deb，不能进 rpm 载荷。
rm -rf "${STAGE}/DEBIAN"

echo ""
echo "[4/4] 构建 .rpm ..."
TOPDIR="${WORK}/rpm"
mkdir -p "${TOPDIR}/BUILD" "${TOPDIR}/RPMS" "${TOPDIR}/SOURCES" "${TOPDIR}/SPECS" "${TOPDIR}/SRPMS"
SPEC="${TOPDIR}/SPECS/akia.spec"
cat > "${SPEC}" << EOF
Name: akia
Version: ${APP_VERSION}
Release: 1
Summary: Open-source personal IE and quality analysis
License: Apache-2.0
URL: https://github.com/chrisliuu345/AKIA-local
BuildArch: x86_64
# 载荷是已经冻结的 PyInstaller 树。自动扫描会把包内 .so 的 soname 当成系统依赖。
AutoReqProv: no
Requires: ${RPM_REQUIRES}

# 不要剥离、重编译或生成 debuginfo，否则会改写冻结后的二进制。
%define debug_package %{nil}
%define _build_id_links none
%define __os_install_post %{nil}

%description
AKIA is a local-first desktop application for industrial engineering
and quality analysis.

%prep
%build

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}
cp -a ${STAGE}/. %{buildroot}/

%files
%defattr(-,root,root,-)
/opt/akia
/usr/bin/akia
/usr/share/applications/akia.desktop
/usr/share/icons/hicolor/256x256/apps/akia.png
/usr/share/doc/akia

%post
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications >/dev/null 2>&1 || :
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q /usr/share/icons/hicolor >/dev/null 2>&1 || :
fi

%postun
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications >/dev/null 2>&1 || :
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q /usr/share/icons/hicolor >/dev/null 2>&1 || :
fi
EOF

rpmbuild --define "_topdir ${TOPDIR}" -bb "${SPEC}"
BUILT_RPM="$(find "${TOPDIR}/RPMS" -type f -name '*.rpm' -print -quit)"
if [ -z "${BUILT_RPM}" ]; then
    echo "[error] rpmbuild 未产生 .rpm"
    exit 1
fi
cp -a "${BUILT_RPM}" "${RPM_FILE}"

write_sha() {
    local file="$1"
    local base
    base="$(basename "${file}")"
    printf '%s  %s\n' "$(_sha256_of "${file}")" "${base}" > "${file}.sha256"
}
write_sha "${DEB_FILE}"
write_sha "${RPM_FILE}"

echo ""
echo "  生成发布溯源清单..."
python "${SCRIPT_DIR}/tools/release_manifest.py" \
    --artifact "${DEB_FILE}" \
    --artifact "${RPM_FILE}" \
    --output "${SCRIPT_DIR}/build/release-manifest-deb-rpm.json"

echo ""
echo "=========================================="
echo "  构建成功!"
echo "  deb: ${DEB_FILE}"
echo "  rpm: ${RPM_FILE}"
echo "  deb 大小: $(du -h "${DEB_FILE}" | cut -f1)"
echo "  rpm 大小: $(du -h "${RPM_FILE}" | cut -f1)"
echo "=========================================="
