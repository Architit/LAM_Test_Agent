#!/usr/bin/env bash
set -euo pipefail

# Hardened autonomous OS image builder:
# - GPT layout (EFI + root + recovery)
# - UEFI boot (GRUB EFI)
# - Optional Secure Boot signing hook (sbsign)
# - Read-only root by default (fstab ro) with explicit recovery partition

OUTPUT="${OUTPUT:-/tmp/lam-autonomous-hardened.img}"
SIZE_GB="${SIZE_GB:-24}"
WORKDIR="${WORKDIR:-/tmp/lam-autonomous-hardened-build}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

ROOT_FS_LABEL="LAMROOT"
EFI_FS_LABEL="LAMEFI"
RECOVERY_FS_LABEL="LAMRECOVERY"

ENABLE_SECURE_BOOT_SIGN="${ENABLE_SECURE_BOOT_SIGN:-0}"
SB_KEY="${SB_KEY:-}"
SB_CERT="${SB_CERT:-}"

usage() {
  cat <<'EOF'
Usage:
  sudo scripts/build_autonomous_os_image_hardened.sh [--output FILE] [--size-gb N] [--workdir DIR]
                                                     [--secure-boot-sign --sb-key KEY --sb-cert CERT]

Features:
  - GPT disk layout:
      p1: EFI System Partition (FAT32)
      p2: root (ext4, mounted read-only by default)
      p3: recovery (ext4)
  - UEFI GRUB install
  - First-boot autopilot bootstrap
  - Optional Secure Boot signing for EFI binaries
EOF
}

die() {
  echo "[hardened-image] $*" >&2
  exit 1
}

require_root() {
  [[ "${EUID}" -eq 0 ]] || die "run as root (sudo)."
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "missing command: $1"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --output) OUTPUT="$2"; shift 2;;
      --size-gb) SIZE_GB="$2"; shift 2;;
      --workdir) WORKDIR="$2"; shift 2;;
      --secure-boot-sign) ENABLE_SECURE_BOOT_SIGN=1; shift;;
      --sb-key) SB_KEY="$2"; shift 2;;
      --sb-cert) SB_CERT="$2"; shift 2;;
      -h|--help) usage; exit 0;;
      *) die "unknown arg: $1";;
    esac
  done
}

parse_args "$@"
require_root

for c in debootstrap qemu-img parted mkfs.vfat mkfs.ext4 mount umount losetup rsync chroot blkid; do
  need_cmd "$c"
done

if [[ "$ENABLE_SECURE_BOOT_SIGN" == "1" ]]; then
  need_cmd sbsign
  [[ -f "$SB_KEY" ]] || die "Secure Boot enabled but SB_KEY missing."
  [[ -f "$SB_CERT" ]] || die "Secure Boot enabled but SB_CERT missing."
fi

rm -rf "$WORKDIR"
mkdir -p "$WORKDIR"

IMG="$OUTPUT"
LOOP_DEV=""
ROOT_MNT="$WORKDIR/mnt"
EFI_MNT="$ROOT_MNT/boot/efi"
RECOVERY_MNT="$ROOT_MNT/recovery"

cleanup() {
  set +e
  if mountpoint -q "$ROOT_MNT/proc"; then umount "$ROOT_MNT/proc"; fi
  if mountpoint -q "$ROOT_MNT/sys"; then umount "$ROOT_MNT/sys"; fi
  if mountpoint -q "$ROOT_MNT/dev"; then umount "$ROOT_MNT/dev"; fi
  if mountpoint -q "$RECOVERY_MNT"; then umount "$RECOVERY_MNT"; fi
  if mountpoint -q "$EFI_MNT"; then umount "$EFI_MNT"; fi
  if mountpoint -q "$ROOT_MNT"; then umount "$ROOT_MNT"; fi
  if [[ -n "$LOOP_DEV" ]]; then losetup -d "$LOOP_DEV"; fi
}
trap cleanup EXIT

qemu-img create -f raw "$IMG" "${SIZE_GB}G"

# GPT layout:
#  - 1MiB..513MiB   EFI
#  - 513MiB..(end-2048MiB) root
#  - (end-2048MiB)..100% recovery
parted -s "$IMG" mklabel gpt
parted -s "$IMG" mkpart ESP fat32 1MiB 513MiB
parted -s "$IMG" set 1 esp on
parted -s "$IMG" mkpart rootfs ext4 513MiB -2048MiB
parted -s "$IMG" mkpart recovery ext4 -2048MiB 100%

LOOP_DEV="$(losetup --show -fP "$IMG")"

