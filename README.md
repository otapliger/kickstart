# kickstart

Automated installer for Linux distributions with encrypted BTRFS and sensible defaults.

> **WARNING**: This installer is DESTRUCTIVE and will wipe the selected disk. Always use `--dry` first.

## Supported Distros

- **Void Linux** (glibc/musl)
- **Arch Linux**

## Quick Start

```bash
# Preview installation (recommended)
python3 kickstart.py --dry

# Install with defaults
sudo python3 kickstart.py

# Custom configuration
sudo python3 kickstart.py --libc musl --keymap colemak

# Use a profile
sudo python3 kickstart.py -p ./profiles/void/minimal.json
```

## Interface

```
┌─────────────────────────────────────┐
│ Logo (ASCII Art)                    │ Fixed Header
│ DRY RUN MODE (if applicable)        │
│                                     │
│ [▓▓▓▓░░░░░░] Settings · Step 1/5    │ ← Status Bar
│                                     │
├─────────────────────────────────────┤
│                                     │ ↕
│ Skipping root and system checks...  │ │
│                                     │ │
│ • C library: glibc                  │ │
│ • Keymap: uk                        │ │
│ • Locale: en_GB.UTF-8               │ │
│ • Timezone: Europe/London           │ │ Scrolling
│                                     │ │ Content
│ Choose a hostname: linux            │ │
│                                     │ │
│ Disks:                              │ │
│   1. /dev/nvme0n1                   │ │
│   ...                               │ │
│                                     │ ↕
└─────────────────────────────────────┘
```

## Features

- **Encryption**: LUKS1-on-BTRFS root filesystem
- **Boot**: EFI with GRUB
- **Subvolumes**: `@`, `@home`, `@snapshots`, `@var_cache`, `@var_log`
- **Packages**: Curated selection with GPU driver detection
- **Profiles**: JSON-based configurations (local files or URLs)

## Options

```
-d, --dry              Preview mode (no changes)
-p, --profile SOURCE   Load profile from file or URL
-r, --repository URL   Override mirror selection
-k, --keymap KEYMAP    Keyboard layout
-t, --timezone TZ      System timezone (Region/City)
--hostname NAME        System hostname
--locale LOCALE        System locale
--libc LIBC            C library (glibc/musl)
--version              Show version
```

## Profiles

Profiles are JSON files that define installation configurations:

```bash
# Local profile
sudo python3 kickstart.py -p ./profiles/void/minimal.json

# Remote profile
sudo python3 kickstart.py -p https://example.com/profile.json
```

Example profile structure:

```json
{
  "name": "Minimal System",
  "description": "Bare minimum installation",
  "version": "1.0",
  "distro": "void",
  "config": {
    "libc": "glibc",
    "timezone": "Europe/London",
    "keymap": "uk",
    "locale": "en_GB.UTF-8"
  },
  "packages": {
    "additional": ["vim", "tmux"],
    "exclude": ["fish-shell"]
  }
}
```

## Configuration

The installer uses `config.json` for defaults, mirrors, and package lists per distro.

## Safety

1. Run dry mode first
2. Disconnect non-target drives
3. Verify target disk path
4. Review planned steps before proceeding

## License

See LICENSE file. Use at your own risk.
