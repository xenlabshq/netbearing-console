#!/usr/bin/env bash
# 4 anten arayuzunu (wlandf_front/right/back/left) monitor moda alir ve
# istege bagli olarak ortak bir kanala kilitler.
#
# Kullanim: sudo ./monitor_mode.sh [kanal]
#   sudo ./monitor_mode.sh          -> sadece monitor moda alir, kanal degistirmez
#   sudo ./monitor_mode.sh 6        -> monitor moda alir ve kanal 6'ya kilitler
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Bu script root gerektirir: sudo $0 $*" >&2
  exit 1
fi

CHANNEL="${1:-}"
IFACES=(wlandf_front wlandf_right wlandf_back wlandf_left)

for ifc in "${IFACES[@]}"; do
  if ! ip link show "$ifc" &>/dev/null; then
    echo "[!] Arayuz bulunamadi: $ifc (udev kurali kurulu mu? adaptor takili mi?)" >&2
    continue
  fi
  echo "[*] $ifc -> monitor mode"
  ip link set "$ifc" down
  iw dev "$ifc" set type monitor
  ip link set "$ifc" up
  if [ -n "$CHANNEL" ]; then
    iw dev "$ifc" set channel "$CHANNEL"
    echo "    kanal $CHANNEL ayarlandi"
  fi
done

echo "[*] Tamamlandi. Durum:"
iw dev
