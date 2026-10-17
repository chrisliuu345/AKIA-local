"""公开开源定位的元数据回归测试。"""

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PUBLIC_DOCS = (
    ROOT / "README.md",
    ROOT / "README.en.md",
    ROOT / "ROADMAP.md",
    ROOT / "ROADMAP.en.md",
)
RETIRED_POSITIONING = (
    "personal-subscription",
    "个人订阅级",
    "proprietary software license",
    "all rights reserved",
    "闭源商业软件",
    "AKIM IE/Quality",
)


def test_apache_license_and_notice():
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    notice = (ROOT / "NOTICE").read_text(encoding="utf-8")

    assert "Apache License" in license_text
    assert "Version 2.0, January 2004" in license_text
    assert "Copyright 2026 AKIA contributors" in notice


def test_public_docs_use_open_source_positioning():
    for path in PUBLIC_DOCS:
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in RETIRED_POSITIONING:
            assert phrase.lower() not in lowered, (
                f"{path.name} 仍包含已退役的闭源/订阅定位: {phrase}"
            )

    assert "Apache License 2.0" in (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Apache License 2.0" in (ROOT / "README.en.md").read_text(encoding="utf-8")


def test_program_metadata_uses_open_source_identity():
    from config.settings import APP_FULL_NAME

    assert "Open-source" in APP_FULL_NAME
    assert "Personal IE" in APP_FULL_NAME

    for rel in ("version_info.txt", "build_pyinstaller.py"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "Apache License 2.0" in text
        assert "AKIA contributors" in text


def test_distribution_includes_license_and_notice():
    build_script = (ROOT / "build_pyinstaller.py").read_text(encoding="utf-8")
    installer = (ROOT / "packaging" / "AKIA-installer.iss").read_text(encoding="utf-8")

    assert '("LICENSE", ".")' in build_script
    assert '("NOTICE", ".")' in build_script
    assert r"LicenseFile=..\LICENSE" in installer
