"""Monitor-mode arayuzlerden 802.11 cerceve yakalama ve RSSI cikarma.

ONEMLI - mimari secimi: Antenler AYNI ANDA degil, SIRAYLA (rotasyonla)
dinlenir. Once 4 anten icin 4 ayri thread/AsyncSniffer denendi, sonra
scapy'nin yerlesik coklu-arayuz destegiyle (tek thread, tek select()
dongusu) tek AsyncSniffer denendi - IKISI DE ayni sonucu verdi: 4 antenden
sadece 1'i veri teslim ediyor, digerleri hicbir hata/istisna vermeden
sessizce hic paket almiyor. Buna karsin TEK bir anten HER ZAMAN (senkron
sniff() ile izole test edildiginde) guvenilir calisti - bu chipset'in
(rtl8xxxu) surucusunun/donanim yolunun ayni anda birden fazla ornekten
veri teslim etmede bir sinirlamasi/hatasi oldugunu gosteriyor, thread
sayisi ya da select() modelinden bagimsiz.

Bu yuzden kanitlanmis guvenilir yontemi kullaniyoruz: her seferinde SADECE
BIR antenden DWELL_SECONDS kadar dinleyip, sirayla digerine geciyoruz. Uzun
vadede (bir kac saniyede) tum yonlerden veri toplanmis olur; aggregator.py
bu rotasyonu kapsayacak genislikte bir pencere (WINDOW_SECONDS) kullanarak
"ayni an" varsayimini korur.
"""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass

from scapy.all import sniff
from scapy.layers.dot11 import Dot11, Dot11Beacon, Dot11ProbeResp, Dot11Elt, RadioTap

DWELL_SECONDS = 2.5  # her yonde bu kadar sure dinlenir, sonra siradakine gecilir
# NOT: kisa degerler (orn. 0.7s) denendi ve basarisiz oldu - soket her acilista
# adaptorun fiilen veri almaya baslamasi icin bir isinma suresi gerekiyor gibi
# gorunuyor (izole 4 saniyelik senkron testler guvenilir calisiyordu).

# UYARLANABILIR DWELL: 4 adaptor de AYNI USB hub'ini (genelde tek bir Full-
# Speed/12Mbit Transaction Translator'i) paylastigi icin, hub'in port'lar
# arasi zamanlama/adalet davranisi bir yonu digerlerine gore SISTEMATIK
# olarak ac  durumda tutabilir - o yonun anteni/sinyali saglikli olsa bile,
# scapy'nin o yondeki dwell penceresinde teslim aldigi paket sayisi digerlerine
# gore kalici olarak dusuk kalabilir (surucu/cekirdek seviyesinde /proc/net/dev
# sayaclari NORMAL gorunse bile - yani sinyal degil, USB teslimati sorunu).
# Bunu telafi etmek icin her yonun son birkac turdaki paket/saniye hizini
# takip edip, grup ortalamasina gore surekli geride kalan yone rotasyon
# donusunu cok uzatmadan (ust sinirla) ekstra dinleme suresi veriyoruz.
MAX_DWELL_SECONDS = 5.0    # zayif yon icin ust sinir (rotasyon turunu asiri uzatmasin diye)
RATE_EMA_ALPHA = 0.3        # yon basina paket/saniye hizinin ustel hareketli ortalama agirligi
WEAK_RATIO_THRESHOLD = 0.5  # grup ortalamasinin bu oranindan daha yavassa "zayif" sayilir


@dataclass
class Sample:
    direction: str      # "front" | "right" | "back" | "left"
    mac: str             # yayin yapan cihazin (BSSID/kaynak) MAC adresi
    rssi: float           # dBm cinsinden anlik sinyal seviyesi
    channel: int | None
    ssid: str | None
    timestamp: float


def _extract_ssid(pkt) -> str | None:
    if pkt.haslayer(Dot11Elt):
        elt = pkt.getlayer(Dot11Elt)
        if elt.ID == 0 and elt.info:
            try:
                return elt.info.decode(errors="replace")
            except Exception:
                return None
    return None


