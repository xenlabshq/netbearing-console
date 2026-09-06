"""Yakalama + agregasyon + yon-bulmayi birlestiren ana dongu."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from wifidf.aggregator import Aggregator, Kalman1D
from wifidf.bearing import (
    BearingResult, BearingSmoother, GainPattern, bearing_to_compass, estimate_bearing,
)
from wifidf.capture import CaptureManager
from wifidf.config import DeviceConfig
from wifidf.distance import PathLossModel, best_signal_rssi


@dataclass
class TrackedDevice:
    mac: str
    ssid: str | None
    readings: dict[str, float]           # SU AN (guncel pencerede) - bos ise sinyal su an yok. Ucgenleme/istasyon
    bearing: BearingResult | None         # kaydi gibi "gercekten simdi mi goruluyor" onemli olan yerler BUNLARI kullanmali.
    compass: str | None
    distance_m: float | None
    last_seen: float
    smoothed_bearing_deg: float | None = None
    locked: bool = False
    stable_count: int = 0
    concentration: float = 0.0  # 0..1 - Kalman filtresinin dairesel tutarlilik olcusu (bkz. BearingSmoother)
    # Sinyal GECICI olarak kesilse bile (readings/bearing yukarida bos/None
    # olsa bile) EN SON bilinen deger - SADECE goruntuleme icin (bkz.
    # Tracker.poll dokstring'i). Ucgenleme/kalibrasyon gibi "su an gercekten
    # goruluyor mu" onemli olan islemler bunlari DEGIL, yukaridaki guncel
    # alanlari kullanmalidir.
    last_known_bearing_deg: float | None = None
    last_known_compass: str | None = None
    last_known_distance_m: float | None = None
    # Ayni gerekce (bkz. yukarisi): rotasyonlu yakalamada bir yonun o anki
    # 12sn pencerede sans eseri taze ornegi olmayabilir (sinyal kesilmedigi
    # halde) - bu TEK pollde bearing=None doner ve locked/stable_count asagida
    # SIFIRA doner. Kullanici arayuzu ham locked/stable_count'u kullanirsa
    # gercekte kararli/kilitli bir cihaz her bir iki pollde bir "kilit
    # bozuldu" gibi titrer. last_known_* burada da ayni "sadece goruntuleme
    # icin" kuralla saglanir.
    last_known_locked: bool = False
    last_known_stable_count: int = 0
    last_known_concentration: float = 0.0
    last_known_confidence: float | None = None


class Tracker:
    DRAIN_INTERVAL_S = 0.3  # arka plan bosaltma dongusu araligi

    def __init__(self, cfg: DeviceConfig, pattern: GainPattern, path_loss: PathLossModel | None = None):
        self.cfg = cfg
        self.pattern = pattern
        self.path_loss = path_loss
        self.aggregator = Aggregator()
        self.manager = CaptureManager(cfg.interfaces())
        self._boresights = {d: a.boresight_deg for d, a in cfg.antennas.items()}
        self._smoothers: dict[str, BearingSmoother] = {}
        # Mesafe kestirimi RSSI'nin gurultulu, dogrusal-olmayan (log) bir
        # donusumu oldugundan, hangi anten "en guclu" oldugu poll'dan poll'a
        # (rotasyonlu yakalamada hangi yonlerin taze ornegi oldugu degistikce)
        # degisebilir - bu, mesafe DEGERININ gercekte sinyal sabit olsa bile
        # zikzak yapmasina yol acar. Ham RSSI'yi mesafeye cevirmeden ONCE
        # (dB uzayinda, RSSI gurultusunun yaklasik Gauss oldugu yerde)
        # Kalman ile yumusatmak, donusum SONRASI (mesafe uzayinda, gurultu
        # carpimsal/carpik oldugu icin) yumusatmaktan daha dogrudur.
        self._distance_rssi: dict[str, Kalman1D] = {}
        self._last_known: dict[str, dict] = {}  # mac -> {"bearing_deg","compass","distance_m"} (bkz. TrackedDevice)
        self._drain_thread: threading.Thread | None = None
        self._drain_stop = threading.Event()

    def start(self) -> None:
        self.manager.start()
        # ONEMLI: kuyruk bosaltma islemini HTTP isteklerine (poll()) birakirsak,
        # tarayici sekmesi kapatilip/arka plana atilip bir sure istek
        # yapilmadiginda kuyruk sinirsizca birikir; tekrar acilinca o eski
        # (bayat) ornekler "last_seen" olarak isaretlenip ANINDA "cok eski"
        # sayilip silinir - sonuc: cihaz listesi bombos gorunur. Bu yuzden
        # kuyruk, HTTP trafiginden BAGIMSIZ, surekli calisan bir arka plan
        # thread'inde duzenli olarak bosaltilir.
        self._drain_stop.clear()
        self._drain_thread = threading.Thread(target=self._drain_loop, daemon=True)
        self._drain_thread.start()

    def _drain_loop(self) -> None:
        while not self._drain_stop.is_set():
            self.aggregator.drain_queue(self.manager.out_queue, max_items=2000)
            time.sleep(self.DRAIN_INTERVAL_S)

    def stop(self) -> None:
        self._drain_stop.set()
        if self._drain_thread is not None:
            self._drain_thread.join(timeout=self.DRAIN_INTERVAL_S + 2.0)
            self._drain_thread = None
        self.manager.stop()

    def capture_stats(self) -> dict[str, dict]:
        return self.manager.stats()

    def poll(self) -> list[TrackedDevice]:
        """Kuyruktaki yeni ornekleri isler ve guncel cihaz listesini dondurur."""
        self.aggregator.drain_queue(self.manager.out_queue)
        now = time.time()
        out: list[TrackedDevice] = []
        seen_macs: set[str] = set()
        for dev in self.aggregator.snapshot():
            seen_macs.add(dev.mac)
            readings = dev.readings(now)
            bearing = estimate_bearing(readings, self._boresights, self.pattern)

            smoothed_deg = None
            locked = False
            stable_count = 0
            concentration = 0.0
            if bearing is not None:
                smoother = self._smoothers.setdefault(dev.mac, BearingSmoother())
                # confidence buraya aktarilir ki Kalman filtresi dusuk-guvenli
                # (orn. cok yakin mesafede near-field bozulmasi yasayan) bir
                # okumayi sabit agirlikla degil, guvenilirligi kadar
                # dikkate alsin (bkz. BearingSmoother docstring).
                smoothed = smoother.update(bearing.bearing_deg, bearing.confidence)
                smoothed_deg, locked, stable_count, concentration = (
                    smoothed.deg, smoothed.locked, smoothed.stable_count, smoothed.concentration
                )

            compass = bearing_to_compass(smoothed_deg if smoothed_deg is not None else bearing.bearing_deg) if bearing else None
            distance = None
            if readings and self.path_loss is not None:
                raw_rssi = best_signal_rssi(readings)
                rssi_smoother = self._distance_rssi.setdefault(dev.mac, Kalman1D(process_var=0.3, measurement_var=4.0))
                smoothed_rssi = rssi_smoother.update(raw_rssi)
                distance = self.path_loss.distance_m(smoothed_rssi)

            # "Son bilinen" degerleri SADECE gercekten TAZE bir sonuc
            # varken guncelle; sinyal kesildiginde (bearing=None) eski
            # deger oldugu gibi kalir - boylece goruntuleme tarafinda
            # gecici sinyal kaybinda yon/mesafe "-" olup kaybolmaz.
            if smoothed_deg is not None:
                self._last_known[dev.mac] = {
                    "bearing_deg": smoothed_deg, "compass": compass, "distance_m": distance,
                    "locked": locked, "stable_count": stable_count, "concentration": concentration,
                    "confidence": bearing.confidence if bearing is not None else None,
                }
            lk = self._last_known.get(dev.mac, {})

            out.append(
                TrackedDevice(
                    mac=dev.mac,
                    ssid=dev.ssid,
                    readings=readings,
                    bearing=bearing,
                    compass=compass,
                    distance_m=distance,
                    last_seen=dev.last_seen,
                    smoothed_bearing_deg=smoothed_deg,
                    locked=locked,
                    stable_count=stable_count,
                    concentration=concentration,
                    last_known_bearing_deg=lk.get("bearing_deg"),
                    last_known_compass=lk.get("compass"),
                    last_known_distance_m=lk.get("distance_m"),
                    last_known_locked=lk.get("locked", False),
                    last_known_stable_count=lk.get("stable_count", 0),
                    last_known_concentration=lk.get("concentration", 0.0),
                    last_known_confidence=lk.get("confidence"),
                )
            )
        # artik gorunmeyen (stale) cihazlarin smoother'larini biriktirmemek icin temizle.
        # _last_known de ayni sekilde temizlenir - ama sadece aggregator'in
        # kendisi cihazi TAMAMEN dustugunde (bkz. STALE_SECONDS, saatler
        # mertebesinde) - kisa sureli sinyal kesintilerinde seen_macs zaten
        # cihazi icerir (aggregator hala tutuyordur), son bilinen yon kalir.
        for mac in list(self._smoothers):
            if mac not in seen_macs:
                del self._smoothers[mac]
        for mac in list(self._distance_rssi):
            if mac not in seen_macs:
                del self._distance_rssi[mac]
        for mac in list(self._last_known):
            if mac not in seen_macs:
                del self._last_known[mac]
        out.sort(key=lambda d: d.last_seen, reverse=True)
        return out

    def __enter__(self) -> "Tracker":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()
