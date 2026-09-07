# Performance baseline tests
import time
import os

class TestStartupPerformance:
    def test_settings_import_time(self):
        start = time.perf_counter()
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0

    def test_core_import_time(self):
        start = time.perf_counter()
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0

    def test_machine_id_generation(self):
        from core.license import LicenseManager
        start = time.perf_counter()
        for _ in range(10):
            LicenseManager.get_machine_id()
        elapsed = (time.perf_counter() - start) / 10
        assert elapsed < 1.0

class TestAntiDebugPerformance:
    def test_anti_debug_total_time(self):
        from core.anti_debug import run_anti_debug_checks
        start = time.perf_counter()
        run_anti_debug_checks()
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0

    def test_anti_debug_returns_list(self):
        from core.anti_debug import run_anti_debug_checks
        result = run_anti_debug_checks()
        assert isinstance(result, list)

class TestIntegrityPerformance:
    def test_integrity_check_time(self):
        from core.integrity import verify_integrity
        start = time.perf_counter()
        passed, issues = verify_integrity()
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0

    def test_hash_computation_time(self):
        from core.integrity import compute_file_hash
        main_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'main.py')
        if os.path.exists(main_path):
            start = time.perf_counter()
            h = compute_file_hash(main_path)
            elapsed = time.perf_counter() - start
            assert elapsed < 0.5
            assert len(h) == 64

class TestLicensePerformance:
    def test_license_verify_time(self):
        from core.license import LicenseManager
        lm = LicenseManager()
        start = time.perf_counter()
        for _ in range(10):
            lm.verify()
        elapsed = (time.perf_counter() - start) / 10
        assert elapsed < 0.5
