"""test_version_consistency.py — 版本与打包配置守卫

1. tools/check_version.py 必须通过（APP_VERSION 单一事实源 → 四处同步）
2. PyInstaller 不得把本机 user_config.json 打进安装包
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_version_check_tool_passes():
    """版本一致性检查（README/INSTALL/ROADMAP/版本资源/安装器）"""
    from tools.check_version import main

    assert main() == 0


def test_pyinstaller_bundles_default_config_only():
    """打包配置: 只带公共默认配置，避免夹带本机设备列表/告警密码"""
    import build_pyinstaller

    sources = [src for src, _dest in build_pyinstaller.DATA_FILES]
    assert "user_config.json" not in sources
    assert "user_config.default.json" in sources


def test_default_config_file_has_no_secrets():
    """随包默认配置不得包含设备列表或任何敏感键"""
    import json

    data = json.loads((ROOT / "user_config.default.json").read_text(encoding="utf-8"))
    assert "devices" not in data
    for key in data:
        assert not key.endswith(("_password", "_secret", "_token", "_api_key")), key
