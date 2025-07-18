#!/usr/bin/env -S sh -e
BOLD='\e[1m'
RED='\e[91m'
BLUE='\e[94m'
WHITE='\e[37m'
GREEN='\e[92m'
RESET='\e[0m'

ARCH=x86_64
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
  info "Chimera Linux will be installed on $DISK."
  return 0
}

set_zfs_pass () {
  echo
  ZFSPASS=
  ZFSPASSCHECK=
  echo -n "Set a password for the ZFS pool: " 1>&2
  while true; do
    IFS= read -r -N1 -s CHAR
    CHARCODE=$(printf '%02x' "'$CHAR")
    case "$CHARCODE" in
    ''|0a|0d)
      break
      ;;
    08|7f)
      if [ -n "$ZFSPASS" ]; then
        ZFSPASS="$( echo "$ZFSPASS" | sed 's/.$//' )"
        echo -n $'\b \b' 1>&2
      fi
      ;;
    15)
      echo -n "$ZFSPASS" | sed 's/./\cH \cH/g' >&2
      ZFSPASS=''
      ;;
    [01]?)
      ;;
    *)
      ZFSPASS="$ZFSPASS$CHAR"
      echo -n '*' 1>&2
      ;;
    esac
  done
  echo
  if [[ -z "$ZFSPASS" ]]; then
    echo
    error "You need to enter a password for the ZFS pool, please try again."
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
      if [ -n "$ZFSPASSCHECK" ]; then
        ZFSPASSCHECK="$( echo "$ZFSPASSCHECK" | sed 's/.$//' )"
        echo -n $'\b \b' 1>&2
      fi
      ;;
    15)
      echo -n "$ZFSPASSCHECK" | sed 's/./\cH \cH/g' >&2
      ZFSPASSCHECK=''
      ;;
    [01]?)
      ;;
    *)
      ZFSPASSCHECK="$ZFSPASSCHECK$CHAR"
      echo -n '*' 1>&2
      ;;
    esac
  done
  echo
  if [[ "$ZFSPASS" != "$ZFSPASSCHECK" ]]; then
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
info "Welcome to chimera.kickstart, a Chimera Linux installer."

if [ "$(id -u)" -ne 0 ]; then
  echo "${RED}Error:${RESET} root privileges is required. Please re-run the script as root" >&2
  exit 1
fi

until set_host; do : ; done
until set_disk; do : ; done
until set_zfs_pass; do : ; done
until set_user; do : ; done
until set_pass; do : ; done
echo

apk update &> /dev/null
apk add parted gptfdisk &> /dev/null

# FILESYSTEM

# Warn user about deletion of old partition scheme
input "The current partition table on $DISK will be deleted. Do you want to proceed with the installation [y/N]?: "
read -r DISK_RESPONSE
if ! [[ "${DISK_RESPONSE,,}" =~ ^(y|yes)$ ]]; then
  error "Installation aborted. No changes were made to the system."
  exit
fi
info "- (1/7) wiping $DISK"
wipefs -af "$DISK" &> /dev/null
sgdisk -Zo "$DISK" &> /dev/null

# Creating a new partition scheme
info "- (2/7) creating new partitions on $DISK"
parted -s "$DISK" \
  mklabel gpt \
  mkpart boot fat32 1MiB 1025MiB \
  mkpart $HOSTNAME 1025MiB 100% \
  set 1 boot on \

BOOT="/dev/disk/by-partlabel/boot"
ZPOOL="/dev/disk/by-partlabel/$HOSTNAME"

# Informing the Kernel of the changes
info "- (3/7) informing the Kernel about the disk changes"
partprobe "$DISK"

# Formatting EFI as FAT32
info "- (4/7) formatting the EFI Partition as FAT32"
mkfs.vfat -F32 -n boot "$BOOT" &> /dev/null

# Setting the ZFS pool
info "- (5/7) setting the ZFS pool"
zpool create \
  -O xattr=sa \
  -O relatime=on \
  -O compression=on \
  -O acltype=posixacl \
  -O atime=off \
  -o ashift=12 \
  -R /mnt \
  $HOSTNAME "$ZPOOL"

yes "$ZFSPASS" | \
zfs create -o mountpoint=none -o encryption=on -o keyformat=passphrase -o keylocation=prompt $HOSTNAME/encrypted
zfs create -o mountpoint=/ canmount=noauto $HOSTNAME/encrypted/root/chimera
zfs create -o mountpoint=/home $HOSTNAME/encrypted/home
zfs mount $HOSTNAME/encrypted/root/chimera
zfs mount $HOSTNAME/encrypted/home

# Mount EFI partition inside boot folder
mkdir -p /mnt/boot
mount "$BOOT" /mnt/boot

# Bootstrap (setting up a base sytem onto the new root)
info "- (6/7) installing the base system (it may take a few minutes)"
chimera-bootstrap /mnt

# Chroot (setup the system)
info "- (7/7) setting up the system (settings, packages and users)"
cp /etc/resolv.conf /mnt/etc
cp chroot.sh /mnt/root

mount --types sysfs none /mnt/sys
mount --types proc none /mnt/proc
mount --rbind /run /mnt/run
mount --rbind /dev /mnt/dev

HOSTNAME=$HOSTNAME USERNAME=$USERNAME \
chroot /mnt /usr/bin/sh -x /root/chroot.sh

yes "$USERPASS" | chroot /mnt passwd root &> /dev/null
yes "$USERPASS" | chroot /mnt passwd $USERNAME &> /dev/null

# Finishing up
rm -rf /mnt/root/chroot.sh
umount --recursive /mnt
info "Installation completed. You can now reboot your system."
exit
