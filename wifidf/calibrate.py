"""Interaktif kalibrasyon: bilinen acilarda referans bir vericiyi olcup anten
kazanc paternini (GainPattern) cikarir.

Kullanim: bilinen MAC adresine sahip bir Wi-Fi verici (orn. telefon hotspot'u)
cihazdan sabit bir yaricapta, sirayla belirlenen acilara (varsayilan 30 derece
araliklarla, 0=on referans, saat yonunde) yerlestirilir; her acida script
birkaç saniye ornek toplar.
"""

from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

import numpy as np

from wifidf.aggregator import Aggregator
from wifidf.bearing import GainPattern, _angle_diff, save_pattern
from wifidf.capture import CaptureManager
from wifidf.config import CALIBRATION_DIR, DeviceConfig, DIRECTIONS
from wifidf.util import require_root

RAW_CALIBRATION_PATH = CALIBRATION_DIR / "raw_calibration.json"


def _collect(cfg: DeviceConfig, target_mac: str, duration: float) -> dict[str, float]:
    """Bir aci icin duration saniye boyunca dinler, yon basina medyan RSSI dondurur."""
    target_mac = target_mac.lower()
    agg = Aggregator()
    manager = CaptureManager(cfg.interfaces())
    manager.start()
    try:
        end = time.time() + duration
        while time.time() < end:
            agg.drain_queue(manager.out_queue)
            time.sleep(0.1)
        agg.drain_queue(manager.out_queue)
    finally:
        manager.stop()

    now = time.time()
    for dev in agg.snapshot():
        if dev.mac.lower() == target_mac:
            return dev.readings(now, window=duration + 1.0)
    return {}


def run_calibration(
    cfg: DeviceConfig,
    target_mac: str,
    angles_deg: list[float] | None = None,
    duration: float = 5.0,
) -> GainPattern:
    if angles_deg is None:
        angles_deg = list(np.arange(0.0, 360.0, 30.0))

    boresights = {d: cfg.antennas[d].boresight_deg for d in DIRECTIONS}
    rounds: list[dict] = []

    for angle in angles_deg:
        input(
            f"\n>> Referans vericiyi cihaza gore {angle:.0f} derece konuma yerlestirin "
            f"(0=on, saat yonunde artar), sonra ENTER'a basin..."
        )
        print(f"   Olculuyor ({duration:.0f} sn)...")
        readings = _collect(cfg, target_mac, duration)
        if len(readings) < 3:
            print(f"   [!] Yetersiz okuma ({len(readings)}/4 anten), bu aci atlaniyor.")
            continue
        print(f"   Okumalar: {readings}")
        rounds.append({"angle": angle, "readings": readings})

    if len(rounds) < 4:
        raise RuntimeError("Kalibrasyon icin en az 4 gecerli aci olcumu gerekli.")

    deltas: list[float] = []
    values: list[float] = []
    for r in rounds:
        readings = r["readings"]
        round_mean = statistics.mean(readings.values())
        for direction, rssi in readings.items():
            delta = _angle_diff(r["angle"], boresights[direction])
            deltas.append(delta)
            values.append(rssi - round_mean)

    pattern = GainPattern.fit(np.array(deltas), np.array(values))

    CALIBRATION_DIR.mkdir(parents=True, exist_ok=True)
    RAW_CALIBRATION_PATH.write_text(json.dumps(rounds, indent=2))
    save_pattern(pattern)

    print("\nKalibrasyon tamamlandi:")
    print(f"  g_max={pattern.g_max:.2f} dB, g_min={pattern.g_min:.2f} dB, n={pattern.n:.2f}")
    print(f"  Ham veri: {RAW_CALIBRATION_PATH}")
    return pattern


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Anten kazanc paterni kalibrasyonu")
    parser.add_argument("--mac", required=True, help="Referans vericinin MAC adresi (orn. telefon hotspot)")
    parser.add_argument("--duration", type=float, default=5.0, help="Aci basina olcum suresi (sn)")
    parser.add_argument("--step", type=float, default=30.0, help="Kalibrasyon acilari araligi (derece)")
    parser.add_argument("--config", type=Path, default=None, help="Cihaz yapilandirma dosyasi")
    args = parser.parse_args()

    require_root()
    cfg = DeviceConfig.load(args.config) if args.config else DeviceConfig.load()
    angles = list(np.arange(0.0, 360.0, args.step))
    run_calibration(cfg, args.mac, angles_deg=angles, duration=args.duration)


if __name__ == "__main__":
    main()
