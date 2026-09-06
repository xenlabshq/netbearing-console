#!/usr/bin/env python3
"""Mevcut cihaz konumunda bearing gozlemleri kaydeder (ucgenleme icin).

Ornek: cihazi (0,0) noktasina koyup 10 sn dinle, sonra 20 metre doguya
tasiyip (20,0) noktasinda tekrar dinle -> iki noktadaki bearing'ler
kesistirilerek hedeflerin konumu bulunabilir (bkz. scripts/fix_targets.py).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wifidf.station_log import record_station


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Istasyon bearing kaydi")
    parser.add_argument("x", type=float, help="Istasyon X konumu (metre, Dogu)")
    parser.add_argument("y", type=float, help="Istasyon Y konumu (metre, Kuzey)")
    parser.add_argument("--duration", type=float, default=8.0)
    args = parser.parse_args()

    n = record_station(args.x, args.y, duration=args.duration)
    print(f"{n} bearing gozlemi kaydedildi ({args.x}, {args.y}) konumunda.")


if __name__ == "__main__":
    main()
