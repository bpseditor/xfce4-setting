#!/bin/sh
set -eu
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT HUP INT TERM
curl --fail --location --proto '=https' --tlsv1.2 https://github.com/bpseditor/xfce-tokyo-night/archive/refs/heads/main.tar.gz -o "$work/repo.tar.gz"
tar -xzf "$work/repo.tar.gz" -C "$work"
sh "$work/xfce-tokyo-night-main/install.sh" "$@"
