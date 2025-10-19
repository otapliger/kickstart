# void.kickstart

A user-friendly, automated installer for Void Linux that provisions an encrypted BTRFS-based minimal system with sensible defaults and a curated package set. It eliminates repetitive manual steps while keeping everything auditable and lean.

> WARNING: This installer is DESTRUCTIVE. It will wipe the selected disk entirely. Always run with `--dry` first and verify the target device.

## Overview & Features

`void.kickstart` performs an opinionated baseline installation:

- Fully encrypted LUKS1-on-BTRFS root (compatibility focused)
- EFI boot with GRUB configured for cryptodisk + BTRFS
- Structured subvolumes: `@`, `@home`, `@snapshots`, `@var_cache`, `@var_log`
- Locale, keymap, timezone, libc selection
- Interactive mirror selection or explicit repository override
- Base bootstrap + extended curated packages
- Service enablement: dbus, elogind, NetworkManager, openntpd, ufw, grub-btrfs
- Firewall defaults (deny incoming, allow outgoing)
- PipeWire + WirePlumber sample configuration
- User creation (wheel groups) with `fish` shell; root shell switched to `bash`
- Strict, typed Python 3.12 code; zero external Python dependencies
- Dry run mode for full visibility (no commands executed / files written)
- Self-contained chroot provisioning script generation

## Usage & Safety

Dry run (recommended first):
```
python3.12 main.py --dry
```

Default install (DESTRUCTIVE after confirmation prompt):
```
sudo python3.12 main.py
```

Common customizations:
```
sudo python3.12 main.py --timezone Europe/Helsinki --keymap us --libc musl
sudo python3.12 main.py --repository https://repo-fi.voidlinux.org/current
python3.12 main.py --version
```

Dry run mode suppresses all state changes:
- Commands are printed prefixed with `[DRY RUN]`
- File writes are shown inline

Safety checklist:
1. Run a dry run.
2. Unplug or detach non-target disks if feasible.
3. Verify target disk string (e.g. `/dev/nvme0n1` vs `/dev/sda`).
4. Read the printed steps before committing.

## Installation Flow

1. Settings Collection
   - Prompts: hostname, disk, encryption password, user + password, repository/mirror.
   - Confirms destructive action.
   - Derives paths (`cryptroot`, `esp`, `root`).
2. Disk Setup
   - Wipes signatures (`wipefs -af`) & resets GPT (`sgdisk -Zo`).
   - Creates ESP + encrypted partition (GPT `parted`).
   - Formats ESP (`mkfs.vfat`).
   - Initializes & opens LUKS container.
   - Creates BTRFS filesystem, mounts, creates subvolumes, remounts layout.
3. System Bootstrap
   - Copies xbps keys.
   - Installs base packages from `config/void/base.json`.
4. System Installation & Configuration
   - Writes `/etc/fstab`, host/network/time/locale/sudo configs.
   - Configures locales (glibc path when selected).
   - Generates chroot script that: installs packages, configures GRUB, enables services, sets firewall, sets up audio, creates user, fetches Neovim nightly.
   - Executes chroot script and sets passwords.
5. Cleanup
   - Removes temporary chroot script; unmounts `/mnt` recursively; prints success message.

## Configuration & CLI

Configuration lives in `config/void/`:
- `defaults.json` – baseline locale, timezone, libc, keymap, repository, NTP servers
- `mirrors.json` – mirror metadata
- `base.json` – minimal base package set
- `pkgs.json` – extended curated packages (GUI, dev tools, multimedia, productivity)

CLI options (`main.py`):
- `--dry` – Preview all steps only
- `--libc <glibc|musl>` – Select C library implementation
- `--repository <URL>` – Override interactive mirror selection
- `--timezone <Region/City>` – Set system timezone (e.g. `Europe/London`)
- `--keymap <layout>` – Keyboard layout (e.g. `gb`, `us`)
- `--locale <locale>` – System locale (e.g. `en_GB.UTF-8`, `C`, `POSIX`)
- `--version` – Show installer version and exit

Invalid values abort early before any destructive action.

## Architecture

Core components:
- `main.py` orchestrates argument parsing, validation, step execution.
- `src/context.py` defines immutable `Config` + mutable `InstallerContext` state passed between steps.
- `src/steps.py` implements deterministic, ordered procedural steps.
- `src/utils.py` provides prompts, JSON loading, command/file helpers, mirror selection.
- `src/chroot.py` generates the audited provisioning script executed under chroot.
- `src/ansi_codes.py` and `src/ascii_art.py` provide terminal UX.

Design pattern: a linear pipeline with an explicit context object, no hidden globals, enabling clarity, testability, and future extension.

## Design & Principles

Guiding principles:
- Clarity: Every command and file write is visible (especially in dry run).
- Minimalism: Only foundational components; avoids surplus packages.
- Extensibility: Behavior driven by JSON; new steps can be appended.
- Auditability: Generated chroot script makes privileged operations inspectable.
- Compatibility: LUKS1 chosen for broad bootloader support.
- Type Safety: Strict typing reduces accidental regressions.

Key choices:
- BTRFS subvolumes for logical data separation & future snapshot tooling.
- GRUB for reliable encrypted boot workflow.
- Externalized configuration rather than hardcoded logic.

## Extensibility & Development

Enhancements you could add:
- Snapshot tooling integration (e.g. snapper).
- Alternative bootloaders.
- Multiple partition scheme selection.
- Install transcript logging.
- Internationalized prompts.

Development workflow:
- Use `ruff` for formatting & lint (`ruff check .`, `ruff format .`).
- Rely on strict typing (basedpyright config in `pyproject.toml`).
- Perform dry runs to validate logic before destructive tests.
- Corrupt JSON intentionally to test validation/error paths.
- (Future) Use loopback devices for automated disk tests.

## Troubleshooting & Security

Package fetch stalls:
- Test connectivity (`ping voidlinux.org`).
- Try a different repository (`--repository <URL>`).

Locale not applied:
- Confirm locale exists in glibc locale database.
- Re-run `xbps-reconfigure -f glibc-locales -r /mnt`.

General issues:
- Inspect dry run output for exact commands.
- Review generated chroot script for misconfiguration.

Security considerations:
- Passwords captured via `getpass` (no echo).
- LUKS password passed by piped echo (appears briefly in process list); could be hardened via temp key file descriptor.
- Basic firewall defaults applied (deny incoming, allow outgoing).
- External artifacts fetched over HTTPS without signature verification.
- Enabled services limited; audit `/var/service/` symlinks.

## License & Disclaimer

See the `LICENSE` file for license terms.

Disclaimer: This software is provided “as is.” Running a destructive installer entails risk. Back up data, confirm target disk, and perform a dry run before proceeding.
