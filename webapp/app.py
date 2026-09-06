#!/usr/bin/env python3
"""NetBearing Console - tek surecli uygulama.

Onceden bu uygulama iki ayri surec olarak calisiyordu: yetkisiz bir Flask
sunucusu (server.py) ve root'ta calisan bir yardimci daemon (helperd.py),
aralarinda bir Unix socket protokolu ile konusuyorlardi. Bu ayrim, tek
kullanicili/kendi makinesinde calisan bir arac icin gereksiz karmasiklik ve
kirilganlik yaratti (surec senkronizasyonu, "yardimci calismiyor" durumlari,
yeniden baslatma sirasinda eski/yeni surec karisikligi). Artik HER SEY
(paket yakalama + web arayuzu) TEK bir surecte, dogrudan root olarak
calisiyor - baslatilirken 'pkexec' ile bir kez sifre sorulur, o kadar.

Kullanim (dogrudan degil, start_gui.sh uzerinden):
    pkexec <venv>/bin/python3 webapp/app.py
"""

from __future__ import annotations

import json
import os
import re
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from flask import Flask, jsonify, request, send_from_directory  # noqa: E402

from wifidf.aggregator import Aggregator  # noqa: E402
from wifidf.bearing import (  # noqa: E402
    DEFAULT_CALIBRATION_PATH, GainPattern, _angle_diff, load_pattern, save_pattern,
)
from wifidf.capture import CaptureManager  # noqa: E402
from wifidf.config import DeviceConfig, DIRECTIONS  # noqa: E402
from wifidf.distance import (  # noqa: E402
    PATH_LOSS_CALIBRATION_PATH, PathLossModel, best_signal_rssi, load_path_loss_model, save_path_loss_model,
)
from wifidf.station_log import DEFAULT_LOG_PATH, load_observations_by_mac  # noqa: E402
from wifidf.tracker import Tracker  # noqa: E402
from wifidf.triangulate import BearingObservation, fix_position  # noqa: E402

import numpy as np  # noqa: E402

HOST = "127.0.0.1"
PORT = 5757


# ---------------------------------------------------------------------------
# Sistem yardimcilari
# ---------------------------------------------------------------------------

def _iw_dev_info() -> dict[str, dict]:
    out = subprocess.run(["iw", "dev"], capture_output=True, text=True).stdout
    info: dict[str, dict] = {}
    cur = None
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("phy#"):
            cur = None  # yeni phy blogu: onceki arayuzun "type" alanini kirletebilecek
            # takip eden "Unnamed/non-netdev interface" (P2P-device) satirlarini onlemek icin sifirla
        if s.startswith("Interface "):
            cur = s.split("Interface ", 1)[1].strip()
            info[cur] = {}
        elif s.startswith("type ") and cur and "type" not in info[cur]:
            # ilk "type" satiri kazanir; ayni phy'deki sonraki Unnamed/P2P-device
            # bloklari (varsa) cur'u kirletmesin diye tekrar yazilmaz.
            info[cur]["type"] = s.split("type ", 1)[1].strip()
    return info


def _id_path_of(iface: str) -> str:
    out = subprocess.run(
        ["udevadm", "info", "-q", "property", "-p", f"/sys/class/net/{iface}"],
        capture_output=True, text=True, check=True,
    ).stdout
    for line in out.splitlines():
        if line.startswith("ID_PATH="):
            return line.split("=", 1)[1]
    raise RuntimeError(f"{iface} icin ID_PATH bulunamadi")


def _permanent_mac_of(iface: str) -> str | None:
    try:
        out = subprocess.run(["ethtool", "-P", iface], capture_output=True, text=True, check=True).stdout
        for line in out.splitlines():
            if "Permanent address" in line:
                return line.split("Permanent address:", 1)[1].strip()
    except Exception:
        pass
    return None


def _freq_to_channel(freq_mhz: int) -> int:
    if freq_mhz == 2484:
        return 14
    return (freq_mhz - 2407) // 5


def _usb_busid_of(iface: str) -> str | None:
    """'wlandf_front' -> '3-1.2' gibi USB fiziksel bus/device kimligi.

    rtl8xxxu suruculu bu adaptorlerde monitor modda RX'in bir sure sonra
    sessizce durmasi (Errno 100 / donmus /proc/net/dev sayaclari) bilinen
    bir kisit; fiziksel cikar-tak bunu duzeltir. USB unbind/bind ile ayni
    seyi yazilimla, kullanici mudahalesi olmadan yapabiliriz.
    """
    try:
        link = os.readlink(f"/sys/class/net/{iface}/device")
    except OSError:
        return None
    basename = os.path.basename(link)  # orn. "3-1.2:1.0"
    return basename.split(":")[0] if basename else None


# ---------------------------------------------------------------------------
# Durum
# ---------------------------------------------------------------------------

