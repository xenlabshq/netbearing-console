#!/usr/bin/env python3
"""Kurulumu baştan sona kontrol eden ve otomatikleştiren sihirbaz.

Her adimi once KONTROL eder (zaten yapilmissa atlar), eksikse otomatik
yapar, ve tum adimlarin sonucunu zaman damgali olarak logs/wizard_*.log
dosyasina yazar. Fiziksel mudahale gereken adimlarda (adaptor takma,
sudo sifresi) sizden terminalde etkilesim ister.

Kullanim:
    python3 setup/wizard.py
"""

from __future__ import annotations

import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from wifidf.config import DeviceConfig, DIRECTIONS, TR_LABELS  # noqa: E402

try:
    from rich.console import Console
    from rich.table import Table
except ImportError:
    print("[!] 'rich' kurulu degil. Once: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)

console = Console()
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_PATH = LOG_DIR / f"wizard_{time.strftime('%Y%m%d_%H%M%S')}.log"
_log_file = LOG_PATH.open("a")


def log(msg: str, style: str = "") -> None:
    ts = time.strftime("%H:%M:%S")
    plain = re.sub(r"\[/?[a-zA-Z ]+\]", "", msg)  # rich etiketlerini temizleyip dosyaya yaz
    _log_file.write(f"[{ts}] {plain}\n")
    _log_file.flush()
    console.print(f"[dim]{ts}[/dim] {msg}" if not style else f"[dim]{ts}[/dim] [{style}]{msg}[/{style}]")


def ok(msg: str) -> None:
    log(f"[OK] {msg}", style="green")


def warn(msg: str) -> None:
    log(f"[UYARI] {msg}", style="yellow")


def fail(msg: str) -> None:
    log(f"[HATA] {msg}", style="red bold")


def step(title: str) -> None:
    console.rule(f"[bold cyan]{title}")
    _log_file.write(f"\n===== {title} =====\n")


def run(cmd: list[str], sudo: bool = False, capture: bool = True, check: bool = False):
    full = (["sudo"] + cmd) if sudo else cmd
    log(f"$ {' '.join(full)}")
    if capture:
        res = subprocess.run(full, capture_output=True, text=True)
        if res.stdout.strip():
            _log_file.write(res.stdout + "\n")
        if res.stderr.strip():
            _log_file.write(res.stderr + "\n")
        if check and res.returncode != 0:
            fail(f"Komut basarisiz (exit={res.returncode}): {' '.join(full)}")
        return res
    else:
        # etkilesimli (stdin/stdout kullanicida kalir), sudo sifresi burada sorulabilir
        res = subprocess.run(full)
        _log_file.write(f"(etkilesimli komut, exit={res.returncode})\n")
        return res


# ---------------------------------------------------------------------------
# 1) On kosullar
# ---------------------------------------------------------------------------

def check_prereqs() -> bool:
    step("1) On kosullar (Python paketleri)")
    missing = []
    for mod in ("scapy", "numpy", "rich"):
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if missing:
        fail(f"Eksik paketler: {', '.join(missing)}. Calistirin: pip install -r requirements.txt")
        return False
    ok("scapy, numpy, rich kurulu.")
    return True


# ---------------------------------------------------------------------------
# 2) USB adaptor sayisi
# ---------------------------------------------------------------------------

def check_adapters() -> int:
    step("2) USB Wi-Fi adaptorleri")
    res = run(["lsusb"])
    count = len(re.findall(r"2357:010c", res.stdout))
    if count == 0:
        warn("TL-WN722N v2/v3 (2357:010c) bulunamadi. lsusb ciktisinda farkli bir ID olabilir, devam ediliyor.")
    else:
        ok(f"{count} adet TL-WN722N v2/v3 adaptoru bulundu.")
    return count


# ---------------------------------------------------------------------------
# 3) Anten yon esleme (udev)
# ---------------------------------------------------------------------------

def _wifidf_interfaces_present() -> set[str]:
    res = run(["iw", "dev"])
    names = set(re.findall(r"Interface (wlandf_\w+)", res.stdout))
    return names


def _install_udev_and_nm_rules() -> None:
    rules_file = ROOT / "setup" / "99-wifi-df.rules"
    nm_file = ROOT / "setup" / "99-wifi-df-unmanaged.conf"
    if rules_file.exists():
        run(["cp", str(rules_file), "/etc/udev/rules.d/"], sudo=True, check=True)
        run(["udevadm", "control", "--reload-rules"], sudo=True)
        run(["udevadm", "trigger", "--action=add", "-s", "net"], sudo=True)
    if nm_file.exists():
        run(["mkdir", "-p", "/etc/NetworkManager/conf.d"], sudo=True)
        run(["cp", str(nm_file), "/etc/NetworkManager/conf.d/"], sudo=True, check=True)
        run(["systemctl", "reload", "NetworkManager"], sudo=True)


def ensure_antenna_mapping() -> bool:
    step("3) Anten <-> yon eslemesi (udev, ID_PATH bazli)")
    cfg = DeviceConfig.load()
    # id_path zorunlu alan: eski (MAC-bazli, artik guvenilmez) kayitlari "eksik" sayip yeniden calistirir.
    mapped = all(cfg.antennas[d].id_path for d in DIRECTIONS)
    present = _wifidf_interfaces_present()
    expected = {f"wlandf_{d}" for d in DIRECTIONS}

    if mapped and expected.issubset(present):
        ok("Antenler zaten eslenmis ve arayuzler dogru isimlerle gorunuyor: " + ", ".join(sorted(present)))
        return True

    if mapped and not expected.issubset(present):
        warn("Eslesme kayitli ama arayuzler henuz o isimlerle gorunmuyor; udev kurali/tetikleme deneniyor.")
        _install_udev_and_nm_rules()
        time.sleep(2)
        present = _wifidf_interfaces_present()
        if expected.issubset(present):
            ok("Arayuzler dogru isimlerle gorunuyor.")
            return True
        warn("Hala eksik. 4 adaptoru fiziksel olarak cikarip tekrar takin.")
        input("Hazir oldugunuzda ENTER'a basin...")
        present = _wifidf_interfaces_present()
        if expected.issubset(present):
            ok("Arayuzler dogru isimlerle gorunuyor.")
            return True
        fail(f"Hala eksik: {expected - present}")
        return False

    warn("Guncel (ID_PATH bazli) anten eslemesi bulunamadi. Interaktif tanimlama baslatiliyor (setup/identify_antennas.py).")
    console.print(
        "[yellow]Su an TUM adaptorleri cikarin, script sizden sirayla her yon icin adaptoru takmanizi isteyecek.[/yellow]"
    )
    input("Hazir oldugunuzda ENTER'a basin...")
    res = run(["python3", str(ROOT / "setup" / "identify_antennas.py")], sudo=True, capture=False)
    if res.returncode != 0:
        fail("identify_antennas.py basarisiz bitti.")
        return False

    _install_udev_and_nm_rules()
    time.sleep(2)
    present = _wifidf_interfaces_present()
    if not expected.issubset(present):
        warn("Kural kuruldu ama arayuzler henuz gorunmuyor; 4 adaptoru cikarip tekrar takin.")
        input("Hazir oldugunuzda ENTER'a basin...")
        present = _wifidf_interfaces_present()
    if expected.issubset(present):
        ok("Antenler basariyla eslesti: " + ", ".join(sorted(present)))
        return True
    fail(f"Eslesme tamamlanamadi: {expected - present}")
    return False


# ---------------------------------------------------------------------------
# 4) Hedef kanal secimi
# ---------------------------------------------------------------------------

def _freq_to_channel(freq_mhz: int) -> int:
    if freq_mhz == 2484:
        return 14
    return (freq_mhz - 2407) // 5


def choose_channel() -> int | None:
    step("4) Hedef Wi-Fi kanali secimi (2.4GHz tarama)")
    # Tarama sadece 'managed' modda calisir; sihirbaz onceki bir calistirmada
    # arayuzu zaten monitor moda almis olabilir - taramadan once garantiye alalim.
    run(["ip", "link", "set", "wlandf_front", "down"], sudo=True)
    run(["iw", "dev", "wlandf_front", "set", "type", "managed"], sudo=True)
    run(["ip", "link", "set", "wlandf_front", "up"], sudo=True)
    time.sleep(1)
    res = run(["iw", "dev", "wlandf_front", "scan"], sudo=True)
    if res.returncode != 0:
        fail("Tarama basarisiz oldu.")
        return None

    entries = []
    ssid = None
    freq = None
    for line in res.stdout.splitlines():
        line = line.strip()
        m = re.match(r"freq: (\d+)", line)
        if m:
            freq = int(m.group(1))
        m = re.match(r"SSID: (.*)", line)
        if m:
            ssid = m.group(1).strip()
        if ssid and freq:
            entries.append((ssid, freq))
            ssid, freq = None, None

    # tekillestir (SSID basina en son gorulen)
    by_ssid: dict[str, int] = {}
    for s, f in entries:
        if s:
            by_ssid[s] = f

    if not by_ssid:
        warn("Hicbir 2.4GHz ag bulunamadi. Kanali manuel girebilirsiniz.")
    else:
        table = Table(title="Bulunan 2.4GHz Aglar")
        table.add_column("#")
        table.add_column("SSID")
        table.add_column("Kanal")
        items = list(by_ssid.items())
        for i, (s, f) in enumerate(items, 1):
            table.add_row(str(i), s, str(_freq_to_channel(f)))
        console.print(table)

        choice = console.input("Bir numara secin (veya kanal numarasini dogrudan yazin, bos = atla): ").strip()
        if choice.isdigit():
            n = int(choice)
            if 1 <= n <= len(items):
                _, f = items[n - 1]
                ch = _freq_to_channel(f)
                ok(f"Secilen kanal: {ch} (SSID={items[n-1][0]})")
                return ch
            ok(f"Kanal dogrudan girildi: {n}")
            return n
        warn("Kanal secimi atlandi.")
        return None
    return None


# ---------------------------------------------------------------------------
# 5) Monitor mode
# ---------------------------------------------------------------------------

def enable_monitor_mode(channel: int | None) -> bool:
    step("5) Monitor mode")
    ifaces = [f"wlandf_{d}" for d in DIRECTIONS]
    all_ok = True
    for ifc in ifaces:
        run(["ip", "link", "set", ifc, "down"], sudo=True)
        r = run(["iw", "dev", ifc, "set", "type", "monitor"], sudo=True)
        run(["ip", "link", "set", ifc, "up"], sudo=True)
        if channel:
            run(["iw", "dev", ifc, "set", "channel", str(channel)], sudo=True)
        if r.returncode != 0:
            fail(f"{ifc}: monitor mode ayarlanamadi.")
            all_ok = False
        else:
            ok(f"{ifc}: monitor mode {'+ kanal ' + str(channel) if channel else ''}".strip())
    return all_ok


def main() -> None:
    console.print(f"[bold]Log dosyasi:[/bold] {LOG_PATH}\n")

    if not check_prereqs():
        return
    check_adapters()
    if not ensure_antenna_mapping():
        fail("Anten eslemesi tamamlanamadan devam edilemez.")
        return
    channel = choose_channel()
    if not enable_monitor_mode(channel):
        warn("Bazi arayuzlerde monitor mode ayarlanamadi, yine de devam edilebilir.")

    step("Tamamlandi")
    console.print("[bold green]Kurulum kontrolu tamamlandi.[/bold green] Sirada:")
    console.print("  1. Hedef MAC bulmak icin:      python3 scripts/scan.py")
    console.print("  2. Kalibrasyon icin:            sudo python3 scripts/run_calibration.py --mac <MAC>")
    console.print("  3. Canli takip icin:             sudo python3 scripts/run_dashboard.py")
    console.print(f"\nTum adimlarin detayli logu: {LOG_PATH}")


if __name__ == "__main__":
    try:
        main()
    finally:
        _log_file.close()
