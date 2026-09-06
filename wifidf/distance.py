"""RSSI'dan kaba mesafe kestirimi (log-distance yol kaybi modeli).

ONEMLI: Tek istasyonda RSSI->mesafe donusumu, coklu yol yansimalari ve ortam
degiskenligi nedeniyle DUSUK DOGRULUKTADIR (genelde +-2-3x hata payi olabilir).
Yuksek dogruluklu KONUM icin bunun yerine triangulate.py kullanarak en az 2
farkli noktadan alinan yon (bearing) olcumlerini kesistirin.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from wifidf.config import CALIBRATION_DIR

PATH_LOSS_CALIBRATION_PATH = CALIBRATION_DIR / "path_loss.json"


@dataclass
class PathLossModel:
    rssi_ref_1m: float = -40.0  # 1 metredeki referans RSSI (dBm), kalibre edilmeli
    path_loss_exponent: float = 2.5  # tipik ic mekan: 2.0-4.0

    def distance_m(self, rssi_dbm: float) -> float:
        exponent = (self.rssi_ref_1m - rssi_dbm) / (10.0 * self.path_loss_exponent)
        return 10.0 ** exponent

    def to_dict(self) -> dict:
        return {"rssi_ref_1m": self.rssi_ref_1m, "path_loss_exponent": self.path_loss_exponent}

    @classmethod
    def from_dict(cls, d: dict) -> "PathLossModel":
        return cls(rssi_ref_1m=d["rssi_ref_1m"], path_loss_exponent=d["path_loss_exponent"])


def load_path_loss_model(path: Path = PATH_LOSS_CALIBRATION_PATH) -> PathLossModel:
    if not path.exists():
        return PathLossModel()
    return PathLossModel.from_dict(json.loads(path.read_text()))


def save_path_loss_model(model: PathLossModel, path: Path = PATH_LOSS_CALIBRATION_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(model.to_dict(), indent=2))


def best_signal_rssi(readings: dict[str, float]) -> float:
    """Mesafe kestirimi icin en guclu (en yakin yonelimli) anten okumasini kullan."""
    return max(readings.values())