class AppState:
    def __init__(self):
        self.cfg = DeviceConfig.load()
        self.pattern = load_pattern()
        self.path_loss = load_path_loss_model()
        self.tracker: Tracker | None = None
        self.identify_baseline: set[str] = set()
        self.identify_mapping: dict[str, dict] = {}
        self.identifying: bool = False  # True iken bekci (watchdog) devre disi - bkz. _watchdog_loop
        self.identifying_since: float | None = None  # yarida kalmis/unutulmus bir tanimlama bekciyi SONSUZA dek kilitlemesin diye (bkz. IDENTIFY_TIMEOUT_S)
        self.calibration_rounds: list[dict] = []
        self.solo_rounds: dict[str, list[dict]] = {}  # tak-cikar kalibrasyonu: yon -> [{"delta","rssi"}]
        self.distance_rounds: list[dict] = []  # mesafe kalibrasyonu: [{"distance_m","rssi"}]
        self.auto_heal_count: int = 0
        self.last_auto_heal: float | None = None
        self.lock = threading.RLock()


state = AppState()


# ---------------------------------------------------------------------------
# Komut isleyicileri (state, params) -> JSON-uyumlu veri
# ---------------------------------------------------------------------------

def h_shutdown(state: AppState, params: dict):
    """Guncelleme/yeniden baslatma icin: kisa bir gecikmeyle sureci kapatir
    (cevap once gonderilir). Kullanici masaustu ikonuna tekrar tiklayarak
    (pkexec ile) yeniden baslatir.
    """
    def _exit():
        time.sleep(0.3)
        os._exit(0)
    threading.Thread(target=_exit, daemon=True).start()
    return "ok"


def h_status(state: AppState, params: dict):
    lsusb = subprocess.run(["lsusb"], capture_output=True, text=True).stdout
    adapter_count = len(re.findall(r"2357:010c", lsusb))
    info = _iw_dev_info()
    expected = {f"wlandf_{d}" for d in DIRECTIONS}
    present = set(info.keys()) & expected
    mapped = all(state.cfg.antennas[d].id_path for d in DIRECTIONS)
    modes = {d: info.get(f"wlandf_{d}", {}).get("type") for d in DIRECTIONS}
    return {
        "adapter_count": adapter_count,
        "antennas_mapped": mapped,
        "interfaces_present": sorted(present),
        "interface_modes": modes,
        "channel": state.cfg.channel,
        "tracking_active": state.tracker is not None,
        "calibration_done": DEFAULT_CALIBRATION_PATH.exists(),
        "distance_calibration_done": PATH_LOSS_CALIBRATION_PATH.exists(),
        "auto_heal_count": state.auto_heal_count,
        "last_auto_heal": state.last_auto_heal,
        "identifying": state.identifying,
    }


def h_install_alt_driver(state: AppState, params: dict):
    """rtl8xxxu (in-tree) suruculunun bu cipsette monitor modda surekli
    veri akisini koruyamamasi bilinen bir kisit; bunun yerine aircrack-ng
    toplulugunun bakimini yaptigi rtl8188eus (out-of-tree) suruculu DKMS
    ile kurup bu 4 USB adaptoru ona gecirir. Laptop'un kendi Wi-Fi'si
    (iwlwifi) farkli bir surucu oldugu icin etkilenmez.
    """
    user_home = ROOT.parent.parent  # .../Projeler/wifi-df -> .../Projeler -> ev dizini
    src = user_home / "rtl8188eus"
    if not (src / "dkms-install.sh").exists():
        raise RuntimeError(f"Surucu kaynagi bulunamadi: {src}")

    _stop_tracker_if_running(state)

    # Onceki (basarisiz) bir denemeden kalma DKMS kaydi/kopyasi varsa temizle;
    # aksi halde dkms-install.sh'nin 'cp -r' adimi eski kopyanin ICINE
    # ic ice bir klasor olusturur ve guncel (yamali) kaynak hic derlenmez.
    subprocess.run(["dkms", "remove", "-m", "8188eu", "-v", "5.3.9", "--all"], capture_output=True, text=True)
    subprocess.run(["rm", "-rf", "/usr/src/8188eu-5.3.9"])

    result = subprocess.run(
        ["bash", "dkms-install.sh"], cwd=str(src), capture_output=True, text=True, timeout=300,
    )
    log_tail = (result.stdout[-1500:] + "\n" + result.stderr[-1500:]).strip()
    if result.returncode != 0:
        raise RuntimeError(f"DKMS kurulumu basarisiz (exit={result.returncode}):\n{log_tail}")

    subprocess.run(["modprobe", "-r", "rtl8xxxu"])
    time.sleep(1)
    r2 = subprocess.run(["modprobe", "8188eu"], capture_output=True, text=True)
    if r2.returncode != 0:
        subprocess.run(["modprobe", "rtl8xxxu"])  # eski surucuyu geri yukle, sistemi bozuk birakma
        raise RuntimeError(f"Yeni surucu (8188eu) yuklenemedi, eskiye donuldu: {r2.stderr}")

    time.sleep(2)
    subprocess.run(["udevadm", "trigger", "--action=add", "-s", "net"])
    time.sleep(2)

    info = _iw_dev_info()
    present = sorted(set(info.keys()) & {f"wlandf_{d}" for d in DIRECTIONS})
    return {"install_log_tail": log_tail[-1000:], "interfaces_present": present}


