"""rich tabanli canli terminal dashboard: tespit edilen cihazlar, yon ve mesafe."""

from __future__ import annotations

import time

from rich.console import Console
from rich.live import Live
from rich.table import Table

from wifidf.bearing import load_pattern
from wifidf.config import DeviceConfig, DIRECTIONS, TR_LABELS
from wifidf.distance import load_path_loss_model
from wifidf.tracker import Tracker
from wifidf.util import require_root

REFRESH_HZ = 4


def _build_table(devices) -> Table:
    table = Table(title="Wi-Fi Yon Bulucu - Canli Tarama", expand=True)
    table.add_column("MAC")
    table.add_column("SSID")
    for d in DIRECTIONS:
        table.add_column(TR_LABELS[d], justify="right")
    table.add_column("Yon (derece)", justify="right")
    table.add_column("Pusula")
    table.add_column("Guven", justify="right")
    table.add_column("~Mesafe (m)", justify="right")
    table.add_column("Son Gorulme", justify="right")

    now = time.time()
    for dev in devices:
        row = [dev.mac, dev.ssid or "-"]
        for d in DIRECTIONS:
            v = dev.readings.get(d)
            row.append(f"{v:.0f}" if v is not None else "-")
        if dev.bearing:
            row.append(f"{dev.bearing.bearing_deg:.0f}")
            row.append(dev.compass or "-")
            row.append(f"{dev.bearing.confidence * 100:.0f}%")
        else:
            row.extend(["-", "-", "-"])
        row.append(f"{dev.distance_m:.1f}" if dev.distance_m else "-")
        row.append(f"{now - dev.last_seen:.1f}s")
        table.add_row(*row)
    return table


def run_dashboard(cfg: DeviceConfig | None = None) -> None:
    require_root()
    cfg = cfg or DeviceConfig.load()
    pattern = load_pattern()
    path_loss = load_path_loss_model()
    console = Console()

    with Tracker(cfg, pattern, path_loss) as tracker:
        with Live(console=console, refresh_per_second=REFRESH_HZ) as live:
            try:
                while True:
                    devices = tracker.poll()
                    live.update(_build_table(devices))
                    time.sleep(1.0 / REFRESH_HZ)
            except KeyboardInterrupt:
                pass


if __name__ == "__main__":
    run_dashboard()
