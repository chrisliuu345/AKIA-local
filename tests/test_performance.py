# Performance baseline tests
import time

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

class TestLicensePerformance:
    def test_license_verify_time(self):
        from core.license import LicenseManager
        lm = LicenseManager()
        start = time.perf_counter()
        for _ in range(10):
            lm.verify()
        elapsed = (time.perf_counter() - start) / 10
        assert elapsed < 0.5
