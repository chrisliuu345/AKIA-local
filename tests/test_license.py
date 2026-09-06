"""
License 系统单元测试 — v3.2.0+ 空操作实现
"""
from core.license import LicenseManager, LicenseStatus, verify_license


class TestLicenseManager:
    def test_get_machine_id_deterministic(self):
        id1 = LicenseManager.get_machine_id()
        id2 = LicenseManager.get_machine_id()
        assert id1 == id2

    def test_get_machine_id_format(self):
        mid = LicenseManager.get_machine_id()
        assert len(mid) == 32
        assert all(c in '0123456789abcdef' for c in mid)

    def test_verify_always_valid(self):
        mgr = LicenseManager()
        valid, status = mgr.verify()
        assert valid is True
        assert status == LicenseStatus.VALID

    def test_activate_always_success(self):
        mgr = LicenseManager()
        result = mgr.activate("any-license-data")
        assert result is True

    def test_get_license_info(self):
        mgr = LicenseManager()
        info = mgr.get_license_info()
        assert info["status"] == "active"
        assert "3.2.0" in info["message"]

    def test_verify_license_function(self):
        valid, status = verify_license()
        assert valid is True
        assert status == LicenseStatus.VALID


class TestAntiDebug:
    def test_no_crash(self):
        from core.anti_debug import run_anti_debug_checks
        result = run_anti_debug_checks()
        assert isinstance(result, list)

    def test_returns_list(self):
        from core.anti_debug import run_anti_debug_checks
        result = run_anti_debug_checks()
        assert len(result) >= 0


class TestIntegrity:
    def test_compute_file_hash(self):
        from core.integrity import compute_file_hash
        h = compute_file_hash("main.py")
        assert len(h) == 64  # SHA-256

    def test_compute_all_hashes(self):
        from core.integrity import compute_all_hashes
        hashes = compute_all_hashes()
        assert isinstance(hashes, dict)
        assert len(hashes) > 0

    def test_verify_integrity(self):
        from core.integrity import verify_integrity
        ok, msg = verify_integrity()
        assert isinstance(ok, bool)
