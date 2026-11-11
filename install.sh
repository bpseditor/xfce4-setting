#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
case " $* " in *" --dry-run "*) exec python3 install.py "$@";; esac
[ "$(id -u)" -ne 0 ] || { echo 'Run as your XFCE user, not root.'; exit 1; }
[ -n "${DISPLAY:-}" ] && [ -n "${DBUS_SESSION_BUS_ADDRESS:-}" ] || { echo 'Run inside XFCE.'; exit 1; }
command -v xbps-install >/dev/null || { echo 'Void Linux is required.'; exit 1; }
sudo xbps-install -y python3 python3-gobject gtk+3 xfce4-panel xfce4-whiskermenu-plugin xfce4-genmon-plugin xfce4-pulseaudio-plugin pavucontrol qt5ct qt6ct xfce4-xkb-plugin xfce4-notifyd xfce4-power-manager xfce4-screensaver xfce4-terminal xfce4-taskmanager Thunar libnotify noto-fonts-cjk noto-fonts-emoji papirus-icon-theme curl git
exec python3 install.py "$@"
