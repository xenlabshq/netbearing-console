"""Donanim gerektirmeyen sentetik dogrulama: bilinen bir aciya gore uretilen
RSSI degerlerinden estimate_bearing()'in dogru aciyi geri bulup bulmadigini
kontrol eder.

Calistirma: python3 -m pytest tests/ -v   (veya) python3 tests/test_bearing.py
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wifidf.bearing import BearingSmoother, GainPattern, _angle_diff, estimate_bearing

BORESIGHTS = {"front": 0.0, "right": 90.0, "back": 180.0, "left": 270.0}
PATTERN = GainPattern(g_max=0.0, g_min=-15.0, n=1.5)


def _simulate_readings(true_bearing: float, tx_power: float = -50.0, noise: dict | None = None) -> dict:
    readings = {}
    for d, bsight in BORESIGHTS.items():
        delta = _angle_diff(true_bearing, bsight)
        rssi = tx_power + PATTERN.gain(delta)
        if noise:
            rssi += noise.get(d, 0.0)
        readings[d] = rssi
    return readings


def test_exact_bearings_no_noise():
    for true_bearing in [0, 45, 90, 135, 180, 225, 270, 315, 37, 163]:
        readings = _simulate_readings(true_bearing)
        result = estimate_bearing(readings, BORESIGHTS, PATTERN, step_deg=0.5)
        assert result is not None
        err = abs(_angle_diff(result.bearing_deg, true_bearing))
        assert err <= 1.0, f"bearing={true_bearing} -> tahmin={result.bearing_deg} (hata={err:.2f})"


def test_robust_to_small_noise():
    noise = {"front": 1.5, "right": -1.0, "back": 0.5, "left": -0.8}
    for true_bearing in [20, 110, 200, 290]:
        readings = _simulate_readings(true_bearing, noise=noise)
        result = estimate_bearing(readings, BORESIGHTS, PATTERN, step_deg=0.5)
        assert result is not None
        err = abs(_angle_diff(result.bearing_deg, true_bearing))
        assert err <= 8.0, f"bearing={true_bearing} -> tahmin={result.bearing_deg} (hata={err:.2f})"


def test_missing_one_antenna_still_works():
    readings = _simulate_readings(60.0)
    del readings["left"]  # sadece 3 anten
    result = estimate_bearing(readings, BORESIGHTS, PATTERN, step_deg=0.5)
    assert result is not None
    err = abs(_angle_diff(result.bearing_deg, 60.0))
    assert err <= 3.0


def test_insufficient_antennas_returns_none():
    readings = _simulate_readings(60.0)
    for k in ["left", "back"]:
        del readings[k]
    assert estimate_bearing(readings, BORESIGHTS, PATTERN) is None


# --- BearingSmoother (dairesel Kalman filtresi) testleri ---------------------

def test_smoother_converges_and_locks_under_noise():
    """Gurultulu ama tutarli (yuksek guvenli) okumalar altinda filtre gercek
    aciya yakinsamali VE bir sure sonra kilitlenmeli."""
    rng = random.Random(42)
    smoother = BearingSmoother()
    true_bearing = 200.0
    result = None
    for _ in range(40):
        noisy = (true_bearing + rng.uniform(-6, 6)) % 360
        result = smoother.update(noisy, confidence=0.8)
    assert result is not None
    err = abs(_angle_diff(result.deg, true_bearing))
    assert err <= 5.0, f"yakinsama hatasi cok buyuk: {err:.2f}"
    assert result.locked, "tutarli, yuksek guvenli okumalar sonunda kilitlenmeliydi"
    assert result.concentration >= 0.75


def test_smoother_rejects_low_confidence_outlier():
    """Tutarli okumalarla kilitlenmis bir filtreye TEK, dusuk guvenli ve
    cok uzak (aykiri) bir okuma verilirse, tahmin neredeyse hic kaymamali -
    outlier gate'in isini yaptigini dogrular (bkz. OTLU PENUR near-field
    vakasi: yakin mesafede boyle dusuk-guvenli/sapkin okumalar olabiliyor)."""
    smoother = BearingSmoother()
    for _ in range(10):
        smoother.update(50.0, confidence=0.8)
    before = smoother.update(50.0, confidence=0.8).deg

    after = smoother.update(220.0, confidence=0.05)  # cok uzak + cok dusuk guven
    err = abs(_angle_diff(after.deg, before))
    assert err <= 10.0, f"aykiri deger filtreyi fazla sicratti: {err:.2f} derece kaydi"


def test_smoother_high_confidence_outlier_is_trusted():
    """Ayni buyuk sicrama YUKSEK guvenle gelirse (gercek bir yon degisimi
    olabilir), filtre bunu bir aykiri deger gibi bastirmamali - makul
    sayida guncellemeden sonra yeni aciya yakinsamali."""
    smoother = BearingSmoother()
    for _ in range(10):
        smoother.update(50.0, confidence=0.8)
    result = None
    for _ in range(15):
        result = smoother.update(220.0, confidence=0.8)
    err = abs(_angle_diff(result.deg, 220.0))
    assert err <= 15.0, f"yuksek guvenli yeni yone yakinsamadi: {err:.2f} derece hata"


def test_smoother_handles_wrap_around():
    """0/360 siniri gecisinde (dairesel) sicrama olmamali - dogrudan aci
    ortalamasi alsaydik (350+10)/2=180 gibi yanlis bir sonuc cikardi."""
    smoother = BearingSmoother()
    smoother.update(350.0, confidence=0.8)
    result = smoother.update(10.0, confidence=0.8)
    # dogru dairesel ortalama 0/360 civarinda olmali, 180 civarinda DEGIL
    assert abs(_angle_diff(result.deg, 0.0)) <= 20.0, f"sinir sarmasi hatali ele alindi: {result.deg}"


if __name__ == "__main__":
    test_exact_bearings_no_noise()
    test_robust_to_small_noise()
    test_missing_one_antenna_still_works()
    test_insufficient_antennas_returns_none()
    test_smoother_converges_and_locks_under_noise()
    test_smoother_rejects_low_confidence_outlier()
    test_smoother_high_confidence_outlier_is_trusted()
    test_smoother_handles_wrap_around()
    print("Tum testler gecti.")
