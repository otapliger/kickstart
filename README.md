# kickstart

Automated installer for Linux distributions with encrypted BTRFS.

> **WARNING**: Destructive operation. Always use `--dry` first.

## Supported

- Void Linux
- Arch Linux

## Quick Start

```bash
# Preview installation
curl -fsSL https://plgr.tv/kickstart | sh -- --dry

# Install with profile
curl -fsSL https://plgr.tv/kickstart | sh -- -p niri

# Install with custom settings
curl -fsSL https://plgr.tv/kickstart | sh -- -k us -t America/Chicago
```

## Options

```
-d, --dry              Preview mode (no changes)
-p, --profile SOURCE   Profile: name, file path, or URL
-r, --repository URL   Override mirror
-k, --keymap KEYMAP    Keyboard layout
-t, --timezone TZ      Timezone
--hostname NAME        Hostname
--locale LOCALE        Locale
--libc LIBC            C library (void only)
--version              Show version
```

## Profiles

JSON files defining installation configuration. Can be embedded names, local files, or URLs.

```json
{
  "name": "Vim + Tmux",
  "description": "Replace helix with vim + tmux",
  "distro": "void",
  "config": {
    "libc": "glibc",
    "timezone": "Europe/London",
    "keymap": "uk",
    "locale": "en_GB.UTF-8"
  },
  "packages": {
    "additional": ["vim", "tmux"],
    "exclude": ["helix"]
  }
}
```

## What It Does

- Creates LUKS1-encrypted BTRFS root filesystem
- Sets up EFI boot with GRUB
- Configures subvolumes: `@`, `@home`, `@snapshots`, `@var_cache`, `@var_log`
- Installs curated packages with GPU driver detection
- Applies profile customizations

## Safety

1. Use `--dry` first
2. Disconnect other drives
3. Verify target disk
4. Review planned steps

## License

MIT. Use at your own risk.
