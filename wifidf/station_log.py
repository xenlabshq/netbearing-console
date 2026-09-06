"""Cok-noktali konum kesisimi (triangulation) icin istasyon bazli bearing kaydi.

Akis: cihazi 2+ farkli, bilinen (x,y) konumuna tasiyin (veya birden fazla
cihazi farkli sabit noktalara kurun). Her konumda `record_station` ile o
konumdaki tum tespit edilen cihazlarin (hedeflerin) bearing'ini bir JSONL
dosyasina kaydedin. Sonra `triangulate.py` + bu log dosyasi ile MAC basina
konum kesisimi hesaplanir.

ONEMLI: Antenlerin "on" (0 derece) referansi tum istasyonlarda AYNI mutlak
yone (orn. gercek Kuzey) hizali olmalidir; aksi halde bearing'ler ortak bir
koordinat sistemine oturmaz ve kesisim hatali olur.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from wifidf.bearing import load_pattern
from wifidf.config import DeviceConfig, DATA_DIR
from wifidf.distance import load_path_loss_model
from wifidf.tracker import Tracker
from wifidf.util import require_root

DEFAULT_LOG_PATH = DATA_DIR / "station_log.jsonl"


def record_station(
    station_x: float,
    station_y: float,
    duration: float = 8.0,
    cfg: DeviceConfig | None = None,
    log_path: Path = DEFAULT_LOG_PATH,
) -> int:
    """Verilen konumda `duration` saniye dinler, tespit edilen her cihaz icin
    bir bearing gozlemi log dosyasina ekler. Kaydedilen gozlem sayisini dondurur.
    """
    require_root()
    cfg = cfg or DeviceConfig.load()
    pattern = load_pattern()
    path_loss = load_path_loss_model()

    with Tracker(cfg, pattern, path_loss) as tracker:
        end = time.time() + duration
        devices = []
        while time.time() < end:
            devices = tracker.poll()
            time.sleep(0.5)

    log_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with log_path.open("a") as f:
        for dev in devices:
            if not dev.bearing:
                continue
            record = {
                "timestamp": time.time(),
                "station_x": station_x,
                "station_y": station_y,
                "mac": dev.mac,
                "ssid": dev.ssid,
                "bearing_deg": dev.bearing.bearing_deg,
                "confidence": dev.bearing.confidence,
            }
            f.write(json.dumps(record) + "\n")
            count += 1
    return count


def load_observations_by_mac(log_path: Path = DEFAULT_LOG_PATH) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    if not log_path.exists():
        return out
    for line in log_path.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        out.setdefault(rec["mac"], []).append(rec)
    return out