def h_install_rules(state: AppState, params: dict):
    rules_file = ROOT / "setup" / "99-wifi-df.rules"
    nm_file = ROOT / "setup" / "99-wifi-df-unmanaged.conf"
    if not rules_file.exists():
        raise RuntimeError("Once anten tanimlama tamamlanmali (identify_finish)")
    subprocess.run(["cp", str(rules_file), "/etc/udev/rules.d/"], check=True)
    subprocess.run(["udevadm", "control", "--reload-rules"])
    subprocess.run(["udevadm", "trigger", "--action=add", "-s", "net"])
    if nm_file.exists():
        os.makedirs("/etc/NetworkManager/conf.d", exist_ok=True)
        subprocess.run(["cp", str(nm_file), "/etc/NetworkManager/conf.d/"], check=True)
        subprocess.run(["systemctl", "reload", "NetworkManager"])
    return "ok"


def h_identify_reset(state: AppState, params: dict):
    # ONEMLI: izleme calisirken bekci (watchdog), "yeterli anten aktif
    # degil" diye algilayip beklenmedik bir USB sifirlamasi tetikleyebilir -
    # tam da kullanici adaptorleri elle takip cikardigi bu sirada arayuzlerin
    # kaybolup/geri gelmesi identify_check'in "hangisi yeni takildi"
    # tespitini karistirir. Tanimlama boyunca izlemeyi (ve dolayisiyla
    # bekciyi) tamamen durdur.
    _stop_tracker_if_running(state)
    state.identifying = True
    state.identifying_since = time.time()
    info = _iw_dev_info()
    state.identify_baseline = set(info.keys())
    state.identify_mapping = {}
    return {"baseline": sorted(state.identify_baseline)}


def h_identify_check(state: AppState, params: dict):
    direction = params["direction"]
    info = _iw_dev_info()
    current = set(info.keys())
    new = current - state.identify_baseline
    if not new:
        return {"found": False}
    iface = sorted(new)[0]
    id_path = _id_path_of(iface)
    mac = _permanent_mac_of(iface)
    state.identify_mapping[direction] = {"id_path": id_path, "mac": mac, "iface": iface}
    state.identify_baseline.add(iface)
    return {"found": True, "iface": iface, "id_path": id_path, "mac": mac}


def h_identify_finish(state: AppState, params: dict):
    missing = [d for d in DIRECTIONS if d not in state.identify_mapping]
    if missing:
        raise RuntimeError(f"Eksik yonler: {missing}")

    rules_file = ROOT / "setup" / "99-wifi-df.rules"
    nm_file = ROOT / "setup" / "99-wifi-df-unmanaged.conf"

    lines = [
        "# Otomatik uretildi: webapp/app.py (identify_finish)",
        "# Eslesme MAC'e degil USB fiziksel port yoluna (ID_PATH) gore yapilir.",
        "",
    ]
    for d, info in state.identify_mapping.items():
        lines.append(f'SUBSYSTEM=="net", ACTION=="add", ENV{{ID_PATH}}=="{info["id_path"]}", NAME="wlandf_{d}"')
    rules_file.write_text("\n".join(lines) + "\n")

    nm_file.write_text(
        "[keyfile]\nunmanaged-devices=interface-name:wlandf_*\n"
    )

    cfg = DeviceConfig.default()
    for d, info in state.identify_mapping.items():
        cfg.antennas[d].mac = info["mac"]
        cfg.antennas[d].id_path = info["id_path"]
    cfg.save()
    state.cfg = cfg

    h_install_rules(state, {})
    time.sleep(2)
    state.identifying = False
    state.identifying_since = None
    return "ok"


def _stop_tracker_if_running(state: AppState) -> None:
    """Arayuz modu/kanali degistirilmeden once cagrilir: acik paket-yakalama
    soketleri, arayuz down/up edildiginde ('Network is down') sessizce
    olur ve bir daha kendiliginden dirilmez - bu yuzden once durdurulur,
    sonraki start_tracking cagrisi ile taze soketlerle yeniden kurulur.
    """
    if state.tracker is not None:
        state.tracker.stop()
        state.tracker = None


def _apply_monitor_mode(state: AppState, channel) -> None:
    for d in DIRECTIONS:
        ifc = f"wlandf_{d}"
        subprocess.run(["ip", "link", "set", ifc, "down"])
        subprocess.run(["iw", "dev", ifc, "set", "type", "monitor"])
        subprocess.run(["ip", "link", "set", ifc, "up"])
        if channel:
            subprocess.run(["iw", "dev", ifc, "set", "channel", str(channel)])
    state.cfg.channel = int(channel) if channel else None
    state.cfg.save()
    time.sleep(0.5)  # arayuzlerin "up" durumuna tam gecmesi icin kisa payanda


