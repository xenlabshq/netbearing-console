"""Cihaz yapilandirmasi: yon <-> arayuz eslesmesi, anten acilari, dosya yollari."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CALIBRATION_DIR = DATA_DIR / "calibration"
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "data" / "device_config.json"

# Silindirik govde ustunde 90 derece araliklarla yerlesim (saat yonunde, on=0 referans)
DEFAULT_BEARINGS = {
    "front": 0.0,
    "right": 90.0,
    "back": 180.0,
    "left": 270.0,
}

DIRECTIONS = ("front", "right", "back", "left")

TR_LABELS = {
    "front": "On",
    "right": "Sag",
    "back": "Arka",
    "left": "Sol",
}


@dataclass
class AntennaConfig:
    direction: str            # "front" | "right" | "back" | "left"
    boresight_deg: float      # antenin baktigi aci (0=on referans, saat yonunde artar)
    interface: str            # monitor-mode arayuz adi, orn. "wlandf_front"
    mac: str | None = None    # adaptorun donanim MAC'i (sadece bilgi amacli; udev eslemesi icin KULLANILMAZ -
                               # NetworkManager bu MAC'i her takista rastgele degistirebilir)
    id_path: str | None = None  # USB fiziksel port yolu (ID_PATH); udev isimlendirmesi buna gore yapilir


@dataclass
class DeviceConfig:
    antennas: dict[str, AntennaConfig] = field(default_factory=dict)
    channel: int | None = None  # dinlenecek sabit Wi-Fi kanali

    @classmethod
    def default(cls) -> "DeviceConfig":
        antennas = {
            d: AntennaConfig(direction=d, boresight_deg=DEFAULT_BEARINGS[d], interface=f"wlandf_{d}")
            for d in DIRECTIONS
        }
        return cls(antennas=antennas)

    @classmethod
    def load(cls, path: Path = DEFAULT_CONFIG_PATH) -> "DeviceConfig":
        if not path.exists():
            return cls.default()
        raw = json.loads(path.read_text())
        antennas = {
            d: AntennaConfig(**a) for d, a in raw["antennas"].items()
        }
        return cls(antennas=antennas, channel=raw.get("channel"))

    def save(self, path: Path = DEFAULT_CONFIG_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = {
            "antennas": {d: vars(a) for d, a in self.antennas.items()},
            "channel": self.channel,
        }
        path.write_text(json.dumps(raw, indent=2, ensure_ascii=False))

    def interfaces(self) -> dict[str, str]:
        return {d: a.interface for d, a in self.antennas.items()}
