*[English](README.md) | Türkçe*

# NetBearing Console — NetBearing-4X icin Yazilim (4 Antenli Wi-Fi Yon Bulucu / RDF)

**NetBearing-4X**, TL-WN722N v2 adaptorlerinden 4 tanesiyle, silindirik
govde uzerinde on/arka/sag/sol yonlere bakacak sekilde monte edilmis
donanimin adidir. **NetBearing Console** ise bu donanimi calistiran,
tespit edilen Wi-Fi cihazlarinin **yonunu (bearing)** ve — cihaz birden
fazla noktaya tasinarak veya birden fazla istasyon kurularak — **konumunu**
kestiren yazilimdir. Turkce/Ingilizce arayuz destegi ve dairesel Kalman
filtresi tabanli yon yumusatma icerir.

![NetBearing-4X donanimi, NetBearing Console calisirken](docs/photos/device-with-console.jpg)

## Ekran goruntuleri

| Canli takip (coklu hedef) | Canli takip (odaklanmis cihaz) |
|---|---|
| ![Canli takip, coklu hedef](docs/screenshots/live-track-multi.png) | ![Canli takip, odaklanmis cihaz](docs/screenshots/live-track.png) |

| Kurulum | Kalibrasyon |
|---|---|
| ![Kurulum sekmesi](docs/screenshots/setup.png) | ![Kalibrasyon sekmesi](docs/screenshots/calibration.png) |

| Kanal secimi | Konum (ucgenleme) |
|---|---|
| ![Kanal secimi](docs/screenshots/channel-selection.png) | ![Konum sekmesi](docs/screenshots/position.png) |

## Ozellikler

- **Grafik arayuz** (Turkce/Ingilizce): kurulumdan canli takibe, kalibrasyona
  ve konum kesisimine kadar her sey tarayicidan, tikla-calistir seklinde.
- **Dairesel Kalman filtresi** ile yon yumusatma: guven skoruna duyarli
  (dusuk kaliteli okumalari daha az agirliklandirir), aykiri deger kapisi
  (tek kotu ornekle sicramaz) ve "manevra tespiti" (gercek bir yon
  degisikligini - anten fiziksel olarak cevrildiginde - yavas yakinsama
  yerine hizla yakalar).
- **Kendi kendini onaran izleme**: arka planda calisan bir bekci, veri akisi
  duran antenleri otomatik olarak (USB seviyesinde) sifirlar; hangi yonun
  duzenli geride kaldigini tespit edip ona rotasyonda daha fazla sure verir.
- **3 farkli kalibrasyon modu** (basit/hassas/tak-cikar) + coklu-istasyon
  ucgenleme ile yuksek dogruluklu konum kestirimi.
- MAC adresi elle girmek ZORUNLU degil - sistem en guclu gorulen cihazi
  otomatik referans alir (istenirse elle de secilebilir).

## Donanim gereksinimleri

![NetBearing-4X anten dizisi, ustten gorunum](docs/photos/device-top.jpg)

Referans donanim (**NetBearing-4X**) su parcalardan olusur:

- **4x TP-Link TL-WN722N v2/v3** USB Wi-Fi adaptoru (Realtek RTL8188EUS
  cipseti). **v1** farkli bir cipsete (Atheros AR9271) sahiptir, bu proje
  onunla test edilmedi.
- Adaptorleri 90 derece araliklarla on/sag/arka/sol yonlere sabitleyecek bir
  govde/mont (silindirik veya kare - onemli olan 4 antenin ayni noktada,
  esit acilarla ve birbirine gore sabit kalmasi). Kendi govdenizi kullanmak
  serbesttir; yazilim herhangi bir 4-anten dizisiyle calisir.
- **USB hub uyarisi:** 4 adaptoru TEK bir USB hub'a baglarken hub'in kalitesi
  onemlidir - detaylar icin asagidaki "Bilinen donanim/surucu kisitlari"
  bolumune bakin.
- Linux, guncel bir cekirdek (`rtl8xxxu` suruculu in-tree monitor mode
  destegi onerilir - asagida detay var).

## Grafik arayuz (onerilen kullanim sekli)

Konsol komutlariyla ugrasmak istemiyorsaniz, tarayicida acilan bir web
kontrol paneli var. Kurulumdan canli takibe kadar her sey buradan, tikla-
calistir seklinde yapilir:

```bash
./start_gui.sh
```

(Ilk calistirmada venv otomatik olusturup bagimliliklari kurar. Uygulamanin
tamami - paket yakalama + web arayuzu - TEK surecte root olarak calisir;
`pkexec` ile **bir kez** sifre sorulur, sonra tarayici otomatik ve YETKISIZ
olarak acilir - root surec kendisi tarayici baslatmaz.) Uygulama menusune
de bir kisayol eklendi: **"NetBearing Console"** ikonuna tiklayarak da
baslatabilirsiniz (terminal acilmadan).

