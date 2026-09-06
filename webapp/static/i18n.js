// ---------------------------------------------------------------------
// TR/EN cift dil destegi. Tum sabit metinler burada anahtar->metin olarak
// tutulur; app.js sadece t(anahtar, degiskenler) ile cagirir. Statik HTML
// metinleri (index.html) ise data-i18n / data-i18n-html / data-i18n-placeholder
// / data-i18n-title ozniteligiyle isaretlenir, applyStaticI18n() bunlari
// sayfa yuklendiginde ve dil degistiginde otomatik doldurur.
// ---------------------------------------------------------------------

const I18N = {
  tr: {
    "app.title": "WiFi YÖN TESPİT SİSTEMİ",
    "app.subtitle": "TAKTİK RDF ÜNİTESİ · 4 KANALLI ANTEN DİZİSİ",
    "page.title": "WiFi Yön Bulucu",

    "tab.setup": "KURULUM",
    "tab.live": "CANLI TAKİP",
    "tab.calib": "KALİBRASYON",
    "tab.pos": "KONUM",

    "setup.status.title": "1) SİSTEM DURUMU",
    "setup.status.refresh": "Durumu Yenile",

    "setup.datastop.title": "VERİ AKIŞI DURDU MU? (gelişmiş)",
    "setup.datastop.desc": "Bilinen sürücü kısıtı: dahili sürücü (rtl8xxxu) bir süre sonra veri akışını sessizce kaybedebilir; fiziksel çıkar-tak bunu düzeltir. Aşağıdaki buton, adaptörleri USB üzerinden <strong>yazılımla</strong> sıfırlar (çıkar-tak ile aynı etki, elle dokunmadan). Önce bunu deneyin.",
    "setup.datastop.reset_btn": "Adaptörleri Yazılımsal Sıfırla",
    "setup.datastop.altdriver_summary": "Sıfırlama yardımcı olmuyorsa: alternatif sürücü kur",
    "setup.datastop.altdriver_desc": "Daha güvenilir alternatif sürücüyü (rtl8188eus) kurup bu 4 adaptörü ona geçirir. Bir kaç dakika sürebilir; çok yeni çekirdeklerde derleme hatası verebilir.",
    "setup.datastop.altdriver_btn": "Alternatif Sürücüyü Kur",

    "setup.identify.title": "2) ANTENLERİ YÖNLERİNE GÖRE TANIMLA",
    "setup.identify.desc": "4 adaptörü de USB'den çıkarın, sonra başlatın. Sırayla her yön için adaptörü (çıkarmadan, sırayla) takmanız istenecek. Ölçüm/WiFi gerekmez, sadece USB port ↔ yön eşlemesi yapılır.",
    "setup.identify.mapped_note": "ℹ Antenler zaten eşlenmiş durumda. Yeniden yapmak isterseniz \"Tanımlamayı Başlat\"a basabilirsiniz — mevcut eşleme güncellenir.",
    "setup.identify.start_btn": "Tanımlamayı Başlat",
    "setup.identify.step_wait": "adaptörünü şimdi takın…",
    "setup.identify.waiting": "bekleniyor",
    "setup.identify.found": "bulundu —",
    "setup.identify.writing_rules": "Kurallar yazılıyor ve etkinleştiriliyor…",
    "setup.identify.done": "Tamamlandı.",

    "setup.channel.title": "3) KANAL SEÇİMİ VE MONITOR MODE",
    "setup.channel.scan_btn": "2.4GHz Ağları Tara",
    "setup.channel.manual_label": "Manuel kanal:",
    "setup.channel.apply_btn": "Kanalı Uygula ve İzlemeyi Başlat",
    "setup.channel.scanning": "Taranıyor…",
    "setup.channel.none_found": "Ağ bulunamadı.",
    "setup.channel.select_btn": "Seç",
    "setup.channel.applying": "Uygulanıyor…",
    "setup.channel.applied": "Kanal ayarlandı, izleme başladı. 'Canlı Takip' sekmesine geçebilirsiniz.",
    "setup.channel.th_ssid": "SSID",
    "setup.channel.th_channel": "Kanal",

    "status.adapters_found": "{n} adet TL-WN722N adaptörü bulundu",
    "status.antennas_mapped": "Antenler yönleriyle eşleşmiş",
    "status.antennas_unmapped": "Anten eşlemesi yapılmamış",
    "status.interfaces": "Arayüzler: {list}",
    "status.none": "yok",
    "status.channel": "Kanal: {ch}",
    "status.channel_unset": "Kanal seçilmedi",
    "status.tracking_on": "İzleme aktif",
    "status.tracking_off": "İzleme başlatılmadı",
    "status.calib_done": "Kalibrasyon yapılmış",
    "status.calib_missing": "Kalibrasyon yapılmamış (varsayılan patern kullanılıyor)",
    "status.dist_calib_done": "Mesafe kalibrasyonu yapılmış (gerçek mesafeler bu ölçümlere dayanıyor)",
    "status.dist_calib_missing": "⚠ Mesafe kalibrasyonu yapılmamış — gösterilen ~mesafeler genel varsayılan değerlerle hesaplanıyor, gerçek değerlerden uzak olabilir. 'Canlı Takip' sekmesinde bir cihaza odaklanıp mesafe kalibrasyonu yapın.",
    "status.autoheal_active": "Otomatik onarım (bekçi): {n} kez veri akışı durunca kendiliğinden USB sıfırlaması yaptı",
    "status.autoheal_idle": "Otomatik onarım (bekçi): aktif, henüz müdahale gerekmedi",
    "status.fetch_failed": "Durum alınamadı: {err}",

    "usb_reset.resetting": "Sıfırlanıyor (birkaç saniye)…",
    "usb_reset.ok_all": "Tamamlandı, 4 arayüz de geri geldi. Şimdi 'Ağları Tara' → kanal seçip 'Kanalı Uygula ve İzlemeyi Başlat' deyin.",
    "usb_reset.ok_partial": "Sıfırlandı ama sadece {found}/4 arayüz geri geldi: {list}. Birkaç saniye bekleyip 'Durumu Yenile'yi deneyin.",

    "altdriver.installing": "Kuruluyor (bir kaç dakika sürebilir)…",
    "altdriver.done": "Tamamlandı. Arayüzler: {list}",
    "altdriver.none": "(bulunamadı)",

    "live.title": "CANLI YÖN TAKİBİ",
    "live.desc": "Liste SSID'ye göre alfabetik sıralanır ve sinyali kesilen cihazlar listeden kaybolmaz (soluklaşır). Bir satıra tıklayın: radar sadece o cihaza odaklanır (tekrar tıklayınca veya \"Odağı Kaldır\" ile geri çıkar).",
    "live.search_placeholder": "🔎 Ara: SSID veya MAC…",
    "live.clear_focus": "Odağı Kaldır",
    "live.focused_prefix": "Odaklanıldı:",
    "live.click_hint": "Sadece bu cihaza odaklanmak için tıklayın",

    "live.dist.title": "Odaklanılan cihaz için mesafe kalibrasyonu",
    "live.dist.desc": "Cihazı bilinen bir mesafeye (örn. 1 metre) koyup ölçün, sonra farklı bir mesafeye (örn. 3-5 metre) taşıyıp tekrar ölçün. En az 2 farklı mesafe gerekir; ne kadar çok mesafe ölçerseniz o kadar isabetli olur.",
    "live.dist.current_label": "Şu anki gerçek mesafe (m):",
    "live.dist.measure_btn": "Bu Mesafede Ölç",
    "live.dist.finish_btn": "Mesafe Kalibrasyonunu Tamamla",
    "live.dist.need_focus": "Önce bir cihaza odaklanın (tabloda bir satıra tıklayın).",
    "live.dist.need_value": "Geçerli bir mesafe girin.",
    "live.dist.measuring": "{d}m için ölçülüyor…",
    "live.dist.recorded": "{d}m @ RSSI={rssi} dBm kaydedildi (toplam {count} nokta). Şimdi cihazı farklı bir mesafeye taşıyıp tekrar ölçün.",
    "live.dist.need_2points": "En az 2 farklı mesafede ölçüm yapmalısınız.",
    "live.dist.done": "✓ Mesafe kalibrasyonu tamamlandı. Artık mesafe tahminleri bu ölçümlere göre hesaplanacak.",

    "live.focus_default": "Odaklanmak için tablodan bir cihaz seçin.",
    "live.focus_gone": "Odaklanılan cihaz ({mac}) şu an listede yok.",
    "live.no_ssid": "(SSID yok)",
    "live.f_direction": "Yön:",
    "live.f_distance": "~Mesafe:",
    "live.f_confidence": "Güven:",
    "live.f_concentration": "Tutarlılık:",
    "live.f_lastseen": "Son görülme:",
    "live.no_signal": "📡 sinyal yok",
    "live.no_signal_lastknown": "📡 sinyal yok (son bilinen yön gösteriliyor)",
    "live.locked": "✓ Kilitlendi ({n})",
    "live.stabilizing": "stabilize oluyor… ({n})",
    "live.seconds_ago": "{s}s önce",

    "live.table.mac": "MAC",
    "live.table.ssid": "SSID",
    "live.table.front": "Ön",
    "live.table.right": "Sağ",
    "live.table.back": "Arka",
    "live.table.left": "Sol",
    "live.table.bearing": "Yön° (yumuşatılmış)",
    "live.table.compass": "Pusula",
    "live.table.confidence": "Güven",
    "live.table.status": "Durum",
    "live.table.distance": "~Mesafe",
    "live.table.last": "Son",

    "live.stats_hint": "Hiç cihaz görünmüyorsa aşağıdaki tanılama sayaçlarına bakın: \"toplam\" 0 ise arayüzler paket görmüyor demektir (kanal/monitor mode sorunu); \"rssi\" sütunu 0 ama diğerleri artıyorsa sürücü RSSI raporlamıyor demektir.",
    "live.stats.th_dir": "Yön",
    "live.stats.th_total": "Toplam paket",
    "live.stats.th_dot11": "802.11",
    "live.stats.th_mac": "MAC var",
    "live.stats.th_radiotap": "RadioTap var",
    "live.stats.th_rssi": "RSSI var",

    "calib.title": "ANTEN KAZANÇ PATERNİ KALİBRASYONU",
    "calib.desc": "Referans verici (örn. telefon hotspot'u) açık ve yayında olsun ve antenin yakınında tutulsun. <strong>MAC seçmenize gerek yok</strong> — sistem her ölçümde \"en güçlü görülen cihazı\" otomatik referans olarak alır (antenin yakınında tuttuğunuz cihaz zaten en güçlü sinyal olacaktır). İsterseniz aşağıdan belirli bir cihaz da seçebilirsiniz.",
    "calib.target_label": "Referans cihaz (opsiyonel):",
    "calib.target_auto": "— otomatik algıla —",
    "calib.target_none": "— hiç cihaz görünmüyor —",
    "calib.target_select": "— seçin —",
    "calib.target_hint_none": "Referans verici yayında mı? İzleme başlatıldı mı? (Kurulum sekmesi)",
    "calib.target_hint_count": "{n} cihaz bulundu.",
    "calib.refresh_btn": "Ağları Yenile",
    "calib.duration_label": "Ölçüm süresi:",
    "calib.duration_desc": "Süre 12 sn önerilir: \"Basit\"/\"Hassas\" modda 4 anten sırayla dinlendiği için (~10 sn/tur), daha kısa süre bazı antenlerin sırası hiç gelmeden ölçümü bitirip hatalı sonuç verebilir. \"Tak-Çıkar\" modunda tek anten olduğu için daha kısa süre de yeterlidir.",
    "calib.manual_summary": "Belirli bir cihaz seçmek istiyorum / listede yok, elle MAC gir",
    "calib.manual_mac_label": "Manuel MAC:",

    "calib.mode.simple": "1) Basit (4 yön)",
    "calib.mode.precise": "2) Hassas (özel açı)",
    "calib.mode.solo": "3) Tak-Çıkar (tek anten)",

    "calib.simple.desc": "Telefonu/referans vericiyi sırayla her antenin TAM ÖNÜNE koyup o yönün butonuna basın. Sistem hangi antenin en güçlü okuduğunu kontrol edip doğru yerleştirip yerleştirmediğinizi size söyler.",
    "calib.simple.start_btn": "Basit Kalibrasyonu Başlat",
    "calib.simple.place_prefix": "Referans vericiyi",
    "calib.simple.place_suffix": "antenin TAM ÖNÜNE koyun.",
    "calib.measure_btn": "Ölç",
    "calib.measuring": "Ölçülüyor…",
    "calib.target_info": "Hedef: {ssid} {mac}",
    "calib.simple.confirmed": "✓ Doğrulandı: \"{dir}\" anteni en güçlü okudu.",
    "calib.simple.unexpected": "⚠ Beklenmedik sonuç: en güçlü okuyan \"{strongest}\" anteni oldu, \"{expected}\" değil. Referans doğru yönde mi, anten yönleri doğru mu kontrol edin. Yine de devam edilecek.",
    "calib.readings_suffix": "Okumalar: {json}",
    "calib.compute_btn": "Kalibrasyonu Hesapla",
    "calib.computed": "Tamamlandı: g_max={gmax} g_min={gmin} n={n}",
    "calib.computed_done": "✓ Tamamlandı:",

    "calib.precise.desc": "Referans vericiyi cihazdan sabit yarıçapta tutup, antene göre <strong>hangi yönde/aralıkta</strong> olduğunu aşağıdaki butonlardan seçerek ölçün (elle açı yazmanıza gerek yok — örn. \"Ön ile Sağ arası\" = 45°). İstediğiniz kadar farklı yönde ölçüm yapabilirsiniz, ne kadar çoksa o kadar hassas olur.",
    "calib.precise.measuring": "{label} ({deg}°) ölçülüyor…",
    "calib.precise.recorded": "✓ {label} ({deg}°) kaydedildi.",
    "calib.precise.total_points": "(toplam {n} nokta)",
    "calib.precise.advanced_summary": "Gelişmiş: otomatik açı dizisi ile ölç",
    "calib.precise.step_label": "Açı aralığı:",
    "calib.precise.auto_start_btn": "Otomatik Diziyle Başlat",
    "calib.precise.place_at": "konumuna referans vericiyi yerleştirin.",

    "calib.solo.warn": "⚠ Sadece hangi USB portun hangi yöne (Ön/Sağ/Arka/Sol) karşılık geldiğini eşlemek mi istiyorsunuz — ölçüm yapmadan, adaptörleri çıkarmadan, sırayla takarak? O zaman burası <strong>yanlış yer</strong>: <strong>Kurulum sekmesi → \"Antenleri Yönlerine Göre Tanımla\"</strong>a gidin. Burası (Tak-Çıkar) <strong>farklı bir amaç</strong> için: sinyal gücü kalibrasyonu, bu yüzden ölçüm ve tek anten izolasyonu (çıkararak test) zorunludur.",
    "calib.solo.desc": "4 anten aynı anda güvenilir çalışmıyorsa: her seferinde <strong>sadece bir</strong> adaptörü takılı bırakıp diğerlerini çıkarın. Sistem size sırayla hangi adaptörü takmanız gerektiğini söyler: <strong>Ön → Sol → Sağ → Arka</strong>. Söylenen adaptörü takıp <strong>\"Taktım, Devam Et\"</strong> ile onaylayın, birkaç açıda ölçün, sonra <strong>\"Sıradaki Antene Geç\"</strong>e basıp adaptörü değiştirin. Her adım sizin onayınızla ilerler.",
    "calib.solo.begin_btn": "Sihirbazı Başlat",
    "calib.solo.reset_btn": "Baştan Başlat (tümünü sıfırla)",
    "calib.solo.confirm_plug_btn": "Taktım, Devam Et",
    "calib.solo.next_btn": "Sıradaki Antene Geç →",
    "calib.solo.complete_btn": "Kalibrasyonu Tamamla",
    "calib.solo.th_dir": "Yön",
    "calib.solo.th_count": "Ölçüm sayısı",
    "calib.solo.only_prefix": "Şimdi",
    "calib.solo.only_suffix": "adaptörünü takın (diğerlerini çıkarın).",
    "calib.solo.ready_prefix": "✓",
    "calib.solo.ready_suffix": "— referans vericiyi TAM ÖNÜNE koyup aşağıdaki açılardan birkaçını ölçün.",
    "calib.solo.need_begin": "Önce 'Sihirbazı Başlat'a basın.",
    "calib.solo.measuring": "{dir} anteni, {delta}° ölçülüyor…",
    "calib.solo.recorded": "{dir} @ {delta}°: RSSI={rssi} dBm — {targetInfo} (bu yön için toplam {n} ölçüm)",
    "calib.solo.reset_done": "Sıfırlandı.",
    "calib.solo.complete_done": "✓ Kalibrasyon Tamamlandı!",
    "calib.solo.delta_front": "Tam önü (0°)",
    "calib.solo.delta_other": "{d}° (antenin kendisine göre)",

    "verify.title": "4) DOĞRULAMA (Kalibrasyonu Test Et)",
    "verify.desc": "Kalibrasyondan sonra kontrol edin: referans vericiyi antene göre <strong>bildiğiniz</strong> bir yöne koyun (veya anteni döndürün), o yönü aşağıdan seçip \"Doğrula\"ya basın. Sistem, o an hesapladığı yönle sizin belirttiğiniz gerçek yönü karşılaştırıp hata payını gösterir.",
    "verify.real_dir_label": "Gerçek yön:",
    "verify.btn": "Doğrula",
    "verify.need_mac": "Doğrulama için üstteki 'Referans cihaz' alanından belirli bir cihaz seçin (otomatik algılama burada kullanılamaz).",
    "verify.checking": "Kontrol ediliyor…",
    "verify.not_visible": "Bu cihaz şu an görünmüyor.",
    "verify.no_bearing": "Bu cihaz için henüz bir yön hesaplanamadı (yetersiz anten okuması).",
    "verify.good": "✓ İyi",
    "verify.medium": "⚠ Orta",
    "verify.bad": "✗ Kötü",
    "verify.result": "Gerçek yön: <strong>{real}°</strong> — Hesaplanan: <strong>{measured}°</strong> — Hata: <strong>{err}°</strong>",
    "verify.not_locked_note": "Not: yön henüz kilitlenmedi, sonuç değişebilir.",
    "verify.calib_added": "✓ Bu ölçüm kalibrasyona eklendi ve patern yeniden hesaplandı",
    "verify.calib_added_points": "(g_max={gmax} g_min={gmin} n={n}, toplam {count} nokta).",
    "verify.calib_added_fail": "Bu ölçüm kalibrasyona eklendi ({n}. nokta) ama yeniden hesaplama başarısız: {err}",
    "verify.calib_added_pending": "Bu ölçüm kalibrasyona eklendi ({n}/4 nokta) — en az 4 farklı açıda doğrulama yapınca patern otomatik hesaplanacak.",

    "pos.title": "ÇOKLU NOKTA KONUM KESİŞİMİ (Üçgenleme)",
    "pos.desc": "Cihazı bilinen (x,y) metre konumlarına taşıyıp her noktada kaydedin. \"Ön\" referansı her noktada aynı mutlak yöne bakmalı.",
    "pos.x_label": "X (m):",
    "pos.y_label": "Y (m):",
    "pos.duration_label": "Süre:",
    "pos.record_btn": "Bu Konumda Kaydet",
    "pos.calc_btn": "Konumları Hesapla",
    "pos.recording": "({x}, {y}) konumunda ölçülüyor…",
    "pos.recorded": "({x}, {y}): {count} gözlem kaydedildi.",
    "pos.record_error": "({x}, {y}): Hata — {err}",
    "pos.calculating": "Hesaplanıyor…",
    "pos.no_records": "Kayıt yok.",
    "pos.th_mac": "MAC",
    "pos.th_ssid": "SSID",
    "pos.th_position": "Konum",
    "pos.th_stations": "İstasyon",
    "pos.th_note": "Not",
    "pos.residual_prefix": "artık",

    "dir.front": "Ön",
    "dir.right": "Sağ",
    "dir.back": "Arka",
    "dir.left": "Sol",

    "compass.0": "Ön",
    "compass.45": "Ön-Sağ",
    "compass.90": "Sağ",
    "compass.135": "Sağ-Arka",
    "compass.180": "Arka",
    "compass.225": "Arka-Sol",
    "compass.270": "Sol",
    "compass.315": "Sol-Ön",

    "common.error_prefix": "Hata:",
    "common.seconds": "sn",
  },

  en: {
    "app.title": "WiFi DIRECTION FINDING SYSTEM",
    "app.subtitle": "TACTICAL RDF UNIT · 4-CHANNEL ANTENNA ARRAY",
    "page.title": "WiFi Direction Finder",

    "tab.setup": "SETUP",
    "tab.live": "LIVE TRACK",
    "tab.calib": "CALIBRATION",
    "tab.pos": "POSITION",

    "setup.status.title": "1) SYSTEM STATUS",
    "setup.status.refresh": "Refresh Status",

    "setup.datastop.title": "DATA FLOW STOPPED? (advanced)",
    "setup.datastop.desc": "Known driver limitation: the built-in driver (rtl8xxxu) can silently lose data flow after a while; physically unplugging/replugging fixes it. The button below resets the adapters over USB <strong>in software</strong> (same effect as unplug/replug, without touching anything). Try this first.",
    "setup.datastop.reset_btn": "Reset Adapters (Software)",
    "setup.datastop.altdriver_summary": "If reset doesn't help: install an alternative driver",
    "setup.datastop.altdriver_desc": "Installs the more reliable alternative driver (rtl8188eus) and switches these 4 adapters to it. May take a few minutes; may fail to build on very new kernels.",
    "setup.datastop.altdriver_btn": "Install Alternative Driver",

    "setup.identify.title": "2) IDENTIFY ANTENNAS BY DIRECTION",
    "setup.identify.desc": "Unplug all 4 adapters from USB, then start. You'll be asked to plug in the adapter for each direction one at a time (without unplugging the previous ones). No measurement/WiFi needed — this only maps USB port ↔ direction.",
    "setup.identify.mapped_note": "ℹ Antennas are already mapped. If you want to redo it, press \"Start Identification\" — the existing mapping will be updated.",
    "setup.identify.start_btn": "Start Identification",
    "setup.identify.step_wait": "adapter: plug it in now…",
    "setup.identify.waiting": "waiting",
    "setup.identify.found": "found —",
    "setup.identify.writing_rules": "Writing and enabling rules…",
    "setup.identify.done": "Done.",

    "setup.channel.title": "3) CHANNEL SELECTION & MONITOR MODE",
    "setup.channel.scan_btn": "Scan 2.4GHz Networks",
    "setup.channel.manual_label": "Manual channel:",
    "setup.channel.apply_btn": "Apply Channel & Start Tracking",
    "setup.channel.scanning": "Scanning…",
    "setup.channel.none_found": "No networks found.",
    "setup.channel.select_btn": "Select",
    "setup.channel.applying": "Applying…",
    "setup.channel.applied": "Channel set, tracking started. You can switch to the 'Live Track' tab.",
    "setup.channel.th_ssid": "SSID",
    "setup.channel.th_channel": "Channel",

    "status.adapters_found": "{n} TL-WN722N adapter(s) found",
    "status.antennas_mapped": "Antennas mapped to directions",
    "status.antennas_unmapped": "Antenna mapping not done",
    "status.interfaces": "Interfaces: {list}",
    "status.none": "none",
    "status.channel": "Channel: {ch}",
    "status.channel_unset": "No channel selected",
    "status.tracking_on": "Tracking active",
    "status.tracking_off": "Tracking not started",
    "status.calib_done": "Calibration done",
    "status.calib_missing": "Calibration not done (using default pattern)",
    "status.dist_calib_done": "Distance calibration done (real distances are based on these measurements)",
    "status.dist_calib_missing": "⚠ Distance calibration not done — the shown ~distances are computed from generic default values and may be far from real values. Focus on a device in the 'Live Track' tab and run distance calibration.",
    "status.autoheal_active": "Auto-heal (watchdog): performed an automatic USB reset {n} time(s) when data flow stopped",
    "status.autoheal_idle": "Auto-heal (watchdog): active, no intervention needed yet",
    "status.fetch_failed": "Could not fetch status: {err}",

    "usb_reset.resetting": "Resetting (a few seconds)…",
    "usb_reset.ok_all": "Done, all 4 interfaces came back. Now 'Scan Networks' → pick a channel and 'Apply Channel & Start Tracking'.",
    "usb_reset.ok_partial": "Reset done but only {found}/4 interfaces came back: {list}. Wait a few seconds and try 'Refresh Status'.",

    "altdriver.installing": "Installing (may take a few minutes)…",
    "altdriver.done": "Done. Interfaces: {list}",
    "altdriver.none": "(none found)",

    "live.title": "LIVE DIRECTION TRACKING",
    "live.desc": "The list is sorted alphabetically by SSID and devices that lose signal don't disappear from the list (they just fade). Click a row: the radar focuses on just that device (click again or use \"Clear Focus\" to go back).",
    "live.search_placeholder": "🔎 Search: SSID or MAC…",
    "live.clear_focus": "Clear Focus",
    "live.focused_prefix": "Focused on:",
    "live.click_hint": "Click to focus only on this device",

    "live.dist.title": "Distance calibration for the focused device",
    "live.dist.desc": "Place the device at a known distance (e.g. 1 meter) and measure, then move it to a different distance (e.g. 3-5 meters) and measure again. At least 2 different distances are required; the more you measure, the more accurate it gets.",
    "live.dist.current_label": "Current real distance (m):",
    "live.dist.measure_btn": "Measure At This Distance",
    "live.dist.finish_btn": "Finish Distance Calibration",
    "live.dist.need_focus": "First focus on a device (click a row in the table).",
    "live.dist.need_value": "Enter a valid distance.",
    "live.dist.measuring": "Measuring at {d}m…",
    "live.dist.recorded": "{d}m @ RSSI={rssi} dBm recorded (total {count} points). Now move the device to a different distance and measure again.",
    "live.dist.need_2points": "You need to measure at least 2 different distances.",
    "live.dist.done": "✓ Distance calibration complete. Distance estimates will now be based on these measurements.",

    "live.focus_default": "Select a device from the table to focus.",
    "live.focus_gone": "The focused device ({mac}) is not currently in the list.",
    "live.no_ssid": "(no SSID)",
    "live.f_direction": "Direction:",
    "live.f_distance": "~Distance:",
    "live.f_confidence": "Confidence:",
    "live.f_concentration": "Consistency:",
    "live.f_lastseen": "Last seen:",
    "live.no_signal": "📡 no signal",
    "live.no_signal_lastknown": "📡 no signal (showing last known direction)",
    "live.locked": "✓ Locked ({n})",
    "live.stabilizing": "stabilizing… ({n})",
    "live.seconds_ago": "{s}s ago",

    "live.table.mac": "MAC",
    "live.table.ssid": "SSID",
    "live.table.front": "Front",
    "live.table.right": "Right",
    "live.table.back": "Back",
    "live.table.left": "Left",
    "live.table.bearing": "Bearing° (smoothed)",
    "live.table.compass": "Compass",
    "live.table.confidence": "Confidence",
    "live.table.status": "Status",
    "live.table.distance": "~Distance",
    "live.table.last": "Last",

    "live.stats_hint": "If no devices show up at all, check the diagnostic counters below: \"total\" at 0 means the interfaces see no packets (channel/monitor mode issue); if \"rssi\" is 0 but the others are growing, the driver isn't reporting RSSI.",
    "live.stats.th_dir": "Direction",
    "live.stats.th_total": "Total packets",
    "live.stats.th_dot11": "802.11",
    "live.stats.th_mac": "Has MAC",
    "live.stats.th_radiotap": "Has RadioTap",
    "live.stats.th_rssi": "Has RSSI",

    "calib.title": "ANTENNA GAIN PATTERN CALIBRATION",
    "calib.desc": "Turn on a reference transmitter (e.g. a phone hotspot) and keep it near the antenna. <strong>You don't need to select a MAC</strong> — the system automatically takes the \"strongest device seen\" as the reference on each measurement (the device you hold near the antenna will already be the strongest signal). You can also pick a specific device below if you want.",
    "calib.target_label": "Reference device (optional):",
    "calib.target_auto": "— auto-detect —",
    "calib.target_none": "— no devices visible —",
    "calib.target_select": "— select —",
    "calib.target_hint_none": "Is the reference transmitter broadcasting? Has tracking been started? (Setup tab)",
    "calib.target_hint_count": "{n} device(s) found.",
    "calib.refresh_btn": "Refresh Networks",
    "calib.duration_label": "Measurement duration:",
    "calib.duration_desc": "12s is recommended: in \"Simple\"/\"Precise\" mode the 4 antennas are listened to in rotation (~10s/cycle), so a shorter duration may finish before some antennas even get a turn, giving a wrong result. In \"Unplug-Plug\" mode only one antenna is active at a time, so a shorter duration is fine.",
    "calib.manual_summary": "I want to pick a specific device / it's not in the list, enter MAC manually",
    "calib.manual_mac_label": "Manual MAC:",

    "calib.mode.simple": "1) Simple (4 directions)",
    "calib.mode.precise": "2) Precise (custom angle)",
    "calib.mode.solo": "3) Unplug-Plug (single antenna)",

    "calib.simple.desc": "Place the phone/reference transmitter directly in front of each antenna in turn and press that direction's button. The system checks which antenna read the strongest and tells you whether you placed it correctly.",
    "calib.simple.start_btn": "Start Simple Calibration",
    "calib.simple.place_prefix": "Place the reference transmitter directly in front of the",
    "calib.simple.place_suffix": "antenna.",
    "calib.measure_btn": "Measure",
    "calib.measuring": "Measuring…",
    "calib.target_info": "Target: {ssid} {mac}",
    "calib.simple.confirmed": "✓ Confirmed: the \"{dir}\" antenna read the strongest.",
    "calib.simple.unexpected": "⚠ Unexpected result: the strongest reading came from the \"{strongest}\" antenna, not \"{expected}\". Check whether the reference is in the right direction and the antenna directions are correct. Continuing anyway.",
    "calib.readings_suffix": "Readings: {json}",
    "calib.compute_btn": "Compute Calibration",
    "calib.computed": "Done: g_max={gmax} g_min={gmin} n={n}",
    "calib.computed_done": "✓ Done:",

    "calib.precise.desc": "Hold the reference transmitter at a fixed radius from the device and select <strong>which direction/bracket</strong> it's in relative to the antenna using the buttons below (no need to type an angle by hand — e.g. \"Between Front and Right\" = 45°). You can measure as many different directions as you like — the more, the more accurate.",
    "calib.precise.measuring": "Measuring {label} ({deg}°)…",
    "calib.precise.recorded": "✓ {label} ({deg}°) recorded.",
    "calib.precise.total_points": "(total {n} points)",
    "calib.precise.advanced_summary": "Advanced: measure with an automatic angle sequence",
    "calib.precise.step_label": "Angle step:",
    "calib.precise.auto_start_btn": "Start Automatic Sequence",
    "calib.precise.place_at": "— place the reference transmitter at this position.",

    "calib.solo.warn": "⚠ Do you just want to map which USB port corresponds to which direction (Front/Right/Back/Left) — without measuring, by plugging them in one at a time without unplugging? Then this is the <strong>wrong place</strong>: go to <strong>Setup tab → \"Identify Antennas by Direction\"</strong>. This (Unplug-Plug) section is for a <strong>different purpose</strong>: signal-strength calibration, which requires measurement and single-antenna isolation (testing by unplugging).",
    "calib.solo.desc": "If the 4 antennas don't work reliably at the same time: leave <strong>only one</strong> adapter plugged in at a time and unplug the others. The system tells you which adapter to plug in next, in order: <strong>Front → Left → Right → Back</strong>. Plug in the requested adapter and confirm with <strong>\"Plugged In, Continue\"</strong>, measure a few angles, then press <strong>\"Next Antenna\"</strong> to switch adapters. Each step proceeds only with your confirmation.",
    "calib.solo.begin_btn": "Start Wizard",
    "calib.solo.reset_btn": "Start Over (reset all)",
    "calib.solo.confirm_plug_btn": "Plugged In, Continue",
    "calib.solo.next_btn": "Next Antenna →",
    "calib.solo.complete_btn": "Finish Calibration",
    "calib.solo.th_dir": "Direction",
    "calib.solo.th_count": "Measurement count",
    "calib.solo.only_prefix": "Now plug in ONLY the",
    "calib.solo.only_suffix": "adapter (unplug the others).",
    "calib.solo.ready_prefix": "✓",
    "calib.solo.ready_suffix": "— place the reference transmitter directly in front of it and measure a few of the angles below.",
    "calib.solo.need_begin": "Press 'Start Wizard' first.",
    "calib.solo.measuring": "Measuring {dir} antenna at {delta}°…",
    "calib.solo.recorded": "{dir} @ {delta}°: RSSI={rssi} dBm — {targetInfo} (total {n} measurements for this direction)",
    "calib.solo.reset_done": "Reset.",
    "calib.solo.complete_done": "✓ Calibration Complete!",
    "calib.solo.delta_front": "Straight ahead (0°)",
    "calib.solo.delta_other": "{d}° (relative to the antenna itself)",

    "verify.title": "4) VERIFICATION (Test the Calibration)",
    "verify.desc": "Check after calibration: place the reference transmitter at a direction relative to the antenna that <strong>you know</strong> (or rotate the antenna), select that direction below and press \"Verify\". The system compares the direction it currently computes with the real direction you specified and shows the margin of error.",
    "verify.real_dir_label": "Real direction:",
    "verify.btn": "Verify",
    "verify.need_mac": "Select a specific device from the 'Reference device' field above for verification (auto-detect can't be used here).",
    "verify.checking": "Checking…",
    "verify.not_visible": "This device is not visible right now.",
    "verify.no_bearing": "No direction could be computed for this device yet (insufficient antenna readings).",
    "verify.good": "✓ Good",
    "verify.medium": "⚠ Medium",
    "verify.bad": "✗ Poor",
    "verify.result": "Real direction: <strong>{real}°</strong> — Computed: <strong>{measured}°</strong> — Error: <strong>{err}°</strong>",
    "verify.not_locked_note": "Note: the direction hasn't locked yet, the result may change.",
    "verify.calib_added": "✓ This measurement was added to the calibration and the pattern was recomputed",
    "verify.calib_added_points": "(g_max={gmax} g_min={gmin} n={n}, {count} points total).",
    "verify.calib_added_fail": "This measurement was added to the calibration (point {n}) but recomputation failed: {err}",
    "verify.calib_added_pending": "This measurement was added to the calibration ({n}/4 points) — the pattern will be auto-computed once you verify at least 4 different angles.",

    "pos.title": "MULTI-POINT POSITION INTERSECTION (Triangulation)",
    "pos.desc": "Move the device to known (x,y) meter positions and record at each point. \"Front\" must face the same absolute direction at every point.",
    "pos.x_label": "X (m):",
    "pos.y_label": "Y (m):",
    "pos.duration_label": "Duration:",
    "pos.record_btn": "Record At This Position",
    "pos.calc_btn": "Compute Positions",
    "pos.recording": "Measuring at ({x}, {y})…",
    "pos.recorded": "({x}, {y}): {count} observations recorded.",
    "pos.record_error": "({x}, {y}): Error — {err}",
    "pos.calculating": "Computing…",
    "pos.no_records": "No records.",
    "pos.th_mac": "MAC",
    "pos.th_ssid": "SSID",
    "pos.th_position": "Position",
    "pos.th_stations": "Stations",
    "pos.th_note": "Note",
    "pos.residual_prefix": "residual",

    "dir.front": "Front",
    "dir.right": "Right",
    "dir.back": "Back",
    "dir.left": "Left",

    "compass.0": "Front",
    "compass.45": "Front-Right",
    "compass.90": "Right",
    "compass.135": "Right-Back",
    "compass.180": "Back",
    "compass.225": "Back-Left",
    "compass.270": "Left",
    "compass.315": "Left-Front",

    "common.error_prefix": "Error:",
    "common.seconds": "s",
  },
};