def _targeted_heal(state: AppState, directions: list[str]) -> None:
    """Belirtilen anten(ler)i, TUM izlemeyi durdurmadan/Tracker'i yeniden
    olusturmadan sifirlar ve yeniden monitor moda alir.

    CaptureManager'in rotasyon dongusu her turda ilgili arayuzu scapy
    uzerinden YENIDEN coz (her seferinde taze bir sniff() cagrisi, kalici
    bir soket degil) - bu yuzden Tracker'i yeniden baslatmaya GEREK YOK;
    sadece USB'yi sifirlayip modu/kanali yeniden uygulamak ve scapy'nin
    arayuz onbellegini tazelemek yeterli. Bu, TUM antenleri sifirlayip
    Tracker'i yeniden kuran tam onarima gore hem cok daha hizli (sadece
    bozulanlar icin ~3.5sn/anten) hem de calisan diger antenleri kesintiye
    ugratmaz.
    """
    channel = state.cfg.channel
    busids = sorted({b for d in directions if (b := _usb_busid_of(f"wlandf_{d}"))})
    for busid in busids:
        try:
            with open("/sys/bus/usb/drivers/usb/unbind", "w") as f:
                f.write(busid)
        except OSError:
            pass
        time.sleep(1)
        try:
            with open("/sys/bus/usb/drivers/usb/bind", "w") as f:
                f.write(busid)
        except OSError:
            pass
        time.sleep(2.5)

    subprocess.run(["udevadm", "trigger", "--action=add", "-s", "net"])
    time.sleep(1.5)

    for d in directions:
        ifc = f"wlandf_{d}"
        subprocess.run(["ip", "link", "set", ifc, "down"])
        subprocess.run(["iw", "dev", ifc, "set", "type", "monitor"])
        subprocess.run(["ip", "link", "set", ifc, "up"])
        if channel:
            subprocess.run(["iw", "dev", ifc, "set", "channel", str(channel)])

    try:
        from scapy.interfaces import conf as iface_conf
        iface_conf.ifaces.reload()
    except Exception:
        pass


def h_usb_reset(state: AppState, params: dict) -> dict:
    _stop_tracker_if_running(state)

    requested = params.get("directions") or list(DIRECTIONS)
    busids = []
    for d in requested:
        busid = _usb_busid_of(f"wlandf_{d}")
        if busid:
            busids.append(busid)
    busids = sorted(set(busids))
    if not busids:
        raise RuntimeError("Adaptorlerin USB kimligi bulunamadi (takili mi?)")

    # Hepsini AYNI ANDA unbind/bind etmek, ayni USB hub uzerinde 4 ozdes
    # cipin firmware yuklemesini yaristirip cogunun sessizce basarisiz
    # olmasina yol acabiliyor. Bu yuzden her adaptoru TEKER TEKER, aralarinda
    # yeterli sure birakarak sifirla.
    for busid in busids:
        try:
            with open("/sys/bus/usb/drivers/usb/unbind", "w") as f:
                f.write(busid)
        except OSError:
            pass
        time.sleep(1)
        try:
            with open("/sys/bus/usb/drivers/usb/bind", "w") as f:
                f.write(busid)
        except OSError:
            pass
        time.sleep(2.5)  # firmware yukleme + arayuz olusmasi icin payanda

    subprocess.run(["udevadm", "trigger", "--action=add", "-s", "net"])
    time.sleep(2)

    info = _iw_dev_info()
    present = sorted(set(info.keys()) & {f"wlandf_{d}" for d in DIRECTIONS})
    return {"busids": busids, "interfaces_present": present}


# ---------------------------------------------------------------------------
# Bekci (watchdog): rtl8xxxu'nun bilinen kisiti - monitor modda RX bir sure
# sonra sessizce durabiliyor, ne yazilimla (iw/ip) ne de sureç yeniden
# baslatmayla kendiliginden dirilmiyor, sadece USB seviyesinde tam sifirlama
# (fiziksel cikar-tak veya onun yazilimsal esdegeri) duzeltiyor. Bunu artik
# kullanicinin fark edip elle tetiklemesi yerine, arka planda periyodik
# olarak paket sayaclarini kontrol edip kendiliginden yapiyoruz.
# ---------------------------------------------------------------------------

WATCHDOG_INTERVAL_S = 10.0   # bir tam rotasyon turunu (~10sn) rahatca kapsayan kontrol araligi
WATCHDOG_GRACE_S = 15.0      # izleme yeni baslamissa bu kadar bekle, henuz kontrol etme
WATCHDOG_MIN_GAP_S = 15.0    # iki otomatik onarim arasi en az bu kadar sure birak (hedefli onarim hizli oldugu icin kisa tutulabilir)
IDENTIFY_PAUSE_TIMEOUT_S = 300.0  # yarida kalmis/unutulmus bir tanimlama bekciyi SONSUZA dek kilitlemesin


