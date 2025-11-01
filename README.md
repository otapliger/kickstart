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
- Service enablement: dbus, dhcpcd, elogind, ufw, grub-btrfs
- Firewall defaults (deny incoming, allow outgoing)
- PipeWire + WirePlumber sample configuration
- User creation (wheel groups) with `fish` shell; root shell switched to `bash`
- Strict, typed Python 3.12 code; zero external Python dependencies
- Dry run mode for full visibility (no commands executed / files written)
- Self-contained chroot provisioning script generation

## Usage & Safety

Dry run (recommended first):
```
python3 kickstart.py -d
```

Default install (DESTRUCTIVE after confirmation prompt):
```
sudo python3 kickstart.py
```

Dry run mode suppresses all state changes:
- Commands are printed prefixed with `[DRY RUN]`
- File writes are shown inline

Safety checklist:
1. Run a dry run.
2. Unplug or detach non-target disks if feasible.
3. Verify target disk string (e.g. `/dev/nvme0n1` vs `/dev/sda`).
4. Read the printed steps before committing.

## Configuration & CLI

Configuration lives in `config/void/`:
- `defaults.json` – baseline locale, timezone, libc, keymap, repository, NTP servers
- `pkgs.json` – essential development and productivity tools
- `mirrors.json` – mirror metadata

CLI options (`kickstart.py`):
- `-d, --dry` – Preview all steps only
- `-p, --profile <source>` – Load installation profile from local file or HTTP URL
- `--libc <glibc|musl>` – Select C library implementation
- `-r, --repository <URL>` – Override interactive mirror selection
- `-t, --timezone <Region/City>` – Set system timezone (e.g. `Europe/London`)
- `--locale <locale>` – System locale (e.g. `en_GB.UTF-8`, `C`, `POSIX`)
- `-k, --keymap <layout>` – Keyboard layout (e.g. `gb`, `us`)
- `--hostname <hostname>` – Set system hostname
- `--version` – Show installer version and exit

Invalid values abort early before any destructive action.

## Profile System

Installation profiles allow you to define reusable configurations in JSON format that can be loaded from local files or HTTP URLs.

### Profile Usage

Load a local profile:
```
sudo python3 kickstart.py -p ./profiles/desktop.json
```

Load a remote profile:
```
sudo python3 kickstart.py -p https://example.com/profiles/minimal.json
```

Common usage examples:
```
# Dry run with custom hostname and timezone
sudo python3 kickstart.py -d --hostname myserver -t America/New_York

# Install with musl libc and custom keymap
sudo python3 kickstart.py --libc musl -k colemak --hostname voidbox

# Use specific repository and profile
sudo python3 kickstart.py --repository https://mirrors.example.com/void -p ./custom.json
```

### Available Profiles

The installer includes several example profiles:
- `profiles/minimal.json` – Bare minimum system
- `profiles/niri.json` – Wayland with Niri compositor

## Architecture

Core components:
- `kickstart.py` orchestrates argument parsing, validation, step execution.
- `src/context.py` defines immutable `Config` + mutable `InstallerContext` state passed between steps.
- `src/steps.py` implements deterministic, ordered procedural steps.
- `src/utils.py` provides prompts, JSON loading, command/file helpers, mirror selection.
- `src/chroot.py` generates the audited provisioning script executed under chroot.
- `src/ansi_codes.py` and `src/ascii_art.py` provide terminal UX.

## License & Disclaimer

See the `LICENSE` file for license terms.

Disclaimer: This software is provided “as is.” Running a destructive installer entails risk. Back up data, confirm target disk, and perform a dry run before proceeding.