Arayuzde 4 sekme var:
- **Kurulum:** sistem durumu, anten tanimlama, ag tarama ve kanal secimi
  buradan tiklanarak yapilir. Sorun giderme icin USB yazilimsal sifirlama ve
  alternatif surucu kurulumu da bu sekmede.
- **Canlı Takip:** tespit edilen cihazlari tablo + canli "radar" gorunumunde
  (yon cizgileri) gosterir; bir cihaza tiklayip odaklanabilirsiniz.
- **Kalibrasyon:** anten kazanc paternini 3 farkli yontemle (basit/hassas/
  tak-cikar) olcup hesaplar.
- **Konum:** cok noktali (ucgenleme) konum kesisimi icin istasyon kayitlarini
  alir ve sonucu hesaplar.

Bu arayuz, asagida anlatilan `wifidf` python paketini perde arkasinda
kullanir — istenirse ayni islemler asagidaki konsol komutlariyla da (elle,
adim adim) yapilabilir.

Masaustu kisayolu (Terminal=false) hicbir konsol penceresi acmaz; bir sorun
olursa once bir kez terminalden `./start_gui.sh` calistirip hata mesajini
gorun.

**Mimari notu:** Bu uygulama tek kullanicili, kendi makinenizde calisan
kisisel bir arac oldugu icin, paket yakalama + web sunucusu TEK bir root
surecte birlesik. Bu, cok-kullanicili/paylasimli bir sistemde tercih
edilecek bir tasarim OLMAZDI (root'ta calisan bir HTTP sunucusu, ayricalik
ayirimi olmayan bir sistemde daha genis bir saldiri yuzeyi demektir) - ama
burada pratiklik/guvenilirlik (tek surec = daha az "sureç birbirini
bulamiyor" sinifi hata) bu ortamda dogru tercih.

## Yontem (nasil calisir)

Bu, amatör telsizcilikte "fox hunting" icin kullanilan **genlik
karsilastirmali yon bulma (amplitude-comparison DF)** teknigidir:

1. 4 anten ayni noktada, 90 derece araliklarla farkli yonlere bakar.
2. Bir vericiden gelen sinyalin her antendeki RSSI'si, o antenin o yondeki
   kazancina baglidir. Antenler yon-yonelimli (directional) oldugundan,
   vericiye en yakin bakan antende RSSI en yuksek, tam ters yondekinde en
   dusuk olur.
3. Kalibrasyonla cikarilan anten kazanc paterni (`bearing.py`) kullanilarak,
   4 RSSI degerine en iyi uyan varis acisi en-kucuk-kareler ile bulunur.
4. **Tek istasyonda sadece yon (bearing) elde edilir, mesafe degil.**
   Yuksek dogruluklu **konum** icin cihaz 2+ farkli (bilinen) noktaya
   tasinir, her noktada bearing kaydedilir, ve bu dogrularin kesisimi
   hesaplanir (`triangulate.py`) — gercek RDF/fox-hunting ekiplerinin
   kullandigi standart yontem budur ve tek-istasyon RSSI-mesafe tahminine
   gore cok daha dogrudur.

RSSI'dan doğrudan mesafe kestirimi de var (`distance.py`) ama bu **kaba** bir
tahmindir (coklu yol yansimasi/ortam nedeniyle dogrulugu dusuktur); asil
dogruluk kaynagi ucgenleme yontemidir.

## Donanim notu: TL-WN722N v2

TL-WN722N **v1**, Atheros AR9271 cipseti kullanir ve Linux'ta cekirdek
suruculeriyle (ath9k_htc) dogrudan monitor mode destekler. **v2/v3** ise
Realtek RTL8188EUS cipseti kullanir. Bu genelde monitor mode + paket
enjeksiyonu icin ek (out-of-tree) bir surucu gerektirir; `setup/install_driver.sh`
bu surucuyu (aircrack-ng/rtl8188eus fork'u) DKMS ile kurar. **Ancak** yeni
cekirdeklerde (bu makinede test edildi: cachyos, kernel 7.1.5) in-tree
`rtl8xxxu` suruculu de bu adaptorler icin artik monitor mode destekliyor
(`iw phy <phy> info` ciktisinda "monitor" listeleniyorsa ek surucu KURMANIZA
GEREK YOK). Sadece pasif dinleme (RSSI okuma) yaptigimiz icin (paket
enjeksiyonu gerekmiyor) cogu durumda in-tree surucu yeterlidir; monitor mode
`iw` ile acilamiyorsa ancak o zaman `install_driver.sh`'i deneyin.

## Kurulum

```bash
cd /home/xen/Projeler/wifi-df
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

**Onemli - sudo + venv:** `scapy` gibi paketler venv icine kurulur, ama
`sudo python3 ...` calistirinca `sudo` venv'i gormezden gelip **sistem**
python3'unu kullanir ve `ModuleNotFoundError: scapy` hatasi verir. Bu
yuzden asagidaki tum `sudo python3 scripts/...` komutlarinda **venv'in tam
yolunu** kullanin:

```bash
sudo .venv/bin/python3 scripts/scan.py
```

(`setup/wizard.py` ve `setup/identify_antennas.py` bu soruna takilmaz,
cunku onlar scapy kullanmiyor / wizard kendi ici sudo cagrilarini ayri
komutlar olarak yapiyor.)

### Hizli kurulum (onerilen): sihirbaz

Asagidaki 1-3 numarali manuel adimlarin tamamini kontrol edip (zaten
yapilmissa atlayip) otomatiklestiren, her adimi zaman damgali olarak
`logs/wizard_*.log` dosyasina kaydeden bir sihirbaz var:

```bash
python3 setup/wizard.py
```

Sirasiyla: Python bagimliliklarini kontrol eder → takili adaptor sayisini
dogrular → anten/yon eslemesi yoksa `identify_antennas.py`'i baslatir (fiziksel
adaptor takma adimlarinda sizden etkilesim ister) → udev kuralini kurup
tetikler → cevredeki 2.4GHz aglari tarayip secmenizi ister → 4 antenin
tamamini monitor mode'a alip secilen kanala kilitler. Sonunda kalibrasyon ve
dashboard icin calistirmaniz gereken komutlari ekrana yazar.

Asagidaki 1-3 numarali adimlar sihirbazin perde arkasinda yaptiklarinin
manuel dokumudur — sihirbaz calismazsa veya bir adimi elle tekrarlamak
isterseniz kullanin.

### 1) Surucu kurulumu (4 adaptor icin de gecerli, tek seferlik)

```bash
bash setup/install_driver.sh
```

Zaten `~/rtl8188eus` altinda bir surucu kaynagi varsa onu kullanir; yoksa
klonlar. Kurulumdan sonra adaptorleri takip `dmesg | tail` ile `8188eu`
modulunun yuklendigini dogrulayin.

### 2) Antenleri yonlerine gore tanimlama

Adaptorler USB'ye hangi sirayla takilirsa takilsin `wlan0`, `wlan1`, ...
gibi ongorulemeyen isimler alir. Her adaptoru o an taktiginiz fiziksel yone
(on/sag/arka/sol) eslestirip kalici arayuz adi (`wlandf_front` vb.) uretmek
icin:

```bash
sudo python3 setup/identify_antennas.py
```

Script sirayla "on adaptoru tak", "sag adaptoru tak" diye soracak. Sonunda
iki dosya uretir; ekrandaki komutlarla kurun:

```bash
sudo cp setup/99-wifi-df.rules /etc/udev/rules.d/
sudo cp setup/99-wifi-df-unmanaged.conf /etc/NetworkManager/conf.d/
sudo systemctl reload NetworkManager
sudo udevadm control --reload-rules
sudo udevadm trigger --action=add -s net
```

(`--action=add` onemli: varsayilan `trigger` "degisiklik" olayi gonderir ve
isim degistirme kurali calismaz. Bu da isi gormezse adaptorleri cikarip
tekrar takin.) Bu adimdan sonra `data/device_config.json` otomatik olusturulur.

**Neden MAC degil de USB port yolu (ID_PATH)?** Bu adaptorlerde
NetworkManager gizlilik amacli olarak her takista **rastgele bir MAC**
atayabiliyor (donanimin gercek/kalici MAC'i sabit kalsa da, arayuze
gorunen adres degisir). Bu yuzden isim eslemesi MAC'e degil, adaptorun
kapsulde hangi fiziksel USB porta kablolandigina (`ID_PATH`, degismez)
gore yapilir — antenleri ilk tanimlamadan sonra ayni fiziksel USB
portlarina takili tutmaya devam edin. `99-wifi-df-unmanaged.conf` ise bu 4
arayuzu NetworkManager'in yonetiminden tamamen cikarir; boylece hem MAC
rastgelestirmesi durur hem de NM'in kanal/monitor-mode ayarlariyla
catismasi onlenir.

### 3) Monitor mode + kanal kilitleme

```bash
sudo bash setup/monitor_mode.sh 6   # 6 = dinlenecek Wi-Fi kanali
```

Not: 4 anten de **ayni kanalda** dinlemelidir (yon karsilastirmasi ancak
esanli, ayni kanaldaki okumalarla anlamlidir). Hedefin kanalini once
`scripts/scan.py` ile (herhangi bir arayuzu gecici olarak farkli kanallara
tarayarak) ya da `iw scan` ile tespit edin.

## Kalibrasyon (zorunlu, dogruluk icin kritik)

Kazanc paterni kalibre edilmeden varsayilan (kaba) bir patern kullanilir;
gercek olcum icin kendi antenlerinizle kalibrasyon yapin:

```bash
sudo .venv/bin/python3 scripts/scan.py       # once referans MAC'i bulun (orn. telefon hotspot)
sudo .venv/bin/python3 scripts/run_calibration.py --mac AA:BB:CC:DD:EE:FF --step 30 --duration 5
```

Referans vericiyi (bilinen MAC'li bir telefon/hotspot) cihazdan sabit bir
yaricapta tutup script'in istedigi acilara (varsayilan 30 derece araliklarla,
0=on referans, saat yonunde) sirayla yerlestirin. Sonuc
`data/calibration/gain_pattern.json` dosyasina kaydedilir.

Algoritmanin donanimsiz dogrulamasi icin (sentetik veriyle):

```bash
python3 -m pytest tests/ -v
```

## Kullanim

### Canli yon takibi (dashboard)

```bash
sudo .venv/bin/python3 scripts/run_dashboard.py
```

Tespit edilen tum cihazlari, yon-basina RSSI'yi, tahmini bearing/pusula
yonunu ve guven skorunu canli tabloda gosterir.

### Konum kesisimi (ucgenleme) — yuksek dogruluk icin

Cihazi bilinen (x, y) metre konumlarina tasiyip her noktada kaydedin:

```bash
sudo .venv/bin/python3 scripts/record_station.py 0 0 --duration 8      # 1. konum
# cihazi tasiyin (orn. 20 metre doguya)...
sudo .venv/bin/python3 scripts/record_station.py 20 0 --duration 8     # 2. konum
```

**Onemli:** her istasyonda cihazin "on" referansi ayni mutlak yone (orn.
gercek Kuzey, pusula ile hizalanarak) bakmalidir; aksi halde bearing'ler
ortak koordinat sistemine oturmaz.

Sonra tum hedeflerin konum tahminini hesaplayin:

```bash
python3 scripts/fix_targets.py
```

## Dogruluk ve sinirlamalar

- **Yon (bearing):** kalibre edilmis 4 antenle, sabit/gurultusuz kosullarda
  birkac derece mertebesinde hata beklenir (bkz. `tests/test_bearing.py`
  sentetik dogrulama). Coklu yol yansimasi (indoor multipath) hatayi artirir.
- **Tek istasyon mesafesi (RSSI'dan):** dusuk dogruluk, sadece kaba fikir
  icin kullanin.
- **Ucgenlenmis konum (2+ istasyon):** en dogru yontem; istasyonlar
  arasindaki aci farki ne kadar buyukse (idealde ~90 derece civari) kesisim
  o kadar keskin/dogru olur. Istasyonlar hemen hemen ayni dogrultuda ise
  kesisim belirsizlesir.

### Bilinen donanim/surucu kisitlari

Bu projeyi baska bir makinede (farkli USB hub, farkli cekirdek surumu)
calistiran herkes asagidaki iki kisitla karsilasabilir. Ikisi de yazilimsal
olarak (kismen) telafi edildi ama donanim/surucu seviyesinde tam olarak
ortadan kaldirilamaz - bu yuzden acikca belgeleniyor.

**1) rtl8xxxu + 4 es zamanli ornek.** Linux'un dahili `rtl8xxxu` suruculu,
RTL8188EUS tabanli 4 adaptoru AYNI ANDA monitor modda calistirinca zaman
zaman bazi adaptorlerin veri teslimini sessizce durdurdugu (hata/istisna
vermeden) gozlemlendi - bu, guc kaynagi (harici beslemeli USB hub ile bile),
thread sayisi ya da yakalama mimarisinden (tek thread/coklu thread/rotasyonlu)
BAGIMSIZ, tekrarlanabilir sekilde dogrulandi. Tek bir antenin izole calismasi
ise HER ZAMAN guvenilir oldu - bu yuzden proje varsayilan olarak antenleri es
zamanli degil ROTASYONLA dinler (bkz. `capture.py` dokstring'i) ve arka
planda calisan bir **bekci (watchdog)** paket sayaclarini surekli izleyip,
bir/iki anten "takilirsa" sadece o antenleri (TUM izlemeyi kesmeden) otomatik
USB seviyesinde sifirlar; cogu/tumu takilirsa tam bir sifirlama yapar.

**2) Paylasimli USB hub bant genisligi darbogazi.** 4 adaptor de TEK bir USB
hub'a (ozellikle Full-Speed/12Mbit, tek Transaction Translator'lu, ucuz/
pasif bir hub'a) baglandiginda, hub'in port'lar arasi zamanlama davranisi
BIR yonu digerlerine gore sistematik olarak ac birakabilir - o antenin
radyosu paket alsa bile (surucu seviyesinde `/proc/net/dev` sayaclari normal
buyur), veri USB uzerinden bilgisayara ayni verimlilikte ulasmaz. Bunu
telafi etmek icin `capture.py`, her yonun son birkac turdaki gercek paket/
saniye hizini olcup, grup ortalamasinin belirgin altinda kalan yone rotasyon
sirasinda otomatik olarak daha fazla dinleme suresi verir (ust sinirli,
digerlerini geciktirmeden). **Oneri:** mumkunse 4 adaptoru TEK bir ucuz
hub yerine (a) anakartin ayri fiziksel USB kok/host denetleyicilerine
(root hub) dagitarak, veya (b) kaliteli, harici beslemeli bir USB 3.0
hub uzerinden baglayin - Full-Speed tek-TT hub'lara gore gozle gorulur
sekilde daha iyi/daha tutarli sonuc verir.

Iki kisit da devam ederse:
1. Kurulum sekmesindeki "Adaptörleri Yazılımsal Sıfırla"yı elle deneyin.
2. Kalibrasyon → "Tak-Çıkar" modunu kullanin (tek anten izolasyonu, bu
   sinirlardan hic etkilenmez).
3. `setup/install_alt_driver` (rtl8188eus, aircrack-ng) ile alternatif
   surucuyu deneyin - ama cok yeni cekirdeklerde (6.12+) derleme yamalari
   gerekebilir (bkz. Kurulum sekmesindeki "Alternatif Sürücüyü Kur").
4. "Canlı Takip" sekmesindeki tanilama sayaclarinda (`rate_pps`, `dwell_s`)
   hangi yonun surekli geride kaldigini gorebilirsiniz - capture_stats API
   yaniti bu degerleri de icerir.

## Kullanim kapsami

Bu arac pasif olarak halka acik Wi-Fi yayinlarini (beacon/probe/veri
cerceveleri) dinler; herhangi bir agа baglanmaya veya sifre kirmaya
calismaz. Yine de belirli bir kisiye ait cihazi izlemek/konumlandirmak
gizlilik ve yerel mevzuata tabi olabilir — yalnizca sahibi oldugunuz
agları/cihazları test etmek, yetkili guvenlik/RF calismalari veya kendi
ekipmanınızı (orn. kayip cihaz, parazit kaynagi) bulmak icin kullanin.

## Proje yapisi

```
start_gui.sh        Grafik arayuzu baslatan launcher (pkexec ile root baslatir, tarayiciyi ayri/yetkisiz acar)
webapp/             Web tabanli kontrol paneli (onerilen kullanim)
  app.py               Tek surecli Flask uygulamasi (root; paket yakalama + web arayuzu bir arada)
  static/                index.html, app.js, app.css (4 sekmeli SPA)
wifidf/            Cekirdek Python paketi
  config.py           Yon<->arayuz esleme, aci tanimlari
  capture.py          Scapy tabanli 802.11/RSSI yakalama (4 arayuz, esanli)
  aggregator.py        MAC bazinda ornek birlestirme + gurultu azaltma
  bearing.py           Genlik-karsilastirmali yon bulma algoritmasi
  calibrate.py          Kalibrasyon rutini
  distance.py            Kaba RSSI->mesafe modeli
  triangulate.py           Coklu-istasyon bearing kesisimi
  station_log.py           Ucgenleme icin istasyon/bearing kaydi
  tracker.py                Capture+aggregate+bearing ana dongusu
  dashboard.py                rich tabanli canli terminal arayuzu
scripts/            Calistirilabilir CLI giris noktalari
setup/              Surucu kurulum, anten tanimlama, monitor mode scriptleri
  wizard.py           Tum kurulum adimlarini kontrol eden/otomatiklestiren, loglayan sihirbaz
data/               Kalibrasyon ve calisma-zamani verileri (git'e girmez)
logs/               wizard.py'nin zaman damgali calisma loglari (git'e girmez)
tests/              Donanimsiz sentetik dogrulama testleri
```