def _watchdog_loop() -> None:
    prev_totals: dict[str, int] | None = None
    tracker_started_at: float | None = None
    last_heal_at = 0.0

    while True:
        time.sleep(WATCHDOG_INTERVAL_S)
        with state.lock:
            identify_stuck = (
                state.identifying
                and state.identifying_since is not None
                and time.time() - state.identifying_since > IDENTIFY_PAUSE_TIMEOUT_S
            )
            if state.identifying and not identify_stuck:
                # Anten tanimlama surerken (Kurulum) mudahale etme - USB
                # sifirlama, kullanicinin o an elle takip cikardigi
                # adaptorlerin tespitini karistirir. AMA: tanimlama yarida
                # birakilip unutulmussa (hata, sekme kapatma vb.) bu bayrak
                # sonsuza dek takili kalip bekciyi tamamen devre disi
                # birakmasin diye bir zaman asimindan sonra yoksayilir.
                prev_totals = None
                tracker_started_at = None
                continue

            tracker = state.tracker
            if tracker is None:
                prev_totals = None
                tracker_started_at = None
                continue

            now = time.time()
            if tracker_started_at is None:
                tracker_started_at = now
            if now - tracker_started_at < WATCHDOG_GRACE_S:
                continue

            stats = tracker.capture_stats()
            totals = {d: s.get("total", 0) for d, s in stats.items()}

            if prev_totals is None:
                prev_totals = totals
                continue  # ilk olcum, henuz karsilastirma yapilamaz

            stalled_dirs = [d for d in DIRECTIONS if totals.get(d, 0) <= prev_totals.get(d, 0)]
            prev_totals = totals

            if not stalled_dirs or (now - last_heal_at) < WATCHDOG_MIN_GAP_S:
                continue

            try:
                if len(stalled_dirs) <= 2:
                    # 1-2 anten takilmis: sadece onlari, TUM izlemeyi
                    # kesmeden hedefli olarak onar (cok daha hizli, digerlerini
                    # rahatsiz etmez).
                    _targeted_heal(state, stalled_dirs)
                else:
                    # Cogu/tumu takilmis: hedefli onarimlar birbiri ardina
                    # gecikecegi icin (her biri ~3.5sn) tam sifirlama daha
                    # hizli VE daha guvenilir sonuc verir.
                    saved_channel = state.cfg.channel
                    h_usb_reset(state, {})
                    _apply_monitor_mode(state, saved_channel)
                    state.tracker = Tracker(state.cfg, state.pattern, state.path_loss)
                    state.tracker.start()
                    tracker_started_at = time.time()
            except Exception:
                state.tracker = None  # bir dahaki taramada temiz baslasin

            state.auto_heal_count += 1
            state.last_auto_heal = now
            last_heal_at = now
            prev_totals = None


def h_scan(state: AppState, params: dict):
    was_tracking = state.tracker is not None
    saved_channel = state.cfg.channel
    _stop_tracker_if_running(state)

    iface = params.get("iface", "wlandf_front")
    subprocess.run(["ip", "link", "set", iface, "down"])
    subprocess.run(["iw", "dev", iface, "set", "type", "managed"])
    subprocess.run(["ip", "link", "set", iface, "up"])
    time.sleep(1)
    res = subprocess.run(["iw", "dev", iface, "scan"], capture_output=True, text=True)
    scan_failed = res.returncode != 0

    networks: list[dict] = []
    if not scan_failed:
        by_ssid: dict[str, int] = {}
        ssid = None
        freq = None
        for line in res.stdout.splitlines():
            line = line.strip()
            if line.startswith("freq: "):
                # 'iw' bazi surumlerde ondalikli yazdirir (orn. "2412.0"); ilk
                # sayisal parcayi al ve tam sayiya yuvarla.
                raw = line.split("freq: ", 1)[1].split()[0]
                freq = int(round(float(raw)))
            elif line.startswith("SSID: "):
                ssid = line.split("SSID: ", 1)[1].strip()
            if ssid and freq:
                by_ssid[ssid] = freq
                ssid, freq = None, None
        networks = [{"ssid": s, "channel": _freq_to_channel(f)} for s, f in sorted(by_ssid.items())]

    # Tarama, izlemeyi aktifken yapildiysa: onceki kanala/monitor moda geri
    # don ve izlemeyi otomatik devam ettir - "Aglari Tara" canli takibi
    # kalici olarak durdurmasin diye.
    if was_tracking:
        _apply_monitor_mode(state, saved_channel)
        state.tracker = Tracker(state.cfg, state.pattern, state.path_loss)
        state.tracker.start()

    if scan_failed:
        raise RuntimeError(f"Tarama basarisiz: {res.stderr.strip()}")
    return {"networks": networks}


def h_monitor_mode(state: AppState, params: dict):
    _stop_tracker_if_running(state)
    _apply_monitor_mode(state, params.get("channel"))
    return "ok"


def h_start_tracking(state: AppState, params: dict):
    if state.tracker is None:
        state.pattern = load_pattern()
        state.path_loss = load_path_loss_model()
        state.tracker = Tracker(state.cfg, state.pattern, state.path_loss)
        state.tracker.start()
    return "ok"


def h_stop_tracking(state: AppState, params: dict):
    if state.tracker is not None:
        state.tracker.stop()
        state.tracker = None
    return "ok"


def h_capture_stats(state: AppState, params: dict):
    """Sorun giderme: her arayuzde kac paket goruldu, kacinda Dot11/RadioTap/RSSI var."""
    if state.tracker is None:
        raise RuntimeError("Once izleme baslatilmali")
    return {"stats": state.tracker.capture_stats()}


def h_debug_sniff(state: AppState, params: dict):
    """Ileri tanilama: AsyncSniffer/Tracker'i devre disi birakip, senkron
    scapy.sniff() ile dogrudan ham yakalama dener.
    """
    from scapy.all import sniff
    from scapy.interfaces import conf as iface_conf
    iface_conf.ifaces.reload()
    iface = params.get("iface", "wlandf_front")
    duration = float(params.get("duration", 5.0))
    try:
        pkts = sniff(iface=iface, timeout=duration, store=True)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "count": 0}
    summary = [p.summary() for p in pkts[:5]]
    return {"count": len(pkts), "sample_summaries": summary}


