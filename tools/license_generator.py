"""
离线 License 签发工具 — 开发者用，含私钥
"""
import json
import os
import sys
import base64
import hashlib
import argparse
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

from core.license_keys import LICENSE_PRODUCT


def load_private_key(key_path: str):
    """加载 Ed25519 私钥"""
    if not HAS_CRYPTOGRAPHY:
        raise ImportError("需要安装 cryptography 库: pip install cryptography")

    with open(key_path, 'rb') as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)

    if not isinstance(private_key, Ed25519PrivateKey):
        raise TypeError("必须是 Ed25519 私钥")

    return private_key


def generate_license(private_key_path: str, machine_id: str, licensee: str,
                     expires_at: datetime, features: list) -> str:
    """生成签名的 license"""
    if not HAS_CRYPTOGRAPHY:
        raise ImportError("需要安装 cryptography 库: pip install cryptography")

    private_key = load_private_key(private_key_path)

    payload = {
        "product": LICENSE_PRODUCT,
        "machine_id": machine_id,
        "licensee": licensee,
        "expires_at": expires_at.isoformat(),
        "features": features,
        "issued_at": datetime.now().isoformat(),
    }

    payload_bytes = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
    signature = private_key.sign(payload_bytes)

    license_data = {
        "payload": payload,
        "signature": base64.b64encode(signature).decode('utf-8'),
    }

    return json.dumps(license_data, indent=2, ensure_ascii=False)


def get_machine_id_from_file() -> str:
    """从目标机器获取 machine_id"""
    from core.license import LicenseManager
    return LicenseManager.get_machine_id()


def generate_key_pair(output_dir: str):
    """生成新的 Ed25519 密钥对"""
    if not HAS_CRYPTOGRAPHY:
        raise ImportError("需要安装 cryptography 库: pip install cryptography")

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    public_b64 = base64.b64encode(public_bytes).decode('utf-8')

    os.makedirs(output_dir, exist_ok=True)

    private_key_path = os.path.join(output_dir, "private_key.pem")
    with open(private_key_path, 'wb') as f:
        f.write(private_pem)

    print(f"私钥已保存: {private_key_path}")
    print(f"公钥 (Base64): {public_b64}")
    print(f"请将公钥更新到 core/license_keys.py 的 LICENSE_PUBLIC_KEY_B64")

    return private_key_path, public_b64


def main():
    """CLI 交互式签发"""
    parser = argparse.ArgumentParser(description="QA-Tool License 签发工具")
    parser.add_argument('--genkey', action='store_true', help="生成新的密钥对")
    parser.add_argument('--keydir', default='.', help="密钥输出目录 (配合 --genkey)")
    parser.add_argument('--mid', help="目标机器 ID")
    parser.add_argument('--licensee', help="被许可方名称")
    parser.add_argument('--expires', help="过期日期 (YYYY-MM-DD)")
    parser.add_argument('--features', nargs='+', default=['all'], help="功能列表")
    parser.add_argument('--private-key', default='private_key.pem', help="私钥文件路径")
    parser.add_argument('--output', help="输出 license 文件路径")
    parser.add_argument('--get-mid', action='store_true', help="获取当前机器 ID")

    args = parser.parse_args()

    if args.genkey:
        generate_key_pair(args.keydir)
        return

    if args.get_mid:
        mid = get_machine_id_from_file()
        print(f"Machine ID: {mid}")
        return

    if not all([args.mid, args.licensee, args.expires]):
        parser.error("签发 license 需要: --mid, --licensee, --expires")

    try:
        expires_at = datetime.strptime(args.expires, '%Y-%m-%d')
    except ValueError:
        parser.error("日期格式错误，应为 YYYY-MM-DD")

    if not os.path.exists(args.private_key):
        parser.error(f"私钥文件不存在: {args.private_key}")

    license_text = generate_license(
        private_key_path=args.private_key,
        machine_id=args.mid,
        licensee=args.licensee,
        expires_at=expires_at,
        features=args.features,
    )

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(license_text)
        print(f"License 已保存到: {args.output}")
    else:
        print(license_text)


if __name__ == "__main__":
    main()
