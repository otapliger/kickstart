#!/usr/bin/env -S bash -e
PKGS="alacritty asciinema bash-completion bat bottom cmake elogind emacs-pgtk ffmpeg fish-shell fzf git httptap hunspell hunspell-en imv intel-media-driver jq mako meld mesa mesa-vulkan-intel nemo ninja niri noto-fonts-cjk noto-fonts-cjk-variable noto-fonts-emoji noto-fonts-ttf noto-fonts-ttf-variable openntpd papirus-folders papirus-icon-theme pipewire podman podman-tui python3 python3-devel qutebrowser rio ripgrep ruff rustup sv-helper starship swww tmux ufw vim vivaldi vulkan-loader wireplumber xdg-desktop-portal-gnome xdg-user-dirs xwayland-satellite yq-go yt-dlp zoxide"

mount --types efivarfs none /sys/firmware/efi/efivars

EFI_UUID=$(blkid --match-tag UUID --output value /dev/disk/by-partlabel/esp)

VOID_UUID=$(blkid --match-tag UUID --output value /dev/mapper/$HOSTNAME)

CRYPT_UUID=$(blkid --match-tag UUID --output value /dev/disk/by-partlabel/encrypted)

CMDLINE_DEFAULT=$(cat /etc/default/grub | grep GRUB_CMDLINE_LINUX_DEFAULT | sed 's/.*="\(.*\)"/\1/')

# Configure the system

chmod 755 /
chown root:root /
mkdir -p /opt /etc/pipewire/pipewire.conf.d

tee /etc/fstab &> /dev/null << EOF
tmpfs /tmp tmpfs defaults,nosuid,nodev 0 0
UUID=$VOID_UUID / btrfs $BTRFS_OPTS,subvol=@ 0 1
UUID=$VOID_UUID /.snapshots btrfs $BTRFS_OPTS,subvol=@snapshots 0 2
UUID=$VOID_UUID /var/cache btrfs $BTRFS_OPTS,subvol=@var_cache 0 2
UUID=$VOID_UUID /var/log btrfs $BTRFS_OPTS,subvol=@var_log 0 2
UUID=$VOID_UUID /home btrfs $BTRFS_OPTS,subvol=@home 0 2
UUID=$EFI_UUID /boot/efi vfat defaults 0 2
EOF

tee /etc/ntpd.conf &> /dev/null << EOF
server 0.fi.pool.ntp.org
server 1.fi.pool.ntp.org
server 2.fi.pool.ntp.org
server 3.fi.pool.ntp.org
EOF

tee /etc/rc.conf &> /dev/null << EOF
TIMEZONE="Europe/Helsinki"
HARDWARECLOCK="UTC"
KEYMAP=us
EOF

tee /etc/hosts &> /dev/null << EOF
127.0.0.1 localhost
::1 localhost
127.0.1.1 $HOSTNAME.localdomain $HOSTNAME
EOF

if [[ ! "$ARCH" == *"musl"* ]]; then
  tee /etc/default/libc-locales &> /dev/null << EOF
en_GB.UTF-8
en_US.UTF-8
C.UTF-8
EOF

  xbps-reconfigure -f glibc-locales

  tee /etc/locale.conf &> /dev/null << EOF
LANGUAGE=en_GB.UTF-8
LANG=en_GB.UTF-8
EOF
fi

tee /etc/xbps.d/10-ignore.conf &> /dev/null << EOF
ignorepkg=gnome-backgrounds
ignorepkg=mate-backgrounds
ignorepkg=plasma-workspace-wallpapers
EOF

tee /etc/sudoers &> /dev/null << EOF
Defaults secure_path="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Defaults env_keep += "SUDO_EDITOR EDITOR VISUAL"
root ALL=(ALL:ALL) ALL
%wheel ALL=(ALL:ALL) ALL
@includedir /etc/sudoers.d
EOF

echo "$HOSTNAME" > /etc/hostname
ln -sf /usr/share/zoneinfo/Europe/Helsinki /etc/localtime
hwclock --systohc

if [[ ! -z "$CMDLINE_DEFAULT" ]]; then
  CMDLINE_DEFAULT="$CMDLINE_DEFAULT rd.auto=1 rd.luks.name=$CRYPT_UUID=encrypted rd.luks.allow-discards=$CRYPT_UUID"
else
  CMDLINE_DEFAULT="rd.auto=1 rd.luks.name=$CRYPT_UUID=encrypted rd.luks.allow-discards=$CRYPT_UUID"
fi

echo "GRUB_ENABLE_CRYPTODISK=y" >> /etc/default/grub
sed -i "s/GRUB_CMDLINE_LINUX_DEFAULT.*/GRUB_CMDLINE_LINUX_DEFAULT=\"$CMDLINE_DEFAULT\"/" /etc/default/grub

dd bs=512 count=4 if=/dev/urandom of=/boot/encrypted.key
echo $LUKSPASS | cryptsetup luksAddKey /dev/disk/by-partlabel/encrypted /boot/encrypted.key &> /dev/null
echo "encrypted UUID=$CRYPT_UUID /boot/encrypted.key luks" > /etc/crypttab
chmod 000 /boot/encrypted.key
chmod -R g-rwx,o-rwx /boot

tee /etc/dracut.conf.d/00-hostonly.conf &> /dev/null << EOF
hostonly_cmdline=yes
hostonly=yes
EOF

tee /etc/dracut.conf.d/10-crypt.conf &> /dev/null << EOF
install_items+=" /boot/encrypted.key /etc/crypttab "
EOF

tee /etc/dracut.conf.d/20-modules.conf &> /dev/null << EOF
add_dracutmodules+=" crypt btrfs resume "
EOF

tee /etc/dracut.conf.d/30-tmpfs.conf &> /dev/null << EOF
tmpdir=/tmp
EOF

# Install bootloader

grub-install --target=x86_64-efi --boot-directory=/boot --efi-directory=/boot/efi --bootloader-id=Void --recheck

# Install packages

xi && yes | xbps-install -USy --repository "$REPO" $PKGS

# Ensure all installed packages are configured properly

xbps-reconfigure --force --all

# Enable services

ln -srf /etc/sv/{dbus,elogind,grub-btrfs,NetworkManager,openntpd,ufw} /var/service/

# Set audio

ln -s /usr/share/examples/wireplumber/10-wireplumber.conf /etc/pipewire/pipewire.conf.d/
ln -s /usr/share/examples/pipewire/20-pipewire-pulse.conf /etc/pipewire/pipewire.conf.d/

# Set firewall
ufw default deny incoming
ufw default allow outgoing

# Set users

chsh --shell /bin/bash root
useradd --create-home --groups wheel,users,input,audio,video,network --shell /bin/fish $USERNAME

USERHOME=/home/$USERNAME
sudo -u $USERNAME mkdir -p $USERHOME/{.local/share/{fonts,icons,themes},stuff}
