"""Coklu-istasyon (veya coklu-konum) yon (bearing) olcumlerinden konum kesisimi.

Bu, RDF/fox-hunting pratiginde kullanilan standart yontemdir: cihaz farkli
en az 2 noktaya tasinir (veya birden fazla sabit istasyon kurulur), her
noktada hedefe olan yon (bearing) olculur ve bu dogrularin en-kucuk-kareler
kesisim noktasi hesaplanir. Tek istasyondaki RSSI-mesafe kestirimine gore
COK DAHA YUKSEK DOGRULUK saglar.

Koordinat sistemi: duzlemsel (x=Dogu, y=Kuzey), metre cinsinden. Bearing
acisi Kuzey'den saat yonunde derece (standart pusula acisi) olarak verilir;
antenlerin "on" referansi kurulumda gercek Kuzey'e (veya sabit bir referansa)
hizalanmalidir ki istasyonlar arasi bearing'ler ayni koordinat sistemine
otursun.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class BearingObservation:
    station_x: float       # istasyon/olcum konumu, metre (Dogu)
    station_y: float       # istasyon/olcum konumu, metre (Kuzey)
    bearing_deg: float     # hedefe olan yon, Kuzey'den saat yonunde derece
    weight: float = 1.0    # guven agirligi (orn. BearingResult.confidence)


@dataclass
class FixResult:
    x: float
    y: float
    residual: float          # agirlikli artik kare hata toplami
    spread_deg: float        # gozlemler arasi aci tutarliligi (kaba belirsizlik gostergesi)


def fix_position(observations: list[BearingObservation]) -> FixResult | None:
    if len(observations) < 2:
        return None

    rows = []
    rhs = []
    weights = []
    for obs in observations:
        rad = np.deg2rad(obs.bearing_deg)
        dx, dy = np.sin(rad), np.cos(rad)   # yon vektoru (Dogu, Kuzey)
        nx, ny = -dy, dx                      # normal vektor
        rows.append([nx, ny])
        rhs.append(nx * obs.station_x + ny * obs.station_y)
        weights.append(obs.weight)

    A = np.array(rows)
    b = np.array(rhs)
    W = np.diag(weights)

    # Agirlikli en kucuk kareler: (A^T W A) p = A^T W b
    AtW = A.T @ W
    try:
        p = np.linalg.solve(AtW @ A, AtW @ b)
    except np.linalg.LinAlgError:
        return None  # dogrular (yaklasik) paralel, kesisim belirsiz

    residual = float(np.sum(weights * (A @ p - b) ** 2))
    spread = float(np.std([o.bearing_deg for o in observations]))

    return FixResult(x=float(p[0]), y=float(p[1]), residual=residual, spread_deg=spread)
