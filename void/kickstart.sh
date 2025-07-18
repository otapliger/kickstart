#!/usr/bin/env -S bash -e
BOLD='\e[1m'
RED='\e[91m'
BLUE='\e[94m'
WHITE='\e[37m'
GREEN='\e[92m'
RESET='\e[0m'

ARCH=x86_64
REPO=https://repo-fi.voidlinux.org/current
BTRFS_OPTS="compress=zstd,noatime"

info () {
  echo -e "${GREEN}$1${RESET}"
}

choice () {
  echo -e "${BLUE}$1${RESET}"
}

input () {
  echo -ne "${WHITE}$1${RESET}"
}

error () {
  echo -e "${RED}$1${RESET}"
}

set_user () {
  echo
  input "We need to create a new user. Set the username: "
  read -r USERNAME
  if [[ -z "$USERNAME" ]]; then
    echo
    error "You need to create an user in order to continue."
    return 1
  fi
  return 0
}

set_pass () {
  USERPASS=
  USERPASSCHECK=
  echo -n "Set a password for $USERNAME: " 1>&2
  while true; do
    IFS= read -r -N1 -s CHAR
    CHARCODE=$(printf '%02x' "'$CHAR")
    case "$CHARCODE" in
    ''|0a|0d)
      break
      ;;
    08|7f)
      if [ -n "$USERPASS" ]; then
        USERPASS="$( echo "$USERPASS" | sed 's/.$//' )"
        echo -n $'\b \b' 1>&2
      fi
      ;;
    15)
      echo -n "$USERPASS" | sed 's/./\cH \cH/g' >&2
      USERPASS=''
      ;;
    [01]?)
      ;;
    *)
      USERPASS="$USERPASS$CHAR"
      echo -n '*' 1>&2
      ;;
    esac
  done
  echo
  if [[ -z "$USERPASS" ]]; then
    echo
    error "You need to enter a password for $USERNAME, please try again."
    return 1
  fi
  echo -n "Verify the password: " 1>&2
  while true; do
    IFS= read -r -N1 -s CHAR
    CHARCODE=$(printf '%02x' "'$CHAR")
    case "$CHARCODE" in
    ''|0a|0d)
      break
      ;;
    08|7f)
      if [ -n "$USERPASSCHECK" ]; then
        USERPASSCHECK="$( echo "$USERPASSCHECK" | sed 's/.$//' )"
        echo -n $'\b \b' 1>&2
      fi
      ;;
    15)
      echo -n "$USERPASSCHECK" | sed 's/./\cH \cH/g' >&2
      USERPASSCHECK=''
      ;;
    [01]?)
      ;;
    *)
      USERPASSCHECK="$USERPASSCHECK$CHAR"
      echo -n '*' 1>&2
      ;;
    esac
  done
  echo
  if [[ "$USERPASS" != "$USERPASSCHECK" ]]; then
    echo
    error "Passwords don't match, please try again."
    return 1
  fi
  return 0
}

set_host () {
  echo
  input "Set a hostname for the system: "
  read -r HOSTNAME
  if [[ -z "$HOSTNAME" ]]; then
    echo
    error "You need to enter a hostname in order to continue."
    return 1
  fi
  return 0
}

set_disk () {
  echo
  DISKS=($(lsblk -dpnoNAME|grep -P "/dev/nvme|sd|vd"))
  for i in "${!DISKS[@]}"; do
    choice "$(expr $i + 1)) ${DISKS[$i]}"
  done
  input "Please select the destination disk: "
  read -r DISK_CHOICE
  if ! ((DISK_CHOICE >= 1 && DISK_CHOICE <= ${#DISKS[@]})); then
    echo
    error "You did not enter a valid selection, please try again."
    return 1
  fi
  DISK="${DISKS[$(expr $DISK_CHOICE - 1)]}"
  info "Void will be installed on $DISK."
  return 0
}

set_luks () {
  echo
  LUKSPASS=
  LUKSPASSCHECK=
  echo -n "Set a password for the LUKS container: " 1>&2
  while true; do
    IFS= read -r -N1 -s CHAR
    CHARCODE=$(printf '%02x' "'$CHAR")
    case "$CHARCODE" in
    ''|0a|0d)
      break
      ;;
    08|7f)
      if [ -n "$LUKSPASS" ]; then
        LUKSPASS="$( echo "$LUKSPASS" | sed 's/.$//' )"
        echo -n $'\b \b' 1>&2
      fi
      ;;
    15)
      echo -n "$LUKSPASS" | sed 's/./\cH \cH/g' >&2
      LUKSPASS=''
      ;;
    [01]?)
      ;;
    *)
      LUKSPASS="$LUKSPASS$CHAR"
      echo -n '*' 1>&2
      ;;
    esac
  done
  echo
  if [[ -z "$LUKSPASS" ]]; then
    echo
    error "You need to enter a password for the LUKS Container, please try again."
    return 1
  fi
  echo -n "Verify the password: " 1>&2
  while true; do
    IFS= read -r -N1 -s CHAR
    CHARCODE=$(printf '%02x' "'$CHAR")
    case "$CHARCODE" in
    ''|0a|0d)
      break
      ;;
    08|7f)
      if [ -n "$LUKSPASSCHECK" ]; then
        LUKSPASSCHECK="$( echo "$LUKSPASSCHECK" | sed 's/.$//' )"
        echo -n $'\b \b' 1>&2
      fi
      ;;
    15)
      echo -n "$LUKSPASSCHECK" | sed 's/./\cH \cH/g' >&2
      LUKSPASSCHECK=''
      ;;
    [01]?)
      ;;
    *)
      LUKSPASSCHECK="$LUKSPASSCHECK$CHAR"
      echo -n '*' 1>&2
      ;;
    esac
  done
  echo
  if [[ "$LUKSPASS" != "$LUKSPASSCHECK" ]]; then
    echo
    error "Passwords don't match, please try again."
    return 1
  fi
  return 0
}

