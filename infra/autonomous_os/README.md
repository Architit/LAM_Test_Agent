# Autonomous OS Build Path (Bare Metal)

This path is for running the ecosystem as an autonomous Linux image (boot path: BIOS/UEFI -> bootloader -> LAM control plane), not as WSL-on-Windows.

## Goal
- One command on a fresh Linux build host to produce a bootable OS image.
- On target device, first boot auto-enables:
  - `lam-control-plane.service` (model delivery worker)
  - `lam-captain-tty.service` (Captain Bridge terminal on `tty1`)

## Scope
- Build host: native Linux with `systemd`, `apt`, `debootstrap`, `grub`, `qemu-img`.
- Target runtime: native Linux only.

## Fast path on already-installed native Linux
```bash
sudo scripts/autonomous_bootstrap.sh full --install-deps
```

## Bare-metal image path
1. Build image:
```bash
sudo scripts/build_autonomous_os_image.sh --output /tmp/lam-autonomous.img --size-gb 16
```
2. Flash image to device disk (example):
```bash
sudo dd if=/tmp/lam-autonomous.img of=/dev/sdX bs=16M status=progress conv=fsync
```
3. Boot device; services start automatically (if first-boot provisioning succeeds).

## Notes
- This repository includes the deployment scripts and service templates.
- Hardware/driver hardening, secure boot chain, and signed artifacts should be added for production rollout.

