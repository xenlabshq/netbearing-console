"""4 anten uzerinden gelen ornekleri MAC bazinda birlestirir ve gurultuyu azaltir."""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field

from wifidf.capture import Sample

WINDOW_SECONDS = 12.0    # bu sure icindeki ornekler "ayni an" sayilir
# NOT: CaptureManager antenleri es zamanli degil ROTASYONLA dinler (bkz.
# capture.py dokstring'i) - tam bir tur ~4x DWELL_S surer, bu pencere en az
# bir tam turu kapsayacak kadar genis olmali ki 4 yonun de "ayni an"a ait
# sayilan taze okumasi bulunsun.
HISTORY_LEN = 20         # yon basina saklanan son ornek sayisi (medyan icin)
# Cihazlar sinyal gecici olarak kesilse bile listeden ANINDA kaybolmasin diye
# (kullanicinin odaklandigi/aradigi cihazi kaybetmemesi icin) bu sure cok
# uzun tutulur - pratikte bir oturum boyunca "kalici" davranir. Arayuz,
# UI'da tazelik/son gorulme bilgisini ayrica gosterir; devam eden bir
# oturumda gercekten cok uzun sureli goz ardi edilmis (orn. gunlerce
# calisan bir surec) cihazlar icin bellek tasmasini onlemek amacli
# yine de bir ust sinir.
STALE_SECONDS = 6 * 3600.0

# Kalman filtresi parametreleri (dBm^2 cinsinden varyans):
# Q = surec gurultusu (RSSI'nin adimlar arasi ne kadar "kayabilecegi" - hareket/oryantasyon degisimi)
# R = olcum gurultusu (tek bir paketin RSSI okumasindaki tipik gurultu)
KALMAN_PROCESS_VAR = 0.6
KALMAN_MEASUREMENT_VAR = 6.0


class Kalman1D:
    """Tek boyutlu (skaler) Kalman filtresi - RSSI gibi gurultulu ama yavas
    degisen bir sinyali, ham medyan yerine kararli/tepkisel bir sekilde
    izlemek icin. Klasik predict/update formulasyonu.
    """

    def __init__(self, process_var: float = KALMAN_PROCESS_VAR, measurement_var: float = KALMAN_MEASUREMENT_VAR):
        self.x: float | None = None   # mevcut tahmin
        self.p: float = 1.0           # tahmin varyansi
        self.q = process_var
        self.r = measurement_var

    def update(self, z: float) -> float:
        if self.x is None:
            self.x = z
            self.p = self.r
            return self.x
        # predict
        self.p += self.q
        # update
        k = self.p / (self.p + self.r)
        self.x = self.x + k * (z - self.x)
        self.p = (1 - k) * self.p
        return self.x


@dataclass
class DeviceState:
    mac: str
    ssid: str | None = None
    last_seen: float = 0.0
    history: dict[str, deque] = field(default_factory=lambda: {})
    _kalman: dict[str, Kalman1D] = field(default_factory=dict)

    def push(self, direction: str, rssi: float, ts: float) -> None:
        if direction not in self.history:
            self.history[direction] = deque(maxlen=HISTORY_LEN)
            self._kalman[direction] = Kalman1D()
        self.history[direction].append((ts, rssi))
        self._kalman[direction].update(rssi)
        self.last_seen = ts

    def smoothed_rssi(self, direction: str, now: float, window: float = WINDOW_SECONDS) -> float | None:
        buf = self.history.get(direction)
        if not buf:
            return None
        has_recent = any(now - ts <= window for ts, _ in buf)
        if not has_recent:
            return None
        kalman = self._kalman.get(direction)
        return kalman.x if kalman is not None else None

    def readings(self, now: float, window: float = WINDOW_SECONDS) -> dict[str, float]:
        out = {}
        for direction in self.history:
            v = self.smoothed_rssi(direction, now, window)
            if v is not None:
                out[direction] = v
        return out


class Aggregator:
    """Sample kuyrugunu tuketen, cihaz basina son durumu tutan thread-safe depo."""

    def __init__(self):
        self._devices: dict[str, DeviceState] = {}
        self._lock = threading.Lock()

    def ingest(self, sample: Sample) -> None:
        with self._lock:
            dev = self._devices.setdefault(sample.mac, DeviceState(mac=sample.mac))
            dev.push(sample.direction, sample.rssi, sample.timestamp)
            if sample.ssid:
                dev.ssid = sample.ssid

    def drain_queue(self, q, max_items: int = 500) -> int:
        n = 0
        while n < max_items:
            try:
                sample = q.get_nowait()
            except Exception:
                break
            self.ingest(sample)
            n += 1
        return n

    def snapshot(self) -> list[DeviceState]:
        now = time.time()
        with self._lock:
            # eski cihazlari temizle
            stale = [mac for mac, d in self._devices.items() if now - d.last_seen > STALE_SECONDS]
            for mac in stale:
                del self._devices[mac]
            return list(self._devices.values())