def h_get_devices(state: AppState, params: dict):
    if state.tracker is None:
        return {"devices": []}
    devices = state.tracker.poll()
    out = []
    for d in devices:
        out.append({
            "mac": d.mac,
            "ssid": d.ssid,
            "readings": d.readings,
            "bearing_deg": d.bearing.bearing_deg if d.bearing else None,
            "smoothed_bearing_deg": d.smoothed_bearing_deg,
            "confidence": d.bearing.confidence if d.bearing else None,
            "locked": d.locked,
            "stable_count": d.stable_count,
            "concentration": d.concentration,
            "compass": d.compass,
            "distance_m": d.distance_m,
            "last_seen": d.last_seen,
            "last_known_bearing_deg": d.last_known_bearing_deg,
            "last_known_compass": d.last_known_compass,
            "last_known_distance_m": d.last_known_distance_m,
            "last_known_locked": d.last_known_locked,
            "last_known_stable_count": d.last_known_stable_count,
            "last_known_concentration": d.last_known_concentration,
            "last_known_confidence": d.last_known_confidence,
        })
    return {"devices": out}


def h_calibration_reset(state: AppState, params: dict):
    state.calibration_rounds = []
    return "ok"


def h_calibration_step(state: AppState, params: dict):
    if state.tracker is None:
        raise RuntimeError("Once izleme baslatilmali (monitor mode ayarlandiktan sonra)")
    angle = float(params["angle"])
    mac_param = (params.get("mac") or "").strip().lower()
    # NOT: varsayilan sure onceden 5sn idi; antenler AYNI ANDA degil
    # ROTASYONLA dinlendigi icin (bkz. capture.py) bir tam tur ~10sn surer -
    # 5sn bazi antenlerin sirasi hic gelmeden bitip yanlislikla "yetersiz
    # okuma" hatasi veriyordu. Bir tam turu rahatça kapsayacak sure gerekir.
    duration = float(params.get("duration", 12.0))

    end = time.time() + duration
    last_snapshot = []
    while time.time() < end:
        last_snapshot = state.tracker.poll()
        time.sleep(0.3)

    if mac_param:
        target = next((d for d in last_snapshot if d.mac.lower() == mac_param), None)
    else:
        # Referans verici kalibrasyon sirasinda antenin hemen onunde/cok
        # yakininda tutulur - bu yuzden en guclu goruleni odur. Elle MAC
        # girmeye/secmeye gerek kalmadan otomatik bulunur.
        candidates = [d for d in last_snapshot if d.readings]
        target = max(candidates, key=lambda d: max(d.readings.values()), default=None)

    if target is None or len(target.readings) < 3:
        found = len(target.readings) if target else 0
        raise RuntimeError(f"Yetersiz okuma ({found}/4 anten). Referans verici görünüyor mu, kanal doğru mu?")

    state.calibration_rounds.append({"angle": angle, "readings": target.readings})
    return {
        "readings": target.readings, "rounds_done": len(state.calibration_rounds),
        "mac": target.mac, "ssid": target.ssid,
    }


def h_calibration_add_round(state: AppState, params: dict):
    """Dogrulama adimindan gelen bilinen-aci + gercek-zamanli okuma ciftini
    (zaten elde mevcut, yeniden yakalamaya gerek yok) dogrudan kalibrasyon
    veri noktasi olarak ekler. Boylece kullanici sistemi normal kullanirken
    dogruladigi her nokta, kalibrasyonu da kademeli olarak iyilestirir.
    """
    angle = float(params["angle"])
    readings = params.get("readings") or {}
    readings = {d: float(r) for d, r in readings.items() if d in DIRECTIONS}
    if len(readings) < 3:
        raise RuntimeError(f"Yetersiz okuma ({len(readings)}/4 anten) - bu nokta kalibrasyona eklenemedi.")
    state.calibration_rounds.append({"angle": angle, "readings": readings})
    return {"rounds_done": len(state.calibration_rounds)}


def _collect_calibration_points(state: AppState) -> tuple[list[float], list[float]]:
    """Kalibrasyon icin TUM kaynaklardan (Basit/Hassas/Dogrulama VE Tak-Cikar)
    biriken veriyi TEK bir (delta, deger) setinde birlestirir.

    ONEMLI - tutarlilik: eskiden 'Basit/Hassas/Dogrulama' (state.calibration_rounds)
    ve 'Tak-Cikar' (state.solo_rounds) TAMAMEN AYRI depolarda tutuluyor ve
    her modun kendi 'Hesapla/Tamamla' butonu SADECE kendi deposunu kullanip
    digerini sessizce gormezden geliyordu - bu da hangi yontemi EN SON
    kullandiginiza gore degisen, tutarsiz sonuclara yol aciyordu. Artik
    HANGI moddan 'Hesapla' cagrilirsa cagrilsin, TUM birikmis veri (her iki
    kaynaktan da) birlikte kullanilir.
    """
    boresights = {d: state.cfg.antennas[d].boresight_deg for d in DIRECTIONS}
    deltas: list[float] = []
    values: list[float] = []

    for r in state.calibration_rounds:
        readings = r["readings"]
        round_mean = statistics.mean(readings.values())
        for direction, rssi in readings.items():
            deltas.append(_angle_diff(r["angle"], boresights[direction]))
            values.append(rssi - round_mean)

    for direction, rounds in state.solo_rounds.items():
        if len(rounds) < 2:
            continue
        mean_rssi = statistics.mean(r["rssi"] for r in rounds)
        for r in rounds:
            deltas.append(r["delta"])
            values.append(r["rssi"] - mean_rssi)

    return deltas, values