function getLang() {
  try {
    const saved = localStorage.getItem("wifidf_lang");
    if (saved === "tr" || saved === "en") return saved;
  } catch (e) { /* localStorage yoksa (gizli sekme vb.) varsayilana dus */ }
  return "tr";
}

function setLang(lang) {
  if (lang !== "tr" && lang !== "en") return;
  try { localStorage.setItem("wifidf_lang", lang); } catch (e) { /* yoksayilir */ }
  applyStaticI18n();
  document.dispatchEvent(new CustomEvent("langchange"));
}

function t(key, vars) {
  const lang = getLang();
  let s = (I18N[lang] && I18N[lang][key]) || I18N.tr[key] || key;
  if (vars) {
    for (const k in vars) s = s.split(`{${k}}`).join(vars[k]);
  }
  return s;
}

function applyStaticI18n() {
  const lang = getLang();
  document.documentElement.lang = lang;
  document.title = t("page.title");
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-html]").forEach((el) => {
    el.innerHTML = t(el.dataset.i18nHtml);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
  document.querySelectorAll("[data-i18n-title]").forEach((el) => {
    el.title = t(el.dataset.i18nTitle);
  });
  document.querySelectorAll("#lang-toggle button").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.lang === lang);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  applyStaticI18n();
  document.querySelectorAll("#lang-toggle button").forEach((btn) => {
    btn.addEventListener("click", () => setLang(btn.dataset.lang));
  });
});
