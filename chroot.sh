#!/usr/bin/env -S bash -e
mount --types efivarfs none /sys/firmware/efi/efivars

EFI_UUID=$(blkid --match-tag UUID --output value /dev/disk/by-partlabel/ESP)
VOID_UUID=$(blkid --match-tag UUID --output value /dev/mapper/$HOSTNAME)
CRYPT_UUID=$(blkid --match-tag UUID --output value /dev/disk/by-partlabel/ENCRYPTED)

# Configure the system

chmod 755 /
chown root:root /
mkdir -p /opt /etc/pipewire/pipewire.conf.d

# TIMEZONE, HWCLOCK, KEYMAP
tee /etc/rc.conf &> /dev/null << EOF
TIMEZONE="Europe/Helsinki"
HARDWARECLOCK="UTC"
KEYMAP=us
EOF

ln -sf /usr/share/zoneinfo/Europe/Helsinki /etc/localtime
hwclock --systohc

# LOCALES
if [[ ! "$ARCH" == *"musl"* ]]; then
  tee /etc/default/libc-locales &> /dev/null << EOF
en_GB.UTF-8
en_US.UTF-8
C.UTF-8
EOF

  xbps-reconfigure -f glibc-locales

  tee /etc/locale.conf &> /dev/null << EOF
export LANG=en_GB.UTF-8
export LANGUAGE=en_GB.UTF-8
export LC_ALL=en_GB.UTF-8
EOF
fi

# NETWORK
tee /etc/hosts &> /dev/null << EOF
127.0.0.1 localhost
::1 localhost
127.0.1.1 $HOSTNAME
EOF

echo "$HOSTNAME" > /etc/hostname

# NTP
tee /etc/ntpd.conf &> /dev/null << EOF
server 0.fi.pool.ntp.org
server 1.fi.pool.ntp.org
server 2.fi.pool.ntp.org
server 3.fi.pool.ntp.org
EOF

# FSTAB
tee /etc/fstab &> /dev/null << EOF
tmpfs /tmp tmpfs defaults,nosuid,nodev 0 0
UUID=$VOID_UUID / btrfs $BTRFS_OPTS,subvol=@ 0 1
UUID=$VOID_UUID /.snapshots btrfs $BTRFS_OPTS,subvol=@snapshots 0 2
UUID=$VOID_UUID /var/cache btrfs $BTRFS_OPTS,subvol=@var_cache 0 2
UUID=$VOID_UUID /var/log btrfs $BTRFS_OPTS,subvol=@var_log 0 2
UUID=$VOID_UUID /home btrfs $BTRFS_OPTS,subvol=@home 0 2
UUID=$EFI_UUID /boot/efi vfat defaults 0 2
EOF

# SUDOERS
tee /etc/sudoers &> /dev/null << EOF
Defaults secure_path="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Defaults env_keep += "SUDO_EDITOR EDITOR VISUAL"
root ALL=(ALL:ALL) ALL
%wheel ALL=(ALL:ALL) ALL
@includedir /etc/sudoers.d
EOF

# GRUB, ENCRYPTION, DRACUT
tee /etc/default/grub &> /dev/null << EOF
GRUB_CMDLINE_LINUX_DEFAULT="quiet rd.auto=1 rd.luks.name=$CRYPT_UUID=ENCRYPTED rd.luks.allow-discards=$CRYPT_UUID"
GRUB_CMDLINE_LINUX=""
GRUB_DEFAULT=0
GRUB_DISTRIBUTOR=Void
GRUB_ENABLE_CRYPTODISK=yes
GRUB_TIMEOUT=10
EOF

dd bs=512 count=4 if=/dev/urandom of=/boot/encrypted.key
echo $LUKSPASS | cryptsetup luksAddKey /dev/disk/by-partlabel/ENCRYPTED /boot/encrypted.key &> /dev/null
echo "ENCRYPTED UUID=$CRYPT_UUID /boot/encrypted.key luks" > /etc/crypttab
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

# XBPS
tee /etc/xbps.d/10-ignore.conf &> /dev/null << EOF
ignorepkg=gnome-backgrounds
ignorepkg=mate-backgrounds
ignorepkg=plasma-workspace-wallpapers
EOF

tee /etc/xbps.d/20-librewolf.conf &> /dev/null << EOF
repository=https://github.com/index-0/librewolf-void/releases/latest/download/
EOF

# Install bootloader

grub-install --target=x86_64-efi --boot-directory=/boot --efi-directory=/boot/efi --bootloader-id=Void --recheck

# Install packages

yes | xi && yes | xargs -a pkgs xbps-install -USy --repository "$REPO"

# VSCODE
TMP_NVIM=$(mktemp)
curl -sSLo "${TMP_NVIM}" https://github.com/neovim/neovim/releases/download/nightly/nvim-linux-x86_64.tar.gz
tar -C /opt -xzf "${TMP_NVIM}" && ln -sf /opt/nvim-linux-x86_64/bin/nvim /usr/bin/nvim && rm -rf "${TMP_NVIM}"

# NEOVIM NIGHTLY
TMP_NVIM=$(mktemp)
curl -sSLo "${TMP_NVIM}" https://github.com/neovim/neovim/releases/download/nightly/nvim-linux-x86_64.tar.gz
tar -C /opt -xzf "${TMP_NVIM}" && ln -sf /opt/nvim-linux-x86_64/bin/nvim /usr/bin/nvim && rm -rf "${TMP_NVIM}"

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