def _fit_and_save_pattern(state: AppState, deltas: list[float], values: list[float]) -> GainPattern:
    pattern = GainPattern.fit(np.array(deltas), np.array(values))
    save_pattern(pattern)
    state.pattern = pattern
    if state.tracker is not None:
        state.tracker.pattern = pattern
    return pattern


def h_calibration_finish(state: AppState, params: dict):
    deltas, values = _collect_calibration_points(state)
    if len(deltas) < 8:  # ~ en az birkac farkli aci/anten kombinasyonu
        raise RuntimeError(
            f"Yeterli kalibrasyon verisi yok (su an {len(deltas)} nokta). "
            "En az 4 farkli acida (Basit/Hassas/Dogrulama) veya 3 antende (Tak-Cikar) olcum yapin."
        )
    pattern = _fit_and_save_pattern(state, deltas, values)
    return pattern.to_dict()


# ---------------------------------------------------------------------------
# Tak-cikar (tek anten) kalibrasyonu - bkz. modul dokstring'i (grup 4)
# ---------------------------------------------------------------------------

def h_solo_calibration_reset(state: AppState, params: dict):
    state.solo_rounds = {}
    return "ok"


def h_solo_calibration_step(state: AppState, params: dict):
    direction = params["direction"]
    if direction not in DIRECTIONS:
        raise RuntimeError(f"Gecersiz yon: {direction}")
    mac_param = (params.get("mac") or "").strip().lower()
    delta = float(params["delta"])
    duration = float(params.get("duration", 5.0))
    iface = f"wlandf_{direction}"

    agg = Aggregator()
    manager = CaptureManager({direction: iface})
    manager.start()
    try:
        end = time.time() + duration
        while time.time() < end:
            agg.drain_queue(manager.out_queue)
            time.sleep(0.3)
        agg.drain_queue(manager.out_queue)
    finally:
        manager.stop()

    now = time.time()
    target_mac = mac_param or None
    if target_mac is None:
        # Referans verici antenin hemen onunde tutulur - en guclu goruleni
        # odur, elle MAC girmeye gerek yok.
        best_rssi = float("-inf")
        for dev in agg.snapshot():
            r = dev.readings(now, window=duration + 1.0).get(direction)
            if r is not None and r > best_rssi:
                best_rssi = r
                target_mac = dev.mac

    rssi = None
    ssid = None
    if target_mac:
        for dev in agg.snapshot():
            if dev.mac.lower() == target_mac.lower():
                readings = dev.readings(now, window=duration + 1.0)
                rssi = readings.get(direction)
                ssid = dev.ssid

    if rssi is None:
        raise RuntimeError(
            f"'{direction}' anteninde ({iface}) hicbir cihaz gorulmedi. "
            "Sadece bu adaptor takili mi, referans yayinda mi?"
        )

    state.solo_rounds.setdefault(direction, []).append({"delta": delta, "rssi": rssi})
    return {"rssi": rssi, "count": len(state.solo_rounds[direction]), "mac": target_mac, "ssid": ssid}


def h_solo_calibration_finish(state: AppState, params: dict):
    # NOT: 'Basit/Hassas/Dogrulama' verisiyle AYNI havuzdan (bkz.
    # _collect_calibration_points) hesaplar - hangi moddan "Hesapla/
    # Tamamla" basilirsa basilsin sonuc ayni, birikmis TUM veriyi kullanir.
    deltas, values = _collect_calibration_points(state)
    if len(deltas) < 8:
        raise RuntimeError(
            f"Yeterli kalibrasyon verisi yok (su an {len(deltas)} nokta). "
            "En az 3 farkli antende (her birinde en az 2 olcum) veya 4 farkli acida veri gerekli."
        )
    pattern = _fit_and_save_pattern(state, deltas, values)
    return pattern.to_dict()


# ---------------------------------------------------------------------------
# Mesafe kalibrasyonu: RSSI -> metre modelini (log-distance yol kaybi)
# gercek olculmus (mesafe, RSSI) ciftlerinden fitler. Kalibre edilmemis
# varsayilan degerler (rssi_ref_1m=-40, n=2.5) bu spesifik donanim/ortam
# icin dogru olmayabilir; en az 2 farkli bilinen mesafede olcum yapilirsa
# gercege cok daha yakin bir mesafe tahmini elde edilir.
# ---------------------------------------------------------------------------

def h_distance_calib_reset(state: AppState, params: dict):
    state.distance_rounds = []
    return "ok"


def h_distance_calib_step(state: AppState, params: dict):
    if state.tracker is None:
        raise RuntimeError("Once izleme baslatilmali")
    mac = params["mac"].strip().lower()
    distance_m = float(params["distance_m"])
    if distance_m <= 0:
        raise RuntimeError("Mesafe pozitif olmali")
    duration = float(params.get("duration", 5.0))

    end = time.time() + duration
    best_rssi = None
    while time.time() < end:
        for d in state.tracker.poll():
            if d.mac.lower() == mac and d.readings:
                r = best_signal_rssi(d.readings)
                if best_rssi is None or r > best_rssi:
                    best_rssi = r
        time.sleep(0.3)

    if best_rssi is None:
        raise RuntimeError("Hedef MAC bu sure icinde gorulmedi.")

    state.distance_rounds.append({"distance_m": distance_m, "rssi": best_rssi})
    return {"rssi": best_rssi, "count": len(state.distance_rounds)}


