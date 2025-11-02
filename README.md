# kickstart

Automated installer for supported Linux distros with encrypted BTRFS and sensible defaults.

> **WARNING**: This installer is DESTRUCTIVE and will wipe the selected disk. Always use `--dry` first.

## Features

- Encrypted LUKS1-on-BTRFS root filesystem
- EFI boot with GRUB
- BTRFS subvolumes: `@`, `@home`, `@snapshots`, `@var_cache`, `@var_log`
- Curated package selection
- User creation with proper groups and shell setup

## Usage

**Dry run first (recommended):**
```bash
python3 kickstart.py -d
```

**Install:**
```bash
sudo python3 kickstart.py
```

## Options

- `-d, --dry` – Preview mode (no changes made)
- `-p, --profile <SOURCE>` – Load profile from local file or HTTP URL
- `--libc <LIBC>` – C library implementation (glibc or musl)
- `-r, --repository <URL>` – Override mirror selection with specific repository URL
- `-t, --timezone <TIMEZONE>` – System timezone in Region/City format
- `--locale <LOCALE>` – System locale
- `-k, --keymap <KEYMAP>` – Keyboard layout
- `--hostname <HOSTNAME>` – System hostname
- `--version` – Show version and exit

## Profiles

Load configurations from local files or URLs:
```bash
sudo python3 kickstart.py -p ./profiles/minimal.json
sudo python3 kickstart.py -p https://example.com/profile.json
```

## Configuration

- `config/void/defaults.json` – System defaults
- `config/void/pkgs.json` – Package lists
- `config/void/mirrors.json` – Mirror information

## Safety

1. Run dry mode first
2. Disconnect non-target drives
3. Verify target disk path
4. Review planned steps before proceeding

## License

See LICENSE file. Use at your own risk.
