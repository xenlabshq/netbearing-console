"""Genlik-karsilastirmali yon bulma (amplitude-comparison DF).

Yontem: 4 sabit yonelimli anten (0, 90, 180, 270 derece boresight) ayni
konumda oldugundan, bir vericinin her antendeki RSSI'si sadece o antenin
kazanc paterni ile aciklanabilir (mesafe/yol kaybi terimi tum antenlerde
ortak oldugundan bilinmeyen bir sabit (C) olarak modellenir):

    RSSI_i(phi) = C + G(phi - boresight_i)

G(.), kalibrasyonla olculen anten kazanc paternidir (derece -> dB, goreli).
Bilinmeyen varis acisi phi, olculen 4 RSSI degerine en iyi uyan (en kucuk
kareler) aci taranarak bulunur; C her aci adayi icin kapali-form ile
(kalanlarin ortalamasi) hesaplanir, ayrica optimizasyon degiskeni degildir.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from wifidf.aggregator import Kalman1D
from wifidf.config import CALIBRATION_DIR, DIRECTIONS


def _angle_diff(a: float, b: float) -> float:
    """[-180, 180] araligina normalize edilmis en kisa aci farki."""
    d = (a - b + 180.0) % 360.0 - 180.0
    return d


@dataclass
class GainPattern:
    """Kosinus-kuvvet modeli ile kalibre edilmis anten kazanc paterni.

    G(delta) = g_min + (g_max - g_min) * ((1 + cos(delta)) / 2) ** n
    delta: hedefin, antenin baktigi yone gore aci farki (derece).
    """

    g_max: float = 0.0    # boresight'taki goreli kazanc (dB, referans=0)
    g_min: float = -20.0  # tam arkadaki (180 derece) goreli kazanc (dB)
    n: float = 1.0        # sekil/keskinlik ustel katsayisi

    def gain(self, delta_deg: float) -> float:
        rad = np.deg2rad(delta_deg)
        shape = ((1.0 + np.cos(rad)) / 2.0) ** self.n
        return self.g_min + (self.g_max - self.g_min) * shape

    @classmethod
    def fit(cls, deltas_deg: np.ndarray, relative_rssi: np.ndarray) -> "GainPattern":
        """Kalibrasyon verisinden (delta_aci -> goreli RSSI) en iyi n, g_min, g_max degerlerini bulur."""
        best: GainPattern | None = None
        best_err = float("inf")
        g_max = float(np.max(relative_rssi))
        g_min_candidates = np.linspace(np.min(relative_rssi) - 5, g_max - 1, 30)
        n_candidates = np.linspace(0.3, 4.0, 30)
        for g_min in g_min_candidates:
            for n in n_candidates:
                cand = cls(g_max=g_max, g_min=float(g_min), n=float(n))
                pred = np.array([cand.gain(d) for d in deltas_deg])
                err = float(np.sum((pred - relative_rssi) ** 2))
                if err < best_err:
                    best_err = err
                    best = cand
        assert best is not None
        return best

    def to_dict(self) -> dict:
        return {"g_max": self.g_max, "g_min": self.g_min, "n": self.n}

    @classmethod
    def from_dict(cls, d: dict) -> "GainPattern":
        return cls(g_max=d["g_max"], g_min=d["g_min"], n=d["n"])


DEFAULT_CALIBRATION_PATH = CALIBRATION_DIR / "gain_pattern.json"


def load_pattern(path: Path = DEFAULT_CALIBRATION_PATH) -> GainPattern:
    if not path.exists():
        # Kalibrasyon yapilmamissa kaba bir varsayilan patch anten paterni kullan.
        return GainPattern(g_max=0.0, g_min=-12.0, n=1.2)
    return GainPattern.from_dict(json.loads(path.read_text()))


def save_pattern(pattern: GainPattern, path: Path = DEFAULT_CALIBRATION_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(pattern.to_dict(), indent=2))


@dataclass
class BearingResult:
    bearing_deg: float       # tahmini varis acisi (0=on referans, saat yonunde)
    confidence: float        # 0..1 arasi kaba guven skoru (kalan hataya dayali)
    residual: float          # en iyi acidaki artik kare hata toplami


def estimate_bearing(
    readings: dict[str, float],
    boresights: dict[str, float],
    pattern: GainPattern,
    step_deg: float = 0.5,
) -> BearingResult | None:
    """En az 3 yonden RSSI okumasi verildiginde en olasi varis acisini dondurur."""
    dirs = [d for d in DIRECTIONS if d in readings]
    if len(dirs) < 3:
        return None

    rssi = np.array([readings[d] for d in dirs])       # (k,)
    bsight = np.array([boresights[d] for d in dirs])     # (k,)

    # Not: bu tarama, poll basina HER cihaz icin calisir (dakikada onlarca
    # cihaz x saniyede bir poll) - 720 adayligi bir Python dongusu yerine
    # tek bir vektorel NumPy islemiyle yapmak ayni sonucu cok daha hizli
    # uretir.
    candidates = np.arange(0.0, 360.0, step_deg)          # (m,)
    diff = candidates[:, None] - bsight[None, :]            # (m,k)
    deltas = (diff + 180.0) % 360.0 - 180.0                   # _angle_diff'in vektorel hali
    g = pattern.gain(deltas)                                    # (m,k)
    c = np.mean(rssi[None, :] - g, axis=1, keepdims=True)          # (m,1) - her aday icin kapali-form nuisance
    pred = c + g
    err = np.sum((pred - rssi[None, :]) ** 2, axis=1)                # (m,)

    best_idx = int(np.argmin(err))
    best_phi = float(candidates[best_idx])
    best_err = float(err[best_idx])

    # Guven skoru: R^2 tipi "aciklanan varyans orani" - fit'in, yonler arasi
    # GOZLENEN RSSI farkliliginin ne kadarini acikladigini olcer. ONEMLI:
    # mutlak dB olceginden BAGIMSIZDIR. Eski yaklasim (sabit "20 dB^2" esigine
    # dayali exp(-hata/20)) cok yakin mesafede (orn. ~1m) sorunluydu: cok
    # yakindaki bir verici, kalibre edilmis anten paterninin (g_max-g_min)
    # tipik dinamik araligini asan buyuk gercek RSSI farklari (25-30dB+)
    # uretebiliyor - yon aslinda acik/tutarli sekilde bulunmus olsa bile
    # (bkz. best_phi), bu sabit esik guveni yapay olarak neredeyse sifira
    # dusuruyor ve kullanicidan "cihazi bulamadi" gibi gorunuyordu. R^2 ise
    # "yonler arasi farklarin sekli ne kadar iyi aciklaniyor" sorusuna
    # odaklandigi icin, mutlak fark buyuk olsa da (yakin mesafe) fit sekli
    # tutarliysa yuksek kalir.
    mean_rssi = float(np.mean(rssi))
    ss_tot = float(np.sum((rssi - mean_rssi) ** 2))
    if ss_tot < 1e-6:
        # tum yonler pratikte ayni RSSI'yi goruyor (aci ayirt edilemez durumda).
        confidence = 1.0 if best_err < 1e-6 else 0.0
    else:
        r2 = 1.0 - best_err / ss_tot
        confidence = float(np.clip(r2, 0.0, 1.0))
    return BearingResult(bearing_deg=best_phi, confidence=confidence, residual=best_err)


def bearing_to_compass(bearing_deg: float) -> str:
    """0=on (K kabul edilirse Kuzey), saat yonunde artan aciyi pusula yonune cevirir."""
    labels = ["K", "KD", "D", "GD", "G", "GB", "B", "KB"]
    idx = int(((bearing_deg + 22.5) % 360) // 45)
    return labels[idx]


@dataclass
class SmoothedBearing:
    deg: float             # dairesel olarak yumusatilmis yon (derece)
    locked: bool            # tutarlilik VE dusuk gurultu esikleri birlikte asildi mi
    stable_count: int        # su anki tutarli-okuma serisinin uzunlugu
    concentration: float      # 0..1 - filtrenin ic "dairesel tutarlilik" olcusu (bkz. asagisi)


class BearingSmoother:
    """Tek bir hedefin (MAC) zaman icindeki bearing okumalarini DAIRESEL
    KALMAN FILTRESI ile yumusatir ve kilit (locked) durumunu istatistiksel
    bir olcute dayandirir.

    Neden dairesel Kalman: aciyi (0-360 derece) dogrudan bir Kalman
    filtresiyle izlemek 350 -> 10 gibi sinir gecislerinde patlar (filtre
    "340 derecelik bir sicrama" sanir). Standart cozum - burada kullanilan -
    aciyi birim cember uzerindeki (cos, sin) bilesenlerine tasiyip bu IKI
    bileseni BAGIMSIZ birer 1-boyutlu Kalman filtresiyle (bkz.
    aggregator.Kalman1D - RSSI icin zaten kullanilan ayni sinif burada
    yeniden kullanilir) izlemek, her guncellemede atan2 ile aciya geri
    donmektir. Sinir sarmasi hic yasanmaz.

    Neden GUVENE (confidence) DUYARLI: eskiden her yeni okuma ayni sabit
    agirlikla (alpha=0.35) harmanlaniyordu - estimate_bearing()'in o an
    urettigi uyum kalitesi (orn. cok yakin mesafede near-field bozulmasi
    yasayan dusuk-guvenli bir okuma) tamamen goz ardi ediliyordu. Artik
    her guncellemede confidence, Kalman'in olcum gurultusu (R) parametresini
    ADAPTIF olarak ayarlar: dusuk guvenli bir okuma filtreyi ayni agirlikla
    degil, guvenilirligi kadar etkiler.

    Neden AYKIRI DEGER KAPISI (outlier gate): dusuk guvenli VE mevcut
    tahminden cok uzak (>outlier_gate_deg) tek bir okuma, byk olasilikla
    gecici bir bozulmadir (orn. anten USB darbogazi, near-field carpitmasi) -
    boyle bir ornekte olcum gurultusu asiri buyutulup etkisi neredeyse
    tamamen bogulur, filtre TEK kotu ornekle sicramaz.

    Neden concentration ILE kilit: eski yontem sadece "son N okuma birbirine
    yakin miydi" sayardi (stable_count) - bu, gurultu SEVIYESINI degil sadece
    YONUNU (tutarli mi degil mi) olcer. Filtrelenmis (x,y) vektorunun
    buyuklugu |sqrt(fx^2+fy^2)| ise dairesel istatistikte "ortalama sonuc
    uzunlugu" (mean resultant length) olarak bilinir ve 1'e ne kadar
    yakinsa (butun agirlikli ornekler ayni yonu gosteriyorsa) o kadar
    dusuk gurultu/yuksek tutarlilik anlamina gelir - stable_count'a gore
    cok daha ilkeli bir "ne kadar eminiz" olcusudur. Kilit artik HEM
    yeterli ardisik tutarlilik HEM de yeterli dairesel yogunluk gerektirir.

    Neden MANEVRA TESPITI (reorientation fast-reset): saf Kalman gecisi,
    guvenilirligi ne olursa olsun kucuk bir surec gurultusuyla (Q) yavas
    yavas yakinsar - bu, GURULTUYU iyi bastirir ama kullanici anteni elle
    FIZIKSEL olarak dondurdugunde (gercek, kalici bir yon degisikligi)
    goze batacak kadar GECIKMELI tepki verir (ilk raporlanan sikayet buydu).
    Bunu cozmek icin radar/hedef takip sistemlerinde "manevra tespiti"
    olarak bilinen teknik uygulanir: son birkac HAM (filtrelenmemis) okuma
    birbirine yakinsa VE hepsi mevcut filtrelenmis tahminden yeterince
    uzaktaysa, bu tek seferlik gurultu degil GERCEK bir yon degisikligidir -
    filtrenin yavas yavas yakinsamasini beklemek yerine durumu doğrudan bu
    yeni kumeye SIFIRLAR (aninda tepki). Tek, izole bir gurultulu okuma bu
    testi gecemez (ardisik birkac okumanin ayni yeni yonde ANLASMASI
    gerekir), boylece aykiri deger korumasi hala gecerlidir.
    """

    def __init__(
        self,
        process_var: float = 0.02,
        base_measurement_var: float = 0.05,
        lock_threshold_deg: float = 12.0,
        lock_count: int = 4,
        lock_concentration: float = 0.75,
        outlier_gate_deg: float = 100.0,
        outlier_confidence_max: float = 0.15,
        reorient_window: int = 3,
        reorient_cluster_deg: float = 20.0,
        reorient_threshold_deg: float = 35.0,
    ):
        self._kx = Kalman1D(process_var, base_measurement_var)
        self._ky = Kalman1D(process_var, base_measurement_var)
        self._base_r = base_measurement_var
        self._deg: float | None = None
        self._stable_count: int = 0
        self._raw_history: list[float] = []  # manevra tespiti icin son birkac HAM (filtrelenmemis) aci
        self.lock_threshold_deg = lock_threshold_deg
        self.lock_count = lock_count
        self.lock_concentration = lock_concentration
        self.outlier_gate_deg = outlier_gate_deg
        self.outlier_confidence_max = outlier_confidence_max
        self.reorient_window = reorient_window
        self.reorient_cluster_deg = reorient_cluster_deg
        self.reorient_threshold_deg = reorient_threshold_deg

    def _reset_to(self, deg: float) -> SmoothedBearing:
        """Filtre durumunu dogrudan bu aciya kurar (manevra tespiti sonrasi
        aninda "sicrama" icin) - sifirdan baslamis gibi davranir."""
        rad = np.deg2rad(deg)
        self._kx = Kalman1D(self._kx.q, self._base_r)
        self._ky = Kalman1D(self._ky.q, self._base_r)
        self._kx.update(np.cos(rad))
        self._ky.update(np.sin(rad))
        self._deg = deg
        self._stable_count = 1
        self._raw_history = [deg]
        return SmoothedBearing(self._deg, False, self._stable_count, 0.0)

    def update(self, new_deg: float, confidence: float | None = None) -> SmoothedBearing:
        if self._deg is None:
            # ilk ornek: filtreyi dogrudan bu deger uzerine kur, henuz "tutarlilik"
            # degerlendirilemez (karsilastirilacak onceki bir tahmin yok).
            return self._reset_to(new_deg)

        self._raw_history.append(new_deg)
        if len(self._raw_history) > self.reorient_window:
            self._raw_history.pop(0)

        # Manevra tespiti: bkz. sinif dokstring'i. Son birkac HAM okuma hem
        # birbirine yakin hem de mevcut tahminden uzaksa, yavas Kalman
        # yakinsamasini beklemeden dogrudan o yeni kumeye atla.
        if len(self._raw_history) == self.reorient_window:
            base = self._raw_history[0]
            spread = max(abs(_angle_diff(a, base)) for a in self._raw_history)
            far_from_current = all(abs(_angle_diff(a, self._deg)) >= self.reorient_threshold_deg for a in self._raw_history)
            if spread <= self.reorient_cluster_deg and far_from_current:
                xs = np.cos(np.deg2rad(self._raw_history))
                ys = np.sin(np.deg2rad(self._raw_history))
                cluster_deg = float(np.degrees(np.arctan2(np.mean(ys), np.mean(xs))) % 360)
                return self._reset_to(cluster_deg)

        diff = _angle_diff(new_deg, self._deg)
        self._stable_count = self._stable_count + 1 if abs(diff) <= self.lock_threshold_deg else 1

        conf = 0.5 if confidence is None else float(np.clip(confidence, 0.0, 1.0))
        if conf < self.outlier_confidence_max and abs(diff) > self.outlier_gate_deg:
            r = self._base_r * 25.0  # aykiri deger kapisi: bu ornegi neredeyse yoksay
        else:
            r = self._base_r * (1.0 + 4.0 * (1.0 - conf))  # dusuk guven -> daha buyuk olcum gurultusu
        self._kx.r = r
        self._ky.r = r

        rad = np.deg2rad(new_deg)
        fx = self._kx.update(np.cos(rad))
        fy = self._ky.update(np.sin(rad))
        self._deg = float(np.degrees(np.arctan2(fy, fx)) % 360)
        concentration = float(np.clip(np.hypot(fx, fy), 0.0, 1.0))

        locked = self._stable_count >= self.lock_count and concentration >= self.lock_concentration
        return SmoothedBearing(self._deg, locked, self._stable_count, concentration)