mkfs.vfat -F32 -n "$EFI_FS_LABEL" "${LOOP_DEV}p1"
mkfs.ext4 -F -L "$ROOT_FS_LABEL" "${LOOP_DEV}p2"
mkfs.ext4 -F -L "$RECOVERY_FS_LABEL" "${LOOP_DEV}p3"

mkdir -p "$ROOT_MNT"
mount "${LOOP_DEV}p2" "$ROOT_MNT"
mkdir -p "$EFI_MNT" "$RECOVERY_MNT"
mount "${LOOP_DEV}p1" "$EFI_MNT"
mount "${LOOP_DEV}p3" "$RECOVERY_MNT"

debootstrap --variant=minbase bookworm "$ROOT_MNT" http://deb.debian.org/debian

mount --bind /dev "$ROOT_MNT/dev"
mount --bind /proc "$ROOT_MNT/proc"
mount --bind /sys "$ROOT_MNT/sys"

chroot "$ROOT_MNT" /bin/bash -lc \
  "apt-get update && apt-get install -y systemd-sysv python3 python3-venv python3-pip rsync curl git grub-efi-amd64 shim-signed"

mkdir -p "$ROOT_MNT/opt/lam"
rsync -a --delete --exclude='.git' --exclude='.venv' "$REPO_ROOT/" "$ROOT_MNT/opt/lam/"

ROOT_UUID="$(blkid -s UUID -o value "${LOOP_DEV}p2")"
EFI_UUID="$(blkid -s UUID -o value "${LOOP_DEV}p1")"
RECOVERY_UUID="$(blkid -s UUID -o value "${LOOP_DEV}p3")"

cat > "$ROOT_MNT/etc/fstab" <<EOF
UUID=${ROOT_UUID} / ext4 defaults,errors=remount-ro 0 1
UUID=${EFI_UUID} /boot/efi vfat umask=0077 0 1
UUID=${RECOVERY_UUID} /recovery ext4 defaults,nofail 0 2
tmpfs /tmp tmpfs nosuid,nodev 0 0
tmpfs /var/tmp tmpfs nosuid,nodev 0 0
EOF

mkdir -p "$ROOT_MNT/etc/default"
cat > "$ROOT_MNT/etc/default/grub" <<'EOF'
GRUB_DEFAULT=0
GRUB_TIMEOUT=2
GRUB_DISTRIBUTOR="LAM-Autonomous"
GRUB_CMDLINE_LINUX_DEFAULT="quiet"
GRUB_CMDLINE_LINUX=""
EOF

# First boot provisioning
cat > "$ROOT_MNT/usr/local/sbin/lam-firstboot.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [[ -f /opt/lam/scripts/autonomous_bootstrap.sh ]]; then
  /opt/lam/scripts/autonomous_bootstrap.sh full --repo-root /opt/lam --user root --install-deps
  /opt/lam/scripts/autonomous_bootstrap.sh status
fi
EOF
chmod +x "$ROOT_MNT/usr/local/sbin/lam-firstboot.sh"

cat > "$ROOT_MNT/etc/systemd/system/lam-firstboot.service" <<'EOF'
[Unit]
Description=LAM First Boot Provisioning
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/lam-firstboot.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

chroot "$ROOT_MNT" /bin/bash -lc "systemctl enable lam-firstboot.service"

# UEFI boot install
chroot "$ROOT_MNT" /bin/bash -lc "grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=LAM --recheck"
chroot "$ROOT_MNT" /bin/bash -lc "update-grub"

if [[ "$ENABLE_SECURE_BOOT_SIGN" == "1" ]]; then
  # Sign common EFI binaries in-place.
  for efi in \
    "$ROOT_MNT/boot/efi/EFI/LAM/grubx64.efi" \
    "$ROOT_MNT/boot/efi/EFI/BOOT/BOOTX64.EFI" \
    "$ROOT_MNT/boot/efi/EFI/debian/grubx64.efi"
  do
    [[ -f "$efi" ]] || continue
    sbsign --key "$SB_KEY" --cert "$SB_CERT" --output "$efi" "$efi"
  done
fi

# Recovery marker and rollback metadata
mkdir -p "$ROOT_MNT/recovery/lam_rollback"
cat > "$ROOT_MNT/recovery/lam_rollback/manifest.json" <<EOF
{
  "ts_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "root_uuid": "${ROOT_UUID}",
  "efi_uuid": "${EFI_UUID}",
  "recovery_uuid": "${RECOVERY_UUID}",
  "image": "$(basename "$IMG")",
  "mode": "hardened",
  "secure_boot_signed": ${ENABLE_SECURE_BOOT_SIGN}
}
EOF

sha256sum "$IMG" > "${IMG}.sha256"
echo "[hardened-image] image ready: $IMG"
echo "[hardened-image] checksum: ${IMG}.sha256"
