#!/usr/bin/env python3
"""Her yondeki (on/sag/arka/sol) TL-WN722N adaptorunu USB fiziksel port yoluna
(ID_PATH) gore tanir ve kalici arayuz adi (wlandf_front, wlandf_right, ...)
icin bir udev kurali uretir.

NOT: Eslesme MAC adresine gore DEGIL, USB fiziksel port yoluna (ID_PATH) gore
yapilir. Cunku NetworkManager bu tur Wi-Fi adaptorlerinde gizlilik amacli MAC
adresini her takista rastgele degistirebilir; ID_PATH ise adaptorun kapsule
hangi fiziksel porta kablolandigina baglidir ve degismez. Bu yuzden her
adaptoru DAIMA ayni fiziksel USB portuna takmalisiniz (kapsulde zaten sabit
kablolu olacagi icin bu dogal olarak saglanir).

Ayrica bu scriptin urettigi kurulum, bu 4 arayuzu NetworkManager'in
yonetiminden cikarir (unmanaged) - aksi halde NM, monitor mode / sabit kanal
ayarlariyla catisabilir ve MAC'i degistirmeye devam eder.

Kullanim: 4 adaptoru da SOKUN, sonra bu scripti calistirin; sirayla her
yon icin tek tek adaptoru takmaniz istenecek.
"""

import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wifidf.config import DeviceConfig, DIRECTIONS, TR_LABELS

RULES_OUT = Path(__file__).resolve().parent / "99-wifi-df.rules"
NM_UNMANAGED_OUT = Path(__file__).resolve().parent / "99-wifi-df-unmanaged.conf"


def _current_wifi_interfaces() -> set[str]:
    try:
        out = subprocess.run(["iw", "dev"], capture_output=True, text=True, check=True).stdout
    except FileNotFoundError:
        print("[!] 'iw' komutu bulunamadi. Once kurun: sudo pacman -S iw", file=sys.stderr)
        sys.exit(1)
    ifaces = set()
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("Interface "):
            ifaces.add(line.split("Interface ", 1)[1].strip())
    return ifaces


def _id_path_of(iface: str) -> str:
    out = subprocess.run(
        ["udevadm", "info", "-q", "property", "-p", f"/sys/class/net/{iface}"],
        capture_output=True, text=True, check=True,
    ).stdout
    for line in out.splitlines():
        if line.startswith("ID_PATH="):
            return line.split("=", 1)[1]
    raise RuntimeError(f"{iface} icin ID_PATH bulunamadi (udevadm info)")


def _permanent_mac_of(iface: str) -> str | None:
    """Sadece bilgi amacli: ethtool ile donanimin kalici (rastgelenmemis) MAC'i."""
    try:
        out = subprocess.run(["ethtool", "-P", iface], capture_output=True, text=True, check=True).stdout
        # "Permanent address: xx:xx:xx:xx:xx:xx"
        for line in out.splitlines():
            if "Permanent address" in line:
                return line.split("Permanent address:", 1)[1].strip()
    except Exception:
        pass
    return None


def _wait_for_new_interface(baseline: set[str], timeout: float = 60.0) -> str:
    start = time.time()
    while time.time() - start < timeout:
        current = _current_wifi_interfaces()
        new = current - baseline
        if new:
            return sorted(new)[0]
        time.sleep(1.0)
    raise TimeoutError("Yeni arayuz algilanamadi (60 sn). Adaptorun takili ve tanindigindan emin olun.")


def main() -> None:
    print("== Wi-Fi DF Anten Tanimlama ==")
    print("Once TUM adaptorleri cikarin, ardindan ENTER'a basin.")
    input()

    baseline = _current_wifi_interfaces()
    print(f"Baslangic arayuzleri: {baseline or '(yok)'}\n")

    mapping: dict[str, dict] = {}  # direction -> {id_path, mac, iface}

    for d in DIRECTIONS:
        label = TR_LABELS[d]
        input(f">> Sadece '{label}' ({d}) adaptorunu simdi takin, sonra ENTER'a basin...")
        print("   Bekleniyor...")
        iface = _wait_for_new_interface(baseline)
        id_path = _id_path_of(iface)
        mac = _permanent_mac_of(iface)
        print(f"   Bulundu: {iface}  ID_PATH={id_path}  kalici_MAC={mac or '?'}")
        mapping[d] = {"id_path": id_path, "mac": mac, "iface": iface}
        baseline.add(iface)

    # udev kurali: fiziksel USB port yoluna (ID_PATH) gore isimlendirme
    lines = [
        "# Otomatik uretildi: setup/identify_antennas.py",
        "# Eslesme MAC'e degil USB fiziksel port yoluna (ID_PATH) gore yapilir -",
        "# NetworkManager MAC'i rastgele degistirse bile isim sabit kalir.",
        "# Kurulum: sudo cp 99-wifi-df.rules /etc/udev/rules.d/ && sudo udevadm control --reload-rules && sudo udevadm trigger --action=add -s net",
        "",
    ]
    for d, info in mapping.items():
        lines.append(
            f'SUBSYSTEM=="net", ACTION=="add", ENV{{ID_PATH}}=="{info["id_path"]}", NAME="wlandf_{d}"'
        )
    RULES_OUT.write_text("\n".join(lines) + "\n")

    # NetworkManager'i bu 4 arayuzden uzak tut (MAC rastgelestirme + kanal/monitor mode catismasini onler)
    NM_UNMANAGED_OUT.write_text(
        "# Otomatik uretildi: setup/identify_antennas.py\n"
        "# Kurulum: sudo cp 99-wifi-df-unmanaged.conf /etc/NetworkManager/conf.d/ && sudo systemctl reload NetworkManager\n"
        "[keyfile]\n"
        "unmanaged-devices=interface-name:wlandf_*\n"
    )

    print(f"\nudev kurali yazildi: {RULES_OUT}")
    print(f"NetworkManager unmanaged kurali yazildi: {NM_UNMANAGED_OUT}")
    print("\nEtkinlestirmek icin:")
    print(f"  sudo cp {RULES_OUT} /etc/udev/rules.d/")
    print(f"  sudo cp {NM_UNMANAGED_OUT} /etc/NetworkManager/conf.d/")
    print("  sudo systemctl reload NetworkManager")
    print("  sudo udevadm control --reload-rules && sudo udevadm trigger --action=add -s net")
    print("  (adaptorleri cikarip tekrar takmaniz gerekebilir)")

    cfg = DeviceConfig.default()
    for d, info in mapping.items():
        cfg.antennas[d].mac = info["mac"]
        cfg.antennas[d].id_path = info["id_path"]
    cfg.save()
    print(f"\nCihaz yapilandirmasi kaydedildi: data/device_config.json")


if __name__ == "__main__":
    main()