class CaptureManager:
    """4 yonu rotasyonla dinleyip ortak bir Sample kuyrugu uretir."""

    def __init__(self, interfaces: dict[str, str]):
        # Sinirli boyut: eger tuketen taraf (Tracker'in arka plan bosaltma
        # thread'i) herhangi bir nedenle geri kalirsa kuyruk sinirsizca
        # buyumesin - en yeni ornekler onemli oldugu icin dolduysa en eskiyi
        # atip yeniyi eklemek, kuyruk asiri eski/bayat veriyle tikanmaktan
        # iyidir.
        self.out_queue: "queue.Queue[Sample]" = queue.Queue(maxsize=5000)
        self._interfaces = dict(interfaces)  # yon -> arayuz adi
        self._stats: dict[str, dict] = {
            d: {"total": 0, "dot11": 0, "has_mac": 0, "radiotap": 0, "rssi": 0}
            for d in interfaces
        }
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._last_error: str | None = None
        self._rate_ema: dict[str, float] = {d: 0.0 for d in interfaces}  # yon -> paket/saniye (EMA)

    def _on_packet(self, pkt, direction: str) -> None:
        s = self._stats[direction]
        s["total"] += 1
        if not pkt.haslayer(Dot11):
            return
        s["dot11"] += 1
        dot11 = pkt.getlayer(Dot11)
        # Sadece yararli yayin/veri cerceveleri: beacon, probe response, veya herhangi bir data/mgmt
        mac = dot11.addr2 or dot11.addr3
        if not mac:
            return
        s["has_mac"] += 1
        if not pkt.haslayer(RadioTap):
            return
        s["radiotap"] += 1
        radiotap = pkt.getlayer(RadioTap)
        rssi = getattr(radiotap, "dBm_AntSignal", None)
        if rssi is None:
            return
        s["rssi"] += 1
        ssid = _extract_ssid(pkt) if pkt.haslayer(Dot11Beacon) or pkt.haslayer(Dot11ProbeResp) else None
        sample = Sample(
            direction=direction,
            mac=mac,
            rssi=float(rssi),
            channel=getattr(radiotap, "Channel", None),
            ssid=ssid,
            timestamp=time.time(),
        )
        try:
            self.out_queue.put_nowait(sample)
        except queue.Full:
            try:
                self.out_queue.get_nowait()  # en eskiyi at, yerine yeniyi koy
            except queue.Empty:
                pass
            try:
                self.out_queue.put_nowait(sample)
            except queue.Full:
                pass

    def _compute_dwell(self, direction: str) -> float:
        """Grup ortalamasina gore surekli geride kalan yone (bkz. dosya basindaki
        UYARLANABILIR DWELL notu) sinirli bir ek dinleme suresi verir."""
        own_rate = self._rate_ema[direction]
        others = [v for d, v in self._rate_ema.items() if d != direction and v > 0]
        if own_rate <= 0 or not others:
            return DWELL_SECONDS  # henuz yeterli olcum yok, varsayilanla basla
        avg_others = sum(others) / len(others)
        if avg_others <= 0:
            return DWELL_SECONDS
        ratio = own_rate / avg_others
        if ratio >= WEAK_RATIO_THRESHOLD:
            return DWELL_SECONDS  # normal performans, ek sureye gerek yok
        bonus_factor = min(MAX_DWELL_SECONDS / DWELL_SECONDS, WEAK_RATIO_THRESHOLD / max(ratio, 0.05))
        return min(MAX_DWELL_SECONDS, DWELL_SECONDS * bonus_factor)

    def _cycle_loop(self) -> None:
        directions = list(self._interfaces.keys())
        i = 0
        while not self._stop_event.is_set():
            direction = directions[i % len(directions)]
            iface = self._interfaces[direction]
            dwell = self._compute_dwell(direction)
            before = self._stats[direction]["total"]
            t0 = time.time()
            try:
                sniff(
                    iface=iface,
                    timeout=dwell,
                    prn=lambda pkt, d=direction: self._on_packet(pkt, d),
                    store=False,
                )
                self._last_error = None
            except Exception as e:
                self._last_error = f"{type(e).__name__}: {e}"
                time.sleep(0.3)  # arayuz gecici olarak yoksa (usb reset vb.) sik sik ugrasmayi yavaslat
            elapsed = time.time() - t0
            if elapsed > 0:
                got = self._stats[direction]["total"] - before
                rate = got / elapsed
                prev = self._rate_ema[direction]
                self._rate_ema[direction] = rate if prev <= 0 else (1 - RATE_EMA_ALPHA) * prev + RATE_EMA_ALPHA * rate
            i += 1

    def start(self) -> None:
        # USB sifirlama/yeniden takma, arayuzu YENI bir kernel ifindex ile
        # yeniden yaratir; scapy'nin arayuz onbellegi (conf.ifaces) bunu
        # kendiliginden fark etmez ve eski (artik gecersiz) ifindex'e
        # baglanmaya calisip 'OSError: [Errno 19] No such device' ile
        # sessizce basarisiz olabilir. Her baslatmada onbellegi tazele.
        try:
            from scapy.interfaces import conf as iface_conf
            iface_conf.ifaces.reload()
        except Exception:
            pass

        for d in self._stats:
            self._stats[d] = {"total": 0, "dot11": 0, "has_mac": 0, "radiotap": 0, "rssi": 0}
            self._rate_ema[d] = 0.0
        self._last_error = None
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._cycle_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=DWELL_SECONDS + 2.0)
            self._thread = None

    def __enter__(self) -> "CaptureManager":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()

    def stats(self) -> dict[str, dict]:
        running = self._thread is not None and self._thread.is_alive()
        return {
            d: {
                **s, "running": running, "exception": self._last_error,
                # tanisal amacli: bu yonun son olculen paket/sn hizi ve
                # (bkz. UYARLANABILIR DWELL) o hiza gore su an ayrilan sure.
                "rate_pps": round(self._rate_ema[d], 1),
                "dwell_s": round(self._compute_dwell(d), 1),
            }
            for d, s in self._stats.items()
        }