def h_distance_calib_finish(state: AppState, params: dict):
    if len(state.distance_rounds) < 2:
        raise RuntimeError("En az 2 farkli mesafede olcum gerekli")

    xs = np.array([np.log10(r["distance_m"]) for r in state.distance_rounds])
    ys = np.array([r["rssi"] for r in state.distance_rounds])
    slope, intercept = np.polyfit(xs, ys, 1)
    n = max(0.5, float(-slope / 10.0))
    model = PathLossModel(rssi_ref_1m=float(intercept), path_loss_exponent=n)
    save_path_loss_model(model)
    state.path_loss = model
    if state.tracker is not None:
        state.tracker.path_loss = model
    state.distance_rounds = []
    return model.to_dict()


def h_record_station(state: AppState, params: dict):
    if state.tracker is None:
        raise RuntimeError("Once izleme baslatilmali")
    x = float(params["x"])
    y = float(params["y"])
    duration = float(params.get("duration", 8.0))

    end = time.time() + duration
    devices = []
    while time.time() < end:
        devices = state.tracker.poll()
        time.sleep(0.5)

    DEFAULT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with DEFAULT_LOG_PATH.open("a") as f:
        for d in devices:
            if not d.bearing:
                continue
            rec = {
                "timestamp": time.time(), "station_x": x, "station_y": y,
                "mac": d.mac, "ssid": d.ssid,
                "bearing_deg": d.bearing.bearing_deg, "confidence": d.bearing.confidence,
            }
            f.write(json.dumps(rec) + "\n")
            count += 1
    return {"count": count}


def h_fix_targets(state: AppState, params: dict):
    by_mac = load_observations_by_mac()
    results = []
    for mac, recs in by_mac.items():
        obs = [
            BearingObservation(
                station_x=r["station_x"], station_y=r["station_y"],
                bearing_deg=r["bearing_deg"], weight=r.get("confidence", 1.0),
            )
            for r in recs
        ]
        stations = {(o.station_x, o.station_y) for o in obs}
        ssid = recs[-1].get("ssid") or "-"
        if len(stations) < 2:
            results.append({"mac": mac, "ssid": ssid, "ok": False, "reason": f"sadece {len(stations)} istasyon"})
            continue
        fix = fix_position(obs)
        if fix is None:
            results.append({"mac": mac, "ssid": ssid, "ok": False, "reason": "kesisim hesaplanamadi"})
            continue
        results.append({
            "mac": mac, "ssid": ssid, "ok": True, "x": fix.x, "y": fix.y,
            "residual": fix.residual, "spread_deg": fix.spread_deg, "stations": len(stations),
        })
    return {"results": results}


HANDLERS = {
    "status": h_status,
    "shutdown": h_shutdown,
    "install_rules": h_install_rules,
    "install_alt_driver": h_install_alt_driver,
    "usb_reset": h_usb_reset,
    "identify_reset": h_identify_reset,
    "identify_check": h_identify_check,
    "identify_finish": h_identify_finish,
    "scan": h_scan,
    "monitor_mode": h_monitor_mode,
    "start_tracking": h_start_tracking,
    "stop_tracking": h_stop_tracking,
    "get_devices": h_get_devices,
    "capture_stats": h_capture_stats,
    "debug_sniff": h_debug_sniff,
    "calibration_reset": h_calibration_reset,
    "calibration_step": h_calibration_step,
    "calibration_finish": h_calibration_finish,
    "calibration_add_round": h_calibration_add_round,
    "solo_calibration_reset": h_solo_calibration_reset,
    "solo_calibration_step": h_solo_calibration_step,
    "solo_calibration_finish": h_solo_calibration_finish,
    "distance_calib_reset": h_distance_calib_reset,
    "distance_calib_step": h_distance_calib_step,
    "distance_calib_finish": h_distance_calib_finish,
    "record_station": h_record_station,
    "fix_targets": h_fix_targets,
}


# ---------------------------------------------------------------------------
# Flask
# ---------------------------------------------------------------------------

app = Flask(__name__, static_folder=str(ROOT / "webapp" / "static"), static_url_path="")


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/call/<action>", methods=["POST"])
def api_call(action: str):
    handler = HANDLERS.get(action)
    if handler is None:
        return jsonify({"ok": False, "error": f"bilinmeyen komut: {action}"}), 400
    params = request.get_json(silent=True) or {}
    try:
        with state.lock:
            data = handler(state, params)
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


def main() -> None:
    if os.geteuid() != 0:
        print("[!] Bu uygulama root olarak calistirilmalidir (paket yakalama + arayuz "
              "ayarlari icin gerekli). start_gui.sh'i kullanin (pkexec ile baslatir).", file=sys.stderr)
        sys.exit(1)
    threading.Thread(target=_watchdog_loop, daemon=True).start()
    app.run(host=HOST, port=PORT, debug=False, threaded=True)


if __name__ == "__main__":
    main()
