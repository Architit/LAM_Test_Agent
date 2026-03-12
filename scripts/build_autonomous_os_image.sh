#!/usr/bin/env bash
set -euo pipefail

# Minimal image builder for autonomous LAM OS (native Linux only).
# Produces a raw disk image with Debian base + repo sync + autopilot services.

OUTPUT="${OUTPUT:-/tmp/lam-autonomous.img}"
SIZE_GB="${SIZE_GB:-16}"
WORKDIR="${WORKDIR:-/tmp/lam-autonomous-build}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat <<'EOF'
Usage:
  sudo scripts/build_autonomous_os_image.sh [--output FILE] [--size-gb N] [--workdir DIR]

Build requirements:
  - debootstrap, qemu-img, parted, mkfs.ext4, mount, grub-install, rsync

Result:
  - bootable raw image with LAM control-plane bootstrap script in place.
EOF
}

die() {
  echo "[autonomous-image] $*" >&2
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
      -h|--help) usage; exit 0;;
      *) die "unknown arg: $1";;
    esac
  done
}

parse_args "$@"
require_root

for c in debootstrap qemu-img parted mkfs.ext4 mount umount losetup rsync chroot; do
  need_cmd "$c"
done

rm -rf "$WORKDIR"
mkdir -p "$WORKDIR"

IMG="$OUTPUT"
LOOP_DEV=""
ROOT_MNT="$WORKDIR/mnt"

cleanup() {
  set +e
  if mountpoint -q "$ROOT_MNT/proc"; then umount "$ROOT_MNT/proc"; fi
  if mountpoint -q "$ROOT_MNT/sys"; then umount "$ROOT_MNT/sys"; fi
  if mountpoint -q "$ROOT_MNT/dev"; then umount "$ROOT_MNT/dev"; fi
  if mountpoint -q "$ROOT_MNT"; then umount "$ROOT_MNT"; fi
  if [[ -n "$LOOP_DEV" ]]; then losetup -d "$LOOP_DEV"; fi
}
trap cleanup EXIT

qemu-img create -f raw "$IMG" "${SIZE_GB}G"

parted -s "$IMG" mklabel msdos
parted -s "$IMG" mkpart primary ext4 1MiB 100%

LOOP_DEV="$(losetup --show -fP "$IMG")"
mkfs.ext4 -F "${LOOP_DEV}p1"

mkdir -p "$ROOT_MNT"
mount "${LOOP_DEV}p1" "$ROOT_MNT"

debootstrap --variant=minbase bookworm "$ROOT_MNT" http://deb.debian.org/debian

mount --bind /dev "$ROOT_MNT/dev"
mount --bind /proc "$ROOT_MNT/proc"
mount --bind /sys "$ROOT_MNT/sys"

chroot "$ROOT_MNT" /bin/bash -lc "apt-get update && apt-get install -y systemd-sysv python3 python3-venv python3-pip rsync curl git"

mkdir -p "$ROOT_MNT/opt/lam"
rsync -a --delete --exclude='.git' --exclude='.venv' "$REPO_ROOT/" "$ROOT_MNT/opt/lam/"

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

if command -v grub-install >/dev/null 2>&1; then
  chroot "$ROOT_MNT" /bin/bash -lc "apt-get install -y grub-pc"
  grub-install --target=i386-pc --boot-directory="$ROOT_MNT/boot" "$LOOP_DEV" || true
  chroot "$ROOT_MNT" /bin/bash -lc "update-grub || true"
fi

echo "[autonomous-image] image ready: $IMG"
