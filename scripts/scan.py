#!/usr/bin/env python3
"""4 antenden kisa sureli tarama yapar; gorulen MAC/SSID/RSSI listesini basar.

Kalibrasyon veya izleme oncesi hedef MAC adresini bulmak icin kullanilir.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wifidf.aggregator import Aggregator
from wifidf.capture import CaptureManager
from wifidf.config import DeviceConfig
from wifidf.util import require_root


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Kisa sureli Wi-Fi tarama")
    parser.add_argument("--duration", type=float, default=10.0)
    args = parser.parse_args()

    require_root()
    cfg = DeviceConfig.load()
    agg = Aggregator()
    manager = CaptureManager(cfg.interfaces())
    manager.start()
    print(f"Taraniyor ({args.duration:.0f} sn)...")
    try:
        end = time.time() + args.duration
        while time.time() < end:
            agg.drain_queue(manager.out_queue)
            time.sleep(0.2)
        agg.drain_queue(manager.out_queue)
    finally:
        manager.stop()

    now = time.time()
    print(f"\n{'MAC':<20}{'SSID':<30}{'Yonler':<20}{'Son Gorulme'}")
    for dev in sorted(agg.snapshot(), key=lambda d: d.last_seen, reverse=True):
        readings = dev.readings(now, window=args.duration + 1.0)
        dirs = ",".join(f"{k}:{v:.0f}" for k, v in readings.items())
        print(f"{dev.mac:<20}{(dev.ssid or '-'): <30}{dirs:<20}{now - dev.last_seen:.1f}s")


if __name__ == "__main__":
    main()
