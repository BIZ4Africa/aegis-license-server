#!/usr/bin/env python3
"""
AEGIS License Server - Key Generation Script

Generates an Ed25519 keypair for license signing.
Usage: python scripts/generate_keys.py [--key-id aegis-2026-01]
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import from server
sys.path.insert(0, str(Path(__file__).parent.parent))

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization


def generate_keypair(key_id: str, output_dir: str = "keys"):
    """
    Generate an Ed25519 keypair and save to PEM files.
    
    Args:
        key_id: Unique identifier for this key (e.g., 'aegis-2026-01')
        output_dir: Directory to save keys (default: keys/)
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)
    
    # Generate private key
    print(f"🔐 Generating Ed25519 keypair (ID: {key_id})...")
    private_key = ed25519.Ed25519PrivateKey.generate()
    
    # Derive public key
    public_key = private_key.public_key()
    
    # Serialize private key (PEM format, no encryption)
    # WARNING: In production, encrypt with a passphrase!
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # Serialize public key (PEM format)
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    # Define file paths
    private_key_path = output_path / f"{key_id}.private.pem"
    public_key_path = output_path / f"{key_id}.public.pem"
    
    # Save private key
    with open(private_key_path, "wb") as f:
        f.write(private_pem)
    os.chmod(private_key_path, 0o600)  # Read/write for owner only
    
    # Save public key
    with open(public_key_path, "wb") as f:
        f.write(public_pem)
    os.chmod(public_key_path, 0o644)  # Readable by all
    
    # Generate metadata file
    metadata = f"""# AEGIS Key Metadata
Key ID: {key_id}
Algorithm: Ed25519 (EdDSA)
Generated: {datetime.utcnow().isoformat()}Z
Private Key: {private_key_path}
Public Key: {public_key_path}

⚠️  SECURITY NOTES:
- Keep the private key SECRET and SECURE
- The private key is NOT encrypted in this version
- In production, use a KMS or encrypt with a strong passphrase
- Backup both keys securely (encrypted backup recommended)
- Public key should be embedded in Odoo client modules

Public Key Size: {len(public_pem)} bytes
Private Key Size: {len(private_pem)} bytes
"""
    
    metadata_path = output_path / f"{key_id}.metadata.txt"
    with open(metadata_path, "w") as f:
        f.write(metadata)
    
    # Print summary
    print(f"✅ Keypair generated successfully!")
    print(f"   Private key: {private_key_path} ({len(private_pem)} bytes)")
    print(f"   Public key:  {public_key_path} ({len(public_pem)} bytes)")
    print(f"   Metadata:    {metadata_path}")
    print(f"\n🔒 Private key permissions: 0600 (owner read/write only)")
    print(f"📖 Public key permissions:  0644 (world readable)")
    print("\n" + "="*60)
    print("⚠️  IMPORTANT: Backup your private key securely!")
    print("="*60)
    
    return str(private_key_path), str(public_key_path)


def main():
    parser = argparse.ArgumentParser(
        description="Generate Ed25519 keypair for AEGIS license signing"
    )
    parser.add_argument(
        "--key-id",
        default=f"aegis-{datetime.now().year}-01",
        help="Key identifier (default: aegis-YYYY-01)"
    )
    parser.add_argument(
        "--output-dir",
        default="keys",
        help="Output directory for keys (default: keys/)"
    )
    
    args = parser.parse_args()
    
    generate_keypair(args.key_id, args.output_dir)


if __name__ == "__main__":
    main()
