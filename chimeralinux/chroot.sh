#!/usr/bin/env -S sh -e
PKGS="asciinema bash bash-completion blender cargo chrony cmake distrobox ffmpeg firefox fonts-noto-emoji fonts-noto-sans-cjk-ttf fonts-noto-serif-cjk-ttf fonts-noto-ttf fuzzel fzf gamescope git imv intel-media-driver jq mako mpv nemo networkmanager ninja niri nushell pipewire podman python ripgrep rust starship steam-devices-udev swww ufw uv xdg-desktop-portal-gnome xdg-user-dirs xwayland-satellite yt-dlp zoxide"

apk add chimera-repo-user ucode-intel

# Configure the system

tee /etc/doas.conf &> /dev/null << EOF
permit persist setenv {PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin} :wheel
EOF

chown -c root:root /etc/doas.conf
chmod -c 0400 /etc/doas.conf

genfstab / > /etc/fstab
echo "$HOSTNAME" > /etc/hostname
ln -sf /usr/share/zoneinfo/Europe/Helsinki /etc/localtime
update-initramfs -c -k all

# Install bootloader

apk add systemd-boot
bootctl install
gen-systemd-boot

# Install packages

apk add $PKGS

# Enable services

dinitctl enable {networkmanager,swww}

# Set firewall

ufw enable
ufw default deny incoming
ufw default allow outgoing

# Set users

chsh --shell /bin/bash root
useradd --create-home --groups wheel,kvm,plugdev --shell /usr/bin/nu $USERNAME

USERHOME=/home/$USERNAME
sudo -u $USERNAME mkdir -p $USERHOME/{Desktop,Downloads,Pictures,Videos,stuff}
