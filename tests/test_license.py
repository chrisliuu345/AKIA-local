"""
License 系统单元测试
"""
import pytest
import json
import os
import tempfile
import base64
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from core.license_keys import LICENSE_PRODUCT
from core.anti_debug import run_anti_debug_checks, is_debugger_detected
from core.integrity import compute_file_hash, compute_all_hashes, verify_integrity


def _generate_test_keypair():
    """Generate an Ed25519 key pair for testing and patch the public key."""
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    except ImportError:
        pytest.skip("cryptography library not installed")

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    from cryptography.hazmat.primitives import serialization
    public_bytes = public_key.public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw
    )
    test_public_key_b64 = base64.b64encode(public_bytes).decode('utf-8')
    return private_key, test_public_key_b64


class TestLicenseManager:
    def test_get_machine_id_deterministic(self):
        from core.license import LicenseManager
        id1 = LicenseManager.get_machine_id()
        id2 = LicenseManager.get_machine_id()
        assert id1 == id2

    def test_get_machine_id_format(self):
        from core.license import LicenseManager
        mid = LicenseManager.get_machine_id()
        assert len(mid) == 32
        assert all(c in '0123456789abcdef' for c in mid)

    def test_verify_no_license(self):
        from core.license import LicenseManager, LicenseStatus
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = LicenseManager()
            mgr._license_dir = tmpdir
            mgr._license_path = os.path.join(tmpdir, "license.dat")
            assert mgr.verify() == LicenseStatus.INVALID

    def test_activate_and_verify(self):
        from core.license import LicenseManager, LicenseStatus
        private_key, test_pub_b64 = _generate_test_keypair()

        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = LicenseManager()
            mgr._license_dir = tmpdir
            mgr._license_path = os.path.join(tmpdir, "license.dat")

            machine_id = mgr.get_machine_id()
            expires = (datetime.now() + timedelta(days=365)).isoformat()

            payload = {
                "product": LICENSE_PRODUCT,
                "machine_id": machine_id,
                "licensee": "Test User",
                "expires_at": expires,
                "features": ["all"],
                "issued_at": datetime.now().isoformat(),
            }

            payload_bytes = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
            signature = private_key.sign(payload_bytes)

            license_data = {
                "payload": payload,
                "signature": base64.b64encode(signature).decode('utf-8'),
            }

            with patch('core.license.LICENSE_PUBLIC_KEY_B64', test_pub_b64):
                success, msg = mgr.activate(json.dumps(license_data))
                assert success, f"Activation failed: {msg}"
                assert mgr.verify() == LicenseStatus.VALID

    def test_tampered_license(self):
        from core.license import LicenseManager, LicenseStatus
        private_key, test_pub_b64 = _generate_test_keypair()

        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = LicenseManager()
            mgr._license_dir = tmpdir
            mgr._license_path = os.path.join(tmpdir, "license.dat")

            machine_id = mgr.get_machine_id()
            expires = (datetime.now() + timedelta(days=365)).isoformat()

            payload = {
                "product": LICENSE_PRODUCT,
                "machine_id": machine_id,
                "licensee": "Test User",
                "expires_at": expires,
                "features": ["all"],
                "issued_at": datetime.now().isoformat(),
            }

            payload_bytes = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
            signature = private_key.sign(payload_bytes)

            license_data = {
                "payload": payload,
                "signature": base64.b64encode(signature).decode('utf-8'),
            }

            with patch('core.license.LICENSE_PUBLIC_KEY_B64', test_pub_b64):
                mgr.activate(json.dumps(license_data))

            with open(mgr._license_path, 'r+') as f:
                data = json.load(f)
                data['payload']['licensee'] = 'TAMPERED'
                f.seek(0)
                json.dump(data, f)
                f.truncate()

            with patch('core.license.LICENSE_PUBLIC_KEY_B64', test_pub_b64):
                assert mgr.verify() == LicenseStatus.TAMPERED

    def test_wrong_machine(self):
        from core.license import LicenseManager, LicenseStatus
        private_key, test_pub_b64 = _generate_test_keypair()

        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = LicenseManager()
            mgr._license_dir = tmpdir
            mgr._license_path = os.path.join(tmpdir, "license.dat")

            wrong_machine_id = "a" * 32
            expires = (datetime.now() + timedelta(days=365)).isoformat()

            payload = {
                "product": LICENSE_PRODUCT,
                "machine_id": wrong_machine_id,
                "licensee": "Test User",
                "expires_at": expires,
                "features": ["all"],
                "issued_at": datetime.now().isoformat(),
            }

            payload_bytes = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
            signature = private_key.sign(payload_bytes)

            license_data = {
                "payload": payload,
                "signature": base64.b64encode(signature).decode('utf-8'),
            }

            with patch('core.license.LICENSE_PUBLIC_KEY_B64', test_pub_b64):
                success, msg = mgr.activate(json.dumps(license_data))
                assert not success
                assert "机器指纹不匹配" in msg

    def test_expired_license(self):
        from core.license import LicenseManager, LicenseStatus
        private_key, test_pub_b64 = _generate_test_keypair()

        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = LicenseManager()
            mgr._license_dir = tmpdir
            mgr._license_path = os.path.join(tmpdir, "license.dat")

            machine_id = mgr.get_machine_id()
            expires = (datetime.now() - timedelta(days=1)).isoformat()

            payload = {
                "product": LICENSE_PRODUCT,
                "machine_id": machine_id,
                "licensee": "Test User",
                "expires_at": expires,
                "features": ["all"],
                "issued_at": datetime.now().isoformat(),
            }

            payload_bytes = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
            signature = private_key.sign(payload_bytes)

            license_data = {
                "payload": payload,
                "signature": base64.b64encode(signature).decode('utf-8'),
            }

            with patch('core.license.LICENSE_PUBLIC_KEY_B64', test_pub_b64):
                success, msg = mgr.activate(json.dumps(license_data))
                assert not success
                assert "过期" in msg


class TestAntiDebug:
    def test_no_crash(self):
        result = run_anti_debug_checks()
        assert isinstance(result, list)

    def test_returns_list(self):
        result = run_anti_debug_checks()
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, str)


class TestIntegrity:
    def test_compute_file_hash(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test content")
            f.flush()
            tmp_path = f.name

        try:
            h = compute_file_hash(tmp_path)
            assert len(h) == 64
            assert all(c in '0123456789abcdef' for c in h)
        finally:
            os.unlink(tmp_path)

    def test_compute_all_hashes(self):
        hashes = compute_all_hashes()
        assert isinstance(hashes, dict)
        assert len(hashes) > 0

    def test_verify_integrity(self):
        passed, issues = verify_integrity()
        assert isinstance(passed, bool)
        assert isinstance(issues, list)
