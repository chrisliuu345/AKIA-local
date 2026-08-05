#!/bin/bash
# macOS 打包脚本 — 生成 QA-Tool.app
# 在 Mac 终端运行: bash build_mac.sh

set -e

echo "=== QA-Tool macOS 打包 ==="

# 1. 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 python3，请先安装 Python 3.11+"
    exit 1
fi
echo "Python: $(python3 --version)"

# 2. 安装依赖
echo ""
echo "安装依赖..."
pip3 install -r requirements.txt 2>&1 | tail -1

# 3. 安装 PyInstaller
pip3 install pyinstaller 2>&1 | tail -1
echo "PyInstaller: $(python3 -m PyInstaller --version)"

# 4. 生成图标 (如果没有 .icns 文件，自动生成一个简单图标)
if [ ! -f "QA-Tool.icns" ]; then
    echo ""
    echo "生成默认图标..."
    python3 -c "
import os
# 创建临时 iconset 目录
os.makedirs('QA-Tool.iconset', exist_ok=True)
# 用 Python 生成一个简单的 1024x1024 PNG 图标
from PIL import Image, ImageDraw
sz = 1024
img = Image.new('RGBA', (sz, sz), (0,0,0,0))
d = ImageDraw.Draw(img)
# 深蓝圆角矩形
d.rounded_rectangle([80, 200, sz-80, sz-200], radius=120, fill='#1b5faa')
# Q字母
from PIL import ImageFont
try:
    font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 380)
except:
    font = ImageFont.load_default()
bbox = d.textbbox((0,0), 'Q', font=font)
tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
d.text(((sz-tw)//2, (sz-th)//2 - 40), 'Q', fill='white', font=font)
img.save('QA-Tool.iconset/icon_512x512@2x.png', 'PNG')
print('图标已生成')
"
    # 用 macOS 自带工具转 icns (需要先缩小 png)
    iconutil -c icns QA-Tool.iconset 2>/dev/null && echo "ICNS 生成成功" || echo "警告: ICNS 生成失败，将无图标"
fi

# 5. 构建
echo ""
echo "构建 QA-Tool.app..."
python3 -m PyInstaller --clean --noconfirm QA-Tool-mac.spec 2>&1 | grep -E "Building|complete|Error|FAIL" || true

# 6. 检查
echo ""
if [ -d "dist/QA-Tool.app" ]; then
    SIZE=$(du -sh dist/QA-Tool.app | cut -f1)
    echo "=== 打包成功 ==="
    echo "位置: $(pwd)/dist/QA-Tool.app"
    echo "大小: $SIZE"
    echo ""
    echo "分发方式:"
    echo "  1. 将 dist/QA-Tool.app 压缩为 ZIP 发给用户"
    echo "  2. 或创建 DMG: hdiutil create -volname QA-Tool -srcfolder dist/ QA-Tool.dmg"
    echo ""
    echo "注意: 首次启动可能需要右键 → 打开 (绕过 Gatekeeper)"
else
    echo "=== 打包失败，请检查上方错误信息 ==="
    exit 1
fi
