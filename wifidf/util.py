"""Ortak yardimcilar."""

import os
import sys


def require_root(reason: str = "Wi-Fi paketlerini yakalamak") -> None:
    """Ham soket erisimi (paket yakalama) root gerektirir; degilse anlasilir hata verip cikar."""
    if os.geteuid() != 0:
        print(f"[!] Bu islem root yetkisi gerektirir ({reason}). Basina 'sudo' ekleyip tekrar calistirin.", file=sys.stderr)
        sys.exit(1)
