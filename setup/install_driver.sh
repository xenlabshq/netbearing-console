#!/usr/bin/env bash
# TL-WN722N v2/v3 (Realtek RTL8188EUS cipset) icin monitor-mode + injection
# destekli sürücüyü DKMS ile kurar.
#
# NOT: TL-WN722N v1, Atheros AR9271 cipseti kullanir ve cekirdek ic surucusu
# (ath9k_htc) zaten monitor mode destekler - o revizyon icin bu script GEREKMEZ.
# v2/v3 STICKER uzerinde "Ver: 2." veya "Ver: 3." yazar ve Realtek RTL8188EUS
# kullanir; monitor mode + paket enjeksiyonu icin bu out-of-tree surucu sarttir.
set -euo pipefail

REPO_URL="https://github.com/aircrack-ng/rtl8188eus.git"
DEFAULT_SRC_DIR="${HOME}/rtl8188eus"

SRC_DIR="${1:-$DEFAULT_SRC_DIR}"

if [ -d "$SRC_DIR" ] && [ -f "$SRC_DIR/dkms.conf" ]; then
  echo "[*] Mevcut surucu kaynagi kullaniliyor: $SRC_DIR"
else
  echo "[*] Surucu kaynagi klonlaniyor: $REPO_URL -> $SRC_DIR"
  git clone --depth 1 "$REPO_URL" "$SRC_DIR"
fi

cd "$SRC_DIR"

if [ ! -f dkms-install.sh ]; then
  echo "[!] dkms-install.sh bulunamadi, repo yapisi beklenenden farkli." >&2
  exit 1
fi

echo "[*] DKMS ile kuruluyor (sudo gerekebilir)..."
sudo bash dkms-install.sh

echo "[*] Kurulum tamamlandi. Adaptorleri takip 'dmesg | tail' ile kontrol edin."
echo "    Beklenen surucu modulu: 8188eu"
