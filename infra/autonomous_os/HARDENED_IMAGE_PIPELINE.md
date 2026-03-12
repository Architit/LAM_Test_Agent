# Hardened Image Pipeline (1+2+3)

This pipeline adds:
1. UEFI/GPT hardened boot image build.
2. Secure Boot signing path (optional, key-driven).
3. Recovery/rollback + OTA bundle preparation.

## 1) Hardened Image Build
```bash
sudo scripts/build_autonomous_os_image_hardened.sh \
  --output /tmp/lam-autonomous-hardened.img \
  --size-gb 24
```

Layout:
- `p1` EFI (`FAT32`)
- `p2` root (`ext4`, mounted `ro`)
- `p3` recovery (`ext4`)

Artifacts:
- image: `/tmp/lam-autonomous-hardened.img`
- checksum: `/tmp/lam-autonomous-hardened.img.sha256`
- rollback manifest in recovery partition.

## 2) Secure Boot Signing (optional)
```bash
sudo scripts/build_autonomous_os_image_hardened.sh \
  --output /tmp/lam-autonomous-hardened.img \
  --secure-boot-sign \
  --sb-key /path/to/db.key \
  --sb-cert /path/to/db.crt
```

Notes:
- Requires `sbsign` and key material.
- For full chain security, enroll keys in firmware/MOK workflow.

## 3) Recovery + OTA
Prepare OTA bundle:
```bash
scripts/prepare_ota_bundle.sh \
  --image /tmp/lam-autonomous-hardened.img \
  --channel stable \
  --version 2026.03.07
```

Recovery control on target:
```bash
sudo scripts/recovery_switch.sh request
sudo scripts/recovery_switch.sh reboot
```

## Operational Notes
- This is a hardened baseline, not a full immutable distro.
- For production: add measured boot/TPM attestations, signed OTA metadata,
  and A/B partition strategy with atomic switch.