echo -ne "${BOLD}${GREEN}
█▄▀ █ █▀▀ █▄▀ █▀ ▀█▀ ▄▀█ █▀█ ▀█▀
█░█ █ █▄▄ █░█ ▄█  █  █▀█ █▀▄  █
${RESET}"
info "Welcome to void.kickstart, a Void Linux installer."

if [ "$(id -u)" -ne 0 ]; then
  echo "${RED}Error:${RESET} root privileges is required. Please re-run the script as root" >&2
  exit 1
fi

until set_host; do : ; done
until set_disk; do : ; done
until set_luks; do : ; done
until set_user; do : ; done
until set_pass; do : ; done
echo

xbps-install -Suy xbps parted gptfdisk &> /dev/null

# FILESYSTEM

# Warn user about deletion of old partition scheme
input "The current partition table on $DISK will be deleted. Do you want to proceed with the installation [y/N]?: "
read -r DISK_RESPONSE
if ! [[ "${DISK_RESPONSE,,}" =~ ^(y|yes)$ ]]; then
  error "Installation aborted. No changes were made to the system."
  exit
fi
info "- (1/10) wiping $DISK"
wipefs -af "$DISK" &> /dev/null
sgdisk -Zo "$DISK" &> /dev/null

# Creating a new partition scheme
info "- (2/10) creating new partitions on $DISK"
parted -s "$DISK" \
  mklabel gpt \
  mkpart esp fat32 1MiB 513MiB \
  mkpart cryptroot 513MiB 100% \
  set 1 esp on \

ESP="/dev/disk/by-partlabel/esp"
CRYPTROOT="/dev/disk/by-partlabel/cryptroot"

# Informing the Kernel of the changes
info "- (3/10) informing the Kernel about the disk changes"
partprobe "$DISK"

# Formatting EFI as FAT32
info "- (4/10) formatting the EFI Partition as FAT32"
mkfs.vfat -F32 -n esp "$ESP" &> /dev/null

# Creating a LUKS Container for the root partition
info "- (5/10) creating LUKS Container for the root partition"
echo -n "$LUKSPASS" | cryptsetup luksFormat --type luks1 --pbkdf-force-iterations 1000 "$CRYPTROOT" -d - &> /dev/null
echo -n "$LUKSPASS" | cryptsetup luksOpen "$CRYPTROOT" void -d -
VOID="/dev/mapper/void"

# Formatting the LUKS Container as BTRFS
info "- (6/10) formatting the LUKS container as BTRFS"
mkfs.btrfs -L "$HOSTNAME" "$VOID" &> /dev/null
mount -o "$BTRFS_OPTS" "$VOID" /mnt

# Creating BTRFS subvolumes.
info "- (7/10) creating BTRFS subvolumes"
SUBVOLUMES=(home snapshots var_cache var_log)
for SUBVOLUME in '' "${SUBVOLUMES[@]}"; do
  btrfs subvolume create /mnt/@"$SUBVOLUME" &> /dev/null
done

# Mounting the newly created subvolumes
info "- (8/10) mounting the newly created subvolumes"
umount /mnt

mount -o X-mount.mkdir,"$BTRFS_OPTS",subvol=@ "$VOID" /mnt
mount -o X-mount.mkdir,"$BTRFS_OPTS",subvol=@snapshots "$VOID" /mnt/.snapshots
mount -o X-mount.mkdir,"$BTRFS_OPTS",subvol=@var_cache "$VOID" /mnt/var/cache
mount -o X-mount.mkdir,"$BTRFS_OPTS",subvol=@var_log "$VOID" /mnt/var/log
mount -o X-mount.mkdir,"$BTRFS_OPTS",subvol=@home "$VOID" /mnt/home

# Bootstrap (setting up a base sytem onto the new root)
info "- (9/10) installing the base system (it may take a few minutes)"

# Mount EFI partition inside boot folder
mkdir -p /mnt/boot/efi
mount "$ESP" /mnt/boot/efi

# Create directory and copy RSA keys for verifying package integrity
mkdir -p /mnt/var/db/xbps/keys
cp /var/db/xbps/keys/* /mnt/var/db/xbps/keys

XBPS_ARCH=$ARCH xbps-install -Sy -R "$REPO" -r /mnt \
linux \
base-system \
base-devel \
cryptsetup \
efibootmgr \
grub-btrfs \
grub-x86_64-efi \
NetworkManager &> /dev/null

# Chroot (setup the system)
info "- (10/10) setting up the system (settings, packages and users)"
cp /etc/resolv.conf /mnt/etc
cp chroot.sh /mnt/root

mount --types sysfs none /mnt/sys
mount --types proc none /mnt/proc
mount --rbind /run /mnt/run
mount --rbind /dev /mnt/dev

ARCH=$ARCH HOSTNAME=$HOSTNAME USERNAME=$USERNAME LUKSPASS=$LUKSPASS REPO=$REPO BTRFS_OPTS=$BTRFS_OPTS \
chroot /mnt /bin/bash -x /root/chroot.sh

yes "$USERPASS" | chroot /mnt passwd root &> /dev/null
yes "$USERPASS" | chroot /mnt passwd $USERNAME &> /dev/null

# Finishing up
rm -rf /mnt/root/chroot.sh
umount --recursive /mnt
info "Installation completed. You can now reboot your system."
exit
