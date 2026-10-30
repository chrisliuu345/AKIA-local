"""Windows 安装包冒烟的文件核对与标签门闩。

标签任务本身只在 Windows runner 上编译安装包。这里锁定核对规则，
以及工作流不会在功能分支上跑 ``package-windows``。
"""

from pathlib import Path

import pytest

from tools.smoke_windows_installer import (
    ENTRY_RELATIVE,
    LICENSE_RELATIVE,
    NOTICE_MARKERS,
    NOTICE_RELATIVE,
    installer_arguments,
    main,
    payload_problems,
    prepare_install_root,
)

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def _write_payload(root: Path, *, entry: bytes, license_text: bytes,
                   notice: str | None) -> None:
    (root / ENTRY_RELATIVE).parent.mkdir(parents=True, exist_ok=True)
    (root / ENTRY_RELATIVE).write_bytes(entry)
    license_path = root / LICENSE_RELATIVE
    license_path.parent.mkdir(parents=True, exist_ok=True)
    license_path.write_bytes(license_text)
    if notice is not None:
        notice_path = root / NOTICE_RELATIVE
        notice_path.parent.mkdir(parents=True, exist_ok=True)
        notice_path.write_text(notice, encoding="utf-8")


def _valid_notice() -> str:
    return "\n".join(NOTICE_MARKERS) + "\n| pandas | 2 | BSD | |\n"


def test_payload_accepts_entry_license_and_notices(tmp_path: Path):
    license_file = tmp_path / "LICENSE"
    license_bytes = b"Apache License\nVersion 2.0\n"
    license_file.write_bytes(license_bytes)
    installed = tmp_path / "installed"
    _write_payload(
        installed,
        entry=b"MZ" + b"\x00" * 2048,
        license_text=license_bytes,
        notice=_valid_notice(),
    )
    assert payload_problems(installed, license_file) == []


def test_payload_accepts_project_license_with_windows_newlines(tmp_path: Path):
    license_file = tmp_path / "LICENSE"
    license_file.write_bytes(b"Apache License\nVersion 2.0\n")
    installed = tmp_path / "installed"
    _write_payload(
        installed,
        entry=b"MZ" + b"\x00" * 2048,
        license_text=b"Apache License\r\nVersion 2.0\r\n",
        notice=_valid_notice(),
    )
    assert payload_problems(installed, license_file) == []


def test_payload_rejects_missing_or_invalid_entry(tmp_path: Path):
    license_file = tmp_path / "LICENSE"
    license_file.write_bytes(b"license")
    installed = tmp_path / "installed"
    _write_payload(installed, entry=b"MZ", license_text=b"license",
                   notice=_valid_notice())
    problems = payload_problems(installed, license_file)
    assert any("程序入口" in item for item in problems)

    (installed / ENTRY_RELATIVE).unlink()
    problems = payload_problems(installed, license_file)
    assert any("缺少程序入口" in item for item in problems)


def test_payload_rejects_license_mismatch_and_missing_notice(tmp_path: Path):
    license_file = tmp_path / "LICENSE"
    license_file.write_bytes(b"project license")
    installed = tmp_path / "installed"
    _write_payload(
        installed,
        entry=b"MZ" + b"\x00" * 2048,
        license_text=b"other license",
        notice=None,
    )
    problems = payload_problems(installed, license_file)
    assert "安装结果中的 LICENSE 与项目 LICENSE 不一致" in problems
    assert any("缺少第三方归属" in item for item in problems)


def test_payload_rejects_notice_without_generated_markers(tmp_path: Path):
    license_file = tmp_path / "LICENSE"
    license_file.write_bytes(b"license")
    installed = tmp_path / "installed"
    _write_payload(
        installed,
        entry=b"MZ" + b"\x00" * 2048,
        license_text=b"license",
        notice="notices\n",
    )
    problems = payload_problems(installed, license_file)
    assert any("第三方归属内容不完整" in item for item in problems)


def test_silent_arguments_disable_startup_prompt():
    # /VERYSILENT 本身不会关掉启动确认框，漏掉 /SP- 会把标签任务挂死。
    args = installer_arguments(
        Path("AKIA-Setup.exe"),
        Path(r"C:\akia-installer-smoke"),
        Path(r"C:\akia-installer-smoke.log"),
    )
    assert "/VERYSILENT" in args
    assert "/SP-" in args
    assert "/SUPPRESSMSGBOXES" in args
    assert "/NORESTART" in args
    assert "/DIR=C:\\akia-installer-smoke" in args or any(
        arg.startswith("/DIR=") and arg.endswith("akia-installer-smoke") for arg in args)
    assert "/MERGETASKS=!desktopicon,!startmenu" in args


def test_prepare_install_root_rejects_system_directories(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("AKIA_INSTALLER_SMOKE_DIR", r"C:\Windows")
    with pytest.raises(RuntimeError, match="系统目录"):
        prepare_install_root()


def test_smoke_command_refuses_non_windows(monkeypatch, capsys):
    monkeypatch.setattr("tools.smoke_windows_installer.sys.platform", "linux")
    assert main([]) == 2
    assert "只能在 Windows 上运行" in capsys.readouterr().err


def _job_block(workflow: str, job_id: str) -> str:
    lines = workflow.splitlines(keepends=True)
    start = next(
        (index for index, line in enumerate(lines) if line.startswith(f"  {job_id}:")),
        None,
    )
    assert start is not None, job_id
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("  ") and not lines[index].startswith("   "):
            end = index
            break
    return "".join(lines[start:end])


def test_windows_installer_job_runs_only_on_version_tags():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    windows = _job_block(workflow, "package-windows")
    appimage = _job_block(workflow, "package-appimage")
    tag_guard = "if: startsWith(github.ref, 'refs/tags/v')"
    assert tag_guard in windows
    assert tag_guard in appimage
    assert "runs-on: windows-latest" in windows
    assert "tools/smoke_windows_installer.py" in windows
    assert "innosetup --version=6.7.1" in windows
    assert "actions/upload-artifact@v4" in windows
    assert "softprops/action-gh-release" not in windows
    assert "gh release" not in windows
    # 门闩必须在 job 上，不能只写在注释里。
    assert windows.split("steps:", 1)[0].count(tag_guard) == 1
