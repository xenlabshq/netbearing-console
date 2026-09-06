#!/usr/bin/env python3
"""station_log.jsonl'daki gozlemlerden her MAC icin konum kesisimi hesaplar."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wifidf.station_log import DEFAULT_LOG_PATH, load_observations_by_mac
from wifidf.triangulate import BearingObservation, fix_position


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Kayitli bearing gozlemlerinden konum kesisimi")
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG_PATH)
    args = parser.parse_args()

    by_mac = load_observations_by_mac(args.log)
    if not by_mac:
        print(f"Kayit bulunamadi: {args.log}")
        return

    for mac, recs in by_mac.items():
        obs = [
            BearingObservation(
                station_x=r["station_x"],
                station_y=r["station_y"],
                bearing_deg=r["bearing_deg"],
                weight=r.get("confidence", 1.0),
            )
            for r in recs
        ]
        # Aynı MAC icin ayni istasyon konumundan birden fazla gozlem varsa
        # sadece farkli istasyonlardan gelenler kesisim uretir.
        stations = {(o.station_x, o.station_y) for o in obs}
        ssid = recs[-1].get("ssid") or "-"
        if len(stations) < 2:
            print(f"{mac} ({ssid}): yetersiz (sadece {len(stations)} istasyondan gozlem) - en az 2 farkli konumdan olcum gerekli")
            continue
        fix = fix_position(obs)
        if fix is None:
            print(f"{mac} ({ssid}): kesisim hesaplanamadi (dogrular paralel olabilir)")
            continue
        print(
            f"{mac} ({ssid}): konum tahmini x={fix.x:.1f} y={fix.y:.1f}  "
            f"[artik={fix.residual:.1f}, aci-sapmasi={fix.spread_deg:.1f} derece, "
            f"{len(stations)} istasyon]"
        )


if __name__ == "__main__":
    main()
