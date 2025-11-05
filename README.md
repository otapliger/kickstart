# kickstart

Automated installer for Linux distributions with encrypted BTRFS and sensible defaults.

> **WARNING**: This installer is DESTRUCTIVE and will wipe the selected disk. Always use `--dry` first.

## Supported Distros

- **Void Linux**
- **Arch Linux** - ⚠️ installer not yet functional, work in progress

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
-t, --timezone TZ      System timezone
--hostname NAME        System hostname
--locale LOCALE        System locale
--libc LIBC            C library
--version              Show version
```

## Profiles

Profiles are JSON files that define installation configurations:

```bash
# Local profile
curl -fsSL https://otapliger.github.io/kickstart/bootstrap.sh | sh -- -p profiles/void/minimal.json

# Remote profile
curl -fsSL https://otapliger.github.io/kickstart/bootstrap.sh | sh -- -p https://example.com/profile.json
```

Example profile structure:

```json
{
  "name": "Minimal System",
  "description": "Bare minimum installation",
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
