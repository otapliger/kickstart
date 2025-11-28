# kickstart

Automated Linux installer with encrypted BTRFS.

> **⚠️ MIGRATION IN PROGRESS**: Rewriting in Go. Python version in `legacy/`.

> **WARNING**: Destructive operation. Use `--dry` first.

## Supported

- Arch Linux
- Void Linux  

## Usage

```bash
# Legacy Python version
cd legacy && ./build.sh
./dist/kickstart --dry

# Go version (coming soon)
./kickstart --dry
```

## Options

```
-d, --dry              Preview mode
-p, --profile SOURCE   Profile (name, file, URL)
-k, --keymap KEYMAP    Keyboard layout
-t, --timezone TZ      Timezone
--hostname NAME        Hostname
--locale LOCALE        Locale
```

## What It Does

- LUKS1-encrypted BTRFS root
- EFI boot with GRUB
- Subvolumes: `@`, `@home`, `@snapshots`, `@var_cache`, `@var_log`
- GPU driver detection
- Profile customizations

## Safety

1. Use `--dry` first
2. Disconnect other drives
3. Verify target disk

## License

GPL-3.0
