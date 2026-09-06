const DIRECTIONS = ["front", "right", "back", "left"];
const DIR_ANGLE = { front: 0, right: 90, back: 180, left: 270 };
function dirLabel(dir) { return t(`dir.${dir}`); }

// 8 yonlu pusula secimi: elle aci yazmak yerine tiklanabilir konumlar (kalibrasyon + dogrulama icin ortak)
const COMPASS_8 = [
  { deg: 0, key: "compass.0" },
  { deg: 45, key: "compass.45" },
  { deg: 90, key: "compass.90" },
  { deg: 135, key: "compass.135" },
  { deg: 180, key: "compass.180" },
  { deg: 225, key: "compass.225" },
  { deg: 270, key: "compass.270" },
  { deg: 315, key: "compass.315" },
];

function circularDiff(a, b) {
  return ((a - b + 180) % 360 + 360) % 360 - 180;
}

let currentTab = "setup";
let liveTimer = null;
let focusedMac = null;
let liveSearchQuery = "";
const STALE_ROW_S = 15; // bu sureden uzun suredir gorulmeyen cihaz "sinyal yok" olarak isaretlenir (listeden SILINMEZ)

// ---------------------------------------------------------------------
// API yardimcilari
// ---------------------------------------------------------------------

async function apiCall(action, params = {}) {
  const res = await fetch(`/api/call/${action}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  return res.json();
}

// ---------------------------------------------------------------------
// Sekmeler
// ---------------------------------------------------------------------

document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
    currentTab = btn.dataset.tab;
    if (currentTab === "live") startLivePolling();
    else stopLivePolling();
    if (currentTab === "calib") refreshCalibTargets();
  });
});

// ---------------------------------------------------------------------
// Sistem durumu
// ---------------------------------------------------------------------

async function refreshStatus() {
  const r = await apiCall("status");
  if (!r.ok) {
    document.getElementById("status-list").innerHTML = `<li class="check-bad"> ${t("status.fetch_failed", { err: r.error })}</li>`;
    return;
  }
  const s = r.data;

  const list = document.getElementById("status-list");
  list.innerHTML = "";
  const items = [
    [s.adapter_count >= 4, t("status.adapters_found", { n: s.adapter_count })],
    [s.antennas_mapped, s.antennas_mapped ? t("status.antennas_mapped") : t("status.antennas_unmapped")],
    [s.interfaces_present.length === 4, t("status.interfaces", { list: s.interfaces_present.join(", ") || t("status.none") })],
    [!!s.channel, s.channel ? t("status.channel", { ch: s.channel }) : t("status.channel_unset")],
    [s.tracking_active, s.tracking_active ? t("status.tracking_on") : t("status.tracking_off")],
    [s.calibration_done, s.calibration_done ? t("status.calib_done") : t("status.calib_missing")],
    [s.distance_calibration_done, s.distance_calibration_done ? t("status.dist_calib_done") : t("status.dist_calib_missing")],
    [true, s.auto_heal_count > 0
      ? t("status.autoheal_active", { n: s.auto_heal_count })
      : t("status.autoheal_idle")],
  ];
  for (const [ok, text] of items) {
    const li = document.createElement("li");
    li.className = ok ? "check-ok" : "check-warn";
    li.textContent = " " + text;
    list.appendChild(li);
  }

  // "identify-card" ARTIK gizlenmiyor - eslesme yapilmis olsa bile
  // kullanici istedigi zaman yeniden tanimlama yapabilmeli (bu daha once
  // "zaten eslenmis" sanilip tamamen gizleniyordu, kullanici bu adimi hic
  // bulamiyordu).
  document.getElementById("identify-mapped-note").hidden = !s.antennas_mapped;
  document.getElementById("channel-card").hidden = !s.antennas_mapped;
}

document.getElementById("btn-refresh-status").addEventListener("click", refreshStatus);

document.getElementById("btn-usb-reset").addEventListener("click", async () => {
  const btn = document.getElementById("btn-usb-reset");
  const box = document.getElementById("usb-reset-result");
  btn.disabled = true;
  box.textContent = t("usb_reset.resetting");
  const res = await apiCall("usb_reset");
  btn.disabled = false;
  if (res.ok) {
    const found = res.data.interfaces_present.length;
    box.textContent = found === 4
      ? t("usb_reset.ok_all")
      : t("usb_reset.ok_partial", { found, list: res.data.interfaces_present.join(", ") || t("status.none") });
    await refreshStatus();
  } else {
    box.textContent = `${t("common.error_prefix")} ${res.error}`;
  }
});

document.getElementById("btn-install-alt-driver").addEventListener("click", async () => {
  const btn = document.getElementById("btn-install-alt-driver");
  const box = document.getElementById("alt-driver-result");
  btn.disabled = true;
  box.textContent = t("altdriver.installing");
  const res = await apiCall("install_alt_driver");
  btn.disabled = false;
  if (res.ok) {
    box.textContent = t("altdriver.done", { list: res.data.interfaces_present.join(", ") || t("altdriver.none") });
    await refreshStatus();
  } else {
    box.textContent = `${t("common.error_prefix")} ${res.error}`;
  }
});

// ---------------------------------------------------------------------
// Anten tanimlama sihirbazi
// ---------------------------------------------------------------------

document.getElementById("btn-identify-start").addEventListener("click", async () => {
  const btn = document.getElementById("btn-identify-start");
  const progress = document.getElementById("identify-progress");
  btn.disabled = true;
  progress.innerHTML = "";
  await apiCall("identify_reset");

  for (const dir of DIRECTIONS) {
    const card = document.createElement("div");
    card.className = "step-card";
    card.innerHTML = `<strong>${dirLabel(dir)}</strong> ${t("setup.identify.step_wait")} <span class="spinner">${t("setup.identify.waiting")}</span>`;
    progress.appendChild(card);

    let found = null;
    while (!found) {
      await new Promise((r) => setTimeout(r, 1000));
      const res = await apiCall("identify_check", { direction: dir });
      if (res.ok && res.data.found) found = res.data;
    }
    card.classList.add("done");
    card.innerHTML = `<strong>${dirLabel(dir)}</strong>: ${t("setup.identify.found")} ${found.iface} <span class="pill">${found.mac || "?"}</span>`;
  }

  const finishMsg = document.createElement("p");
  finishMsg.textContent = t("setup.identify.writing_rules");
  progress.appendChild(finishMsg);
  const fin = await apiCall("identify_finish");
  finishMsg.textContent = fin.ok ? t("setup.identify.done") : `${t("common.error_prefix")} ${fin.error}`;
  btn.disabled = false;
  await refreshStatus();
});

// ---------------------------------------------------------------------
// Kanal secimi + monitor mode
// ---------------------------------------------------------------------

document.getElementById("btn-scan").addEventListener("click", async () => {
  const box = document.getElementById("scan-results");
  box.textContent = t("setup.channel.scanning");
  const res = await apiCall("scan", { iface: "wlandf_front" });
  if (!res.ok) { box.textContent = `${t("common.error_prefix")} ${res.error}`; return; }
  const nets = res.data.networks;
  if (!nets.length) { box.textContent = t("setup.channel.none_found"); return; }
  const table = document.createElement("table");
  table.innerHTML = `<thead><tr><th>${t("setup.channel.th_ssid")}</th><th>${t("setup.channel.th_channel")}</th><th></th></tr></thead>`;
  const tbody = document.createElement("tbody");
  for (const n of nets) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${n.ssid}</td><td>${n.channel}</td><td></td>`;
    const btn = document.createElement("button");
    btn.textContent = t("setup.channel.select_btn");
    btn.addEventListener("click", () => {
      document.getElementById("manual-channel").value = n.channel;
    });
    tr.lastElementChild.appendChild(btn);
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  box.innerHTML = "";
  box.appendChild(table);
});

document.getElementById("btn-apply-channel").addEventListener("click", async () => {
  const status = document.getElementById("channel-status");
  const ch = document.getElementById("manual-channel").value;
  status.textContent = t("setup.channel.applying");
  const r1 = await apiCall("monitor_mode", { channel: ch ? parseInt(ch, 10) : null });
  if (!r1.ok) { status.textContent = `${t("common.error_prefix")} ${r1.error}`; return; }
  const r2 = await apiCall("start_tracking");
  status.textContent = r2.ok ? t("setup.channel.applied") : `${t("common.error_prefix")} ${r2.error}`;
  await refreshStatus();
});

// ---------------------------------------------------------------------
// Canli takip
// ---------------------------------------------------------------------

function startLivePolling() {
  if (liveTimer) return;
  pollDevices();
  liveTimer = setInterval(pollDevices, 1000);
}

function stopLivePolling() {
  if (liveTimer) { clearInterval(liveTimer); liveTimer = null; }
}

// Gosterim icin yon/pusula/mesafe: once GUNCEL (smoothed_bearing_deg/
// bearing_deg), yoksa SON BILINEN (last_known_*, sinyal gecici kesilse
// bile) deger kullanilir. "isLastKnown" bayragi, cagiran kodun isterse
// bunu ayirt etmesini saglar (su an sadece stale-row/pill zaten "sinyal
// yok" gosteriyor, bu yeterli oldugu icin ayrica kullanilmiyor).
// NOT: locked/stable_count/confidence de ayni "guncel yoksa son bilinen"
// mantigina dahil edildi. Sebep: rotasyonlu yakalamada bir cihazin bir
// yonu, sinyal aslinda kesilmemisken bile sadece o anki 12sn'lik pencerede
// sans eseri taze ornek almamis olabilir - bu TEK pollde bearing hesabi
// basarisiz olup ham locked/stable_count SIFIRA doner. Bunu dogrudan
// gosterirsek, aslinda kararli/kilitli bir cihaz arayuzde her bir-iki
// pollde bir "kilit bozuldu, 0" diye titrer - kullaniciya "cihaz
// bulunamiyor" izlenimi verir. Son bilinen degere dusmek bu titremeyi
// onler (stale-row/"son bilinen yon" isareti zaten ayri bir uyari verdigi
// icin yaniltici olmaz).
function displayBearing(d) {
  if (d.smoothed_bearing_deg !== null) {
    return { deg: d.smoothed_bearing_deg, compass: d.compass, distance: d.distance_m, locked: d.locked, stableCount: d.stable_count, confidence: d.confidence, concentration: d.concentration, isLastKnown: false };
  }
  if (d.bearing_deg !== null) {
    return { deg: d.bearing_deg, compass: d.compass, distance: d.distance_m, locked: d.locked, stableCount: d.stable_count, confidence: d.confidence, concentration: d.concentration, isLastKnown: false };
  }
  if (d.last_known_bearing_deg !== null && d.last_known_bearing_deg !== undefined) {
    return {
      deg: d.last_known_bearing_deg, compass: d.last_known_compass, distance: d.last_known_distance_m,
      locked: d.last_known_locked, stableCount: d.last_known_stable_count, confidence: d.last_known_confidence,
      concentration: d.last_known_concentration,
      isLastKnown: true,
    };
  }
  return { deg: null, compass: null, distance: null, locked: false, stableCount: 0, confidence: null, concentration: 0, isLastKnown: false };
}

async function pollDevices() {
  const res = await apiCall("get_devices");
  if (!res.ok) return;
  const devices = res.data.devices;
  const radarDevices = focusedMac ? devices.filter((d) => d.mac === focusedMac) : devices;
  renderDevicesTable(devices);
  renderRadar(radarDevices);
  renderFocusInfo(devices);

  const statsRes = await apiCall("capture_stats");
  if (statsRes.ok) renderStatsTable(statsRes.data.stats);
}

function renderFocusInfo(devices) {
  const box = document.getElementById("radar-focus-info");
  if (!focusedMac) {
    box.innerHTML = `<span class="muted">${t("live.focus_default")}</span>`;
    return;
  }
  const d = devices.find((x) => x.mac === focusedMac);
  if (!d) {
    box.innerHTML = `<span class="muted">${t("live.focus_gone", { mac: focusedMac })}</span>`;
    return;
  }
  const b = displayBearing(d);
  const age = Date.now() / 1000 - d.last_seen;
  const stale = age > STALE_ROW_S;
  const statusPill = stale
    ? `<span class="pill">${b.isLastKnown ? t("live.no_signal_lastknown") : t("live.no_signal")}</span>`
    : (b.locked
        ? `<span class="pill pill-locked">${t("live.locked", { n: b.stableCount })}</span>`
        : `<span class="pill">${t("live.stabilizing", { n: b.stableCount })}</span>`);
  box.innerHTML = `
    <div style="font-weight:600;margin-bottom:8px">${d.ssid || t("live.no_ssid")}<br><span class="muted" style="font-weight:400;font-size:0.8rem">${d.mac}</span></div>
    <div style="display:grid;grid-template-columns:auto auto;gap:4px 12px;font-size:0.9rem">
      <span class="muted">${t("live.f_direction")}</span><strong>${b.deg !== null ? b.deg.toFixed(0) + "° " + (b.compass || "") : "-"}</strong>
      <span class="muted">${t("live.f_distance")}</span><strong>${b.distance ? b.distance.toFixed(1) + " m" : "-"}</strong>
      <span class="muted">${t("live.f_confidence")}</span><strong>${b.confidence !== null && b.confidence !== undefined ? (b.confidence * 100).toFixed(0) + "%" : "-"}</strong>
      <span class="muted">${t("live.f_concentration")}</span><strong>${b.concentration !== null && b.concentration !== undefined ? (b.concentration * 100).toFixed(0) + "%" : "-"}</strong>
      <span class="muted">${t("live.f_lastseen")}</span><strong>${t("live.seconds_ago", { s: age.toFixed(0) })}</strong>
    </div>
    <div style="margin-top:8px">${statusPill}</div>
  `;
}

document.getElementById("btn-clear-focus").addEventListener("click", () => setFocus(null));

document.getElementById("live-search").addEventListener("input", (e) => {
  liveSearchQuery = e.target.value.trim().toLowerCase();
});

function setFocus(mac) {
  focusedMac = focusedMac === mac ? null : mac;
  const banner = document.getElementById("focus-banner");
  const distPanel = document.getElementById("distance-calib-panel");
  if (focusedMac) {
    banner.hidden = false;
    banner.querySelector("span").textContent = `${t("live.focused_prefix")} ${focusedMac}`;
    distPanel.hidden = false;
    document.getElementById("distance-calib-result").textContent = "";
  } else {
    banner.hidden = true;
    distPanel.hidden = true;
    document.getElementById("radar-focus-info").innerHTML = `<span class="muted">${t("live.focus_default")}</span>`;
  }
}

function renderStatsTable(stats) {
  const tbody = document.querySelector("#stats-table tbody");
  tbody.innerHTML = "";
  for (const dir of DIRECTIONS) {
    const s = stats[dir] || { total: 0, dot11: 0, has_mac: 0, radiotap: 0, rssi: 0 };
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${dirLabel(dir)}</td><td>${s.total}</td><td>${s.dot11}</td><td>${s.has_mac}</td><td>${s.radiotap}</td><td>${s.rssi}</td>`;
    tbody.appendChild(tr);
  }
}

function renderDevicesTable(devices) {
  const tbody = document.querySelector("#devices-table tbody");
  tbody.innerHTML = "";
  const now = Date.now() / 1000;

  let list = devices;
  if (liveSearchQuery) {
    list = list.filter((d) =>
      (d.ssid || "").toLowerCase().includes(liveSearchQuery) ||
      d.mac.toLowerCase().includes(liveSearchQuery)
    );
  }
  // Alfabetik siralama (SSID'ye gore) - boylece liste her poll'da (last_seen
  // degistikce) yeniden karismaz, satirlar hep ayni sirada durur ve
  // odaklanmak icin dogru satiri bulmak kolaylasir. Ismi (SSID) olmayan
  // cihazlar (gizli SSID / cihazdan gelen probe vb.) alfabetik sirayi
  // bozmasin diye en sona atilir, aralarinda MAC'e gore siralanir.
  list = [...list].sort((a, b) => {
    if (!!a.ssid !== !!b.ssid) return a.ssid ? -1 : 1;
    return (a.ssid || a.mac).localeCompare(b.ssid || b.mac, "tr");
  });

  for (const d of list) {
    const age = now - d.last_seen;
    const stale = age > STALE_ROW_S;
    const tr = document.createElement("tr");
    tr.className = "clickable-row" + (d.mac === focusedMac ? " focused-row" : "") + (stale ? " stale-row" : "");
    tr.title = t("live.click_hint");
    const r = d.readings || {};
    const bd = displayBearing(d);
    const statusPill = stale
      ? `<span class="pill">${t("live.no_signal")}</span>`
      : (bd.locked
          ? `<span class="pill pill-locked">${t("live.locked", { n: bd.stableCount })}</span>`
          : (bd.deg !== null ? `<span class="pill">${t("live.stabilizing", { n: bd.stableCount })}</span>` : "-"));
    tr.innerHTML = `
      <td>${d.mac}</td>
      <td>${d.ssid || "-"}</td>
      <td>${r.front !== undefined ? r.front.toFixed(0) : "-"}</td>
      <td>${r.right !== undefined ? r.right.toFixed(0) : "-"}</td>
      <td>${r.back !== undefined ? r.back.toFixed(0) : "-"}</td>
      <td>${r.left !== undefined ? r.left.toFixed(0) : "-"}</td>
      <td>${bd.deg !== null ? bd.deg.toFixed(0) : "-"}</td>
      <td>${bd.compass || "-"}</td>
      <td>${bd.confidence !== null && bd.confidence !== undefined ? (bd.confidence * 100).toFixed(0) + "%" : "-"}</td>
      <td>${statusPill}</td>
      <td>${bd.distance ? bd.distance.toFixed(1) + "m" : "-"}</td>
      <td>${age.toFixed(0)}s${stale ? " ⚠" : ""}</td>
    `;
    tr.addEventListener("click", () => setFocus(d.mac));
    tbody.appendChild(tr);
  }
}

const SVG_NS = "http://www.w3.org/2000/svg";

function renderRadar(devices) {
  const svg = document.getElementById("radar");
  svg.innerHTML = "";

  // es merkezli mesafe halkalari (25/50/75/100%) + artı-isareti (crosshair) -
  // saf kozmetik, taktik radar ekrani hissini guclendirir.
  for (const frac of [0.25, 0.5, 0.75, 1.0]) {
    const ring = document.createElementNS(SVG_NS, "circle");
    ring.setAttribute("cx", 0); ring.setAttribute("cy", 0); ring.setAttribute("r", 95 * frac);
    ring.setAttribute("fill", "none"); ring.setAttribute("stroke", frac === 1.0 ? "#3d4a58" : "#1f2830");
    ring.setAttribute("stroke-width", frac === 1.0 ? "1.2" : "0.6");
    svg.appendChild(ring);
  }
  for (const [x1, y1, x2, y2] of [[0, -95, 0, 95], [-95, 0, 95, 0]]) {
    const axis = document.createElementNS(SVG_NS, "line");
    axis.setAttribute("x1", x1); axis.setAttribute("y1", y1); axis.setAttribute("x2", x2); axis.setAttribute("y2", y2);
    axis.setAttribute("stroke", "#1a222b"); axis.setAttribute("stroke-width", "0.6");
    svg.appendChild(axis);
  }

  for (const [dir, angle] of Object.entries(DIR_ANGLE)) {
    const rad = (angle * Math.PI) / 180;
    const x = 105 * Math.sin(rad), y = -105 * Math.cos(rad);
    const t2 = document.createElementNS(SVG_NS, "text");
    t2.setAttribute("x", x); t2.setAttribute("y", y);
    t2.setAttribute("fill", "#7c8896"); t2.setAttribute("font-size", "11");
    t2.setAttribute("text-anchor", "middle"); t2.setAttribute("dominant-baseline", "middle");
    t2.textContent = dirLabel(dir);
    svg.appendChild(t2);
  }

  devices.forEach((d, i) => {
    const bd = displayBearing(d);
    if (bd.deg === null) return;
    const rad = (bd.deg * Math.PI) / 180;
    const conf = bd.confidence || 0.3;
    const r = 80;
    const x = r * Math.sin(rad), y = -r * Math.cos(rad);
    // Son bilinen (su an sinyal yok) bir yon gosteriliyorsa kesikli/soluk
    // cizgi ile ayirt edilir - kullanici bunun canli olmadigini anlasin.
    const lastKnownDash = bd.isLastKnown ? "4,3" : "none";
    const opacityScale = bd.isLastKnown ? 0.5 : 1;

    const line = document.createElementNS(SVG_NS, "line");
    line.setAttribute("x1", 0); line.setAttribute("y1", 0);
    line.setAttribute("x2", x); line.setAttribute("y2", y);
    line.setAttribute("stroke", bd.locked ? "#34d399" : "#22d3ee");
    line.setAttribute("stroke-width", bd.locked ? "2.5" : "1.5");
    line.setAttribute("stroke-opacity", Math.max(0.25, conf) * opacityScale);
    line.setAttribute("stroke-dasharray", lastKnownDash);
    svg.appendChild(line);

    const dot = document.createElementNS(SVG_NS, "circle");
    dot.setAttribute("cx", x); dot.setAttribute("cy", y); dot.setAttribute("r", bd.locked ? 5 : 4);
    dot.setAttribute("fill", bd.locked ? "#34d399" : "#22d3ee");
    dot.setAttribute("fill-opacity", opacityScale);
    svg.appendChild(dot);

    const label = document.createElementNS(SVG_NS, "text");
    label.setAttribute("x", x); label.setAttribute("y", y - 8);
    label.setAttribute("fill", "#e4e9ee"); label.setAttribute("font-size", "9");
    label.setAttribute("text-anchor", "middle");
    label.textContent = (bd.locked ? "✓ " : "") + (d.ssid || d.mac.slice(-5));
    svg.appendChild(label);
  });
}

// ---------------------------------------------------------------------
// Mesafe kalibrasyonu (odaklanilan cihaz icin gercege yakin ~mesafe)
// ---------------------------------------------------------------------

let distanceCalibCount = 0;

document.getElementById("btn-distance-calib-measure").addEventListener("click", async () => {
  if (!focusedMac) { alert(t("live.dist.need_focus")); return; }
  const distanceInput = document.getElementById("distance-calib-input");
  const distance_m = parseFloat(distanceInput.value);
  if (!distance_m || distance_m <= 0) { alert(t("live.dist.need_value")); return; }
  const btn = document.getElementById("btn-distance-calib-measure");
  const box = document.getElementById("distance-calib-result");
  btn.disabled = true;
  box.textContent = t("live.dist.measuring", { d: distance_m });
  const res = await apiCall("distance_calib_step", { mac: focusedMac, distance_m, duration: 5 });
  btn.disabled = false;
  if (res.ok) {
    distanceCalibCount = res.data.count;
    box.textContent = t("live.dist.recorded", { d: distance_m, rssi: res.data.rssi.toFixed(1), count: distanceCalibCount });
  } else {
    box.textContent = `${t("common.error_prefix")} ${res.error}`;
  }
});

document.getElementById("btn-distance-calib-finish").addEventListener("click", async () => {
  const btn = document.getElementById("btn-distance-calib-finish");
  const box = document.getElementById("distance-calib-result");
  if (distanceCalibCount < 2) { alert(t("live.dist.need_2points")); return; }
  btn.disabled = true;
  const res = await apiCall("distance_calib_finish");
  btn.disabled = false;
  if (res.ok) {
    box.innerHTML = `<strong style="color:var(--good)">${t("live.dist.done")}</strong>`;
    distanceCalibCount = 0;
    await apiCall("distance_calib_reset");
  } else {
    box.textContent = `${t("common.error_prefix")} ${res.error}`;
  }
});

// ---------------------------------------------------------------------
// Kalibrasyon
// ---------------------------------------------------------------------

const CALIB_MODES = ["simple", "precise", "solo"];
function selectCalibMode(mode) {
  for (const m of CALIB_MODES) {
    document.getElementById(`mode-${m}`).classList.toggle("active", m === mode);
    document.getElementById(`calib-${m}`).hidden = m !== mode;
  }
}
for (const m of CALIB_MODES) {
  document.getElementById(`mode-${m}`).addEventListener("click", () => selectCalibMode(m));
}

// --- Referans hedef secimi: gorulen cihazlardan otomatik MAC (elle yazma yerine) ---

async function refreshCalibTargets() {
  const select = document.getElementById("calib-target-select");
  const hint = document.getElementById("calib-target-hint");
  const prev = select.value;
  const res = await apiCall("get_devices");
  if (!res.ok) { hint.textContent = `${t("common.error_prefix")} ${res.error}`; return; }
  const devices = res.data.devices;
  select.innerHTML = "";
  if (!devices.length) {
    select.innerHTML = `<option value="">${t("calib.target_none")}</option>`;
    hint.textContent = t("calib.target_hint_none");
    return;
  }
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = t("calib.target_select");
  select.appendChild(placeholder);
  for (const d of devices) {
    const opt = document.createElement("option");
    opt.value = d.mac;
    opt.textContent = `${d.ssid || t("live.no_ssid")} — ${d.mac}`;
    select.appendChild(opt);
  }
  if ([...select.options].some((o) => o.value === prev)) select.value = prev;
  hint.textContent = t("calib.target_hint_count", { n: devices.length });
}

document.getElementById("btn-calib-refresh-targets").addEventListener("click", refreshCalibTargets);

function getCalibMac() {
  const selected = document.getElementById("calib-target-select").value;
  if (selected) return selected;
  return document.getElementById("calib-mac").value.trim();
}

// --- 1) Basit kalibrasyon: 4 kardinal yon (Ön/Sağ/Arka/Sol), otomatik dogrulamali ---
document.getElementById("btn-calib-simple-start").addEventListener("click", async () => {
  const mac = getCalibMac(); // bos olabilir - backend en guclu sinyali otomatik hedef alir
  const duration = parseFloat(document.getElementById("calib-duration").value) || 12;

  const btn = document.getElementById("btn-calib-simple-start");
  const progress = document.getElementById("calib-simple-progress");
  btn.disabled = true;
  progress.innerHTML = "";
  await apiCall("calibration_reset");

  for (const dir of DIRECTIONS) {
    await new Promise((resolve) => {
      const card = document.createElement("div");
      card.className = "step-card";
      card.innerHTML = `${t("calib.simple.place_prefix")} <strong>${dirLabel(dir)}</strong> ${t("calib.simple.place_suffix")} `;
      const measureBtn = document.createElement("button");
      measureBtn.className = "primary";
      measureBtn.textContent = t("calib.measure_btn");
      card.appendChild(measureBtn);
      const result = document.createElement("div");
      card.appendChild(result);
      progress.appendChild(card);

      measureBtn.addEventListener("click", async () => {
        measureBtn.disabled = true;
        result.textContent = t("calib.measuring");
        const res = await apiCall("calibration_step", { mac, angle: DIR_ANGLE[dir], duration });
        if (!res.ok) {
          result.innerHTML = `<span class="verify-warn">${t("common.error_prefix")} ${res.error}</span>`;
          measureBtn.disabled = false;
          return;
        }
        const readings = res.data.readings;
        const strongest = Object.entries(readings).sort((a, b) => b[1] - a[1])[0][0];
        const targetInfo = t("calib.target_info", { ssid: res.data.ssid || t("live.no_ssid"), mac: res.data.mac || "" });
        card.classList.add("done");
        if (strongest === dir) {
          result.innerHTML = `<span class="verify-ok">${t("calib.simple.confirmed", { dir: dirLabel(dir) })}</span> ${targetInfo} — ${t("calib.readings_suffix", { json: JSON.stringify(readings) })}`;
        } else {
          result.innerHTML = `<span class="verify-warn">${t("calib.simple.unexpected", { strongest: dirLabel(strongest), expected: dirLabel(dir) })}</span> ${targetInfo} — ${t("calib.readings_suffix", { json: JSON.stringify(readings) })}`;
        }
        resolve();
      });
    });
  }

  const finishCard = document.createElement("div");
  finishCard.className = "step-card";
  const finishBtn = document.createElement("button");
  finishBtn.className = "primary";
  finishBtn.textContent = t("calib.compute_btn");
  finishCard.appendChild(finishBtn);
  const finishResult = document.createElement("div");
  finishCard.appendChild(finishResult);
  progress.appendChild(finishCard);

  finishBtn.addEventListener("click", async () => {
    finishBtn.disabled = true;
    const res = await apiCall("calibration_finish");
    if (res.ok) {
      finishResult.textContent = t("calib.computed", { gmax: res.data.g_max.toFixed(1), gmin: res.data.g_min.toFixed(1), n: res.data.n.toFixed(2) });
      await refreshStatus();
    } else {
      finishResult.textContent = `${t("common.error_prefix")} ${res.error}`;
      finishBtn.disabled = false;
    }
  });

  btn.disabled = false;
});

// --- 2) Hassas kalibrasyon: 8 yonlu pusula butonlariyla hizli olcum ---
function buildPreciseCompassButtons() {
  const box = document.getElementById("calib-precise-compass-buttons");
  box.innerHTML = "";
  for (const { deg, key } of COMPASS_8) {
    const label = t(key);
    const btn = document.createElement("button");
    btn.textContent = `${label} (${deg}°)`;
    btn.className = "secondary";
    btn.addEventListener("click", async () => {
      const mac = getCalibMac();
      const duration = parseFloat(document.getElementById("calib-duration").value) || 12;
      const result = document.getElementById("calib-precise-result");
      btn.disabled = true;
      result.textContent = t("calib.precise.measuring", { label, deg });
      const res = await apiCall("calibration_step", { mac, angle: deg, duration });
      btn.disabled = false;
      if (res.ok) {
        result.innerHTML = `<span class="verify-ok">${t("calib.precise.recorded", { label, deg })}</span> ${t("calib.target_info", { ssid: res.data.ssid || t("live.no_ssid"), mac: res.data.mac || "" })} — ${t("calib.readings_suffix", { json: JSON.stringify(res.data.readings) })} ${t("calib.precise.total_points", { n: res.data.rounds_done })}`;
      } else {
        result.innerHTML = `<span class="verify-warn">${t("common.error_prefix")} ${res.error}</span>`;
      }
    });
    box.appendChild(btn);
  }
}
buildPreciseCompassButtons();

document.getElementById("btn-calib-precise-finish").addEventListener("click", async () => {
  const btn = document.getElementById("btn-calib-precise-finish");
  const box = document.getElementById("calib-precise-finish-result");
  btn.disabled = true;
  const res = await apiCall("calibration_finish");
  btn.disabled = false;
  if (res.ok) {
    box.innerHTML = `<strong style="color:var(--good)">${t("calib.computed_done")}</strong> g_max=${res.data.g_max.toFixed(1)} g_min=${res.data.g_min.toFixed(1)} n=${res.data.n.toFixed(2)}`;
    await refreshStatus();
  } else {
    box.textContent = `${t("common.error_prefix")} ${res.error}`;
  }
});

// --- Otomatik aci dizisi (gelismis, mevcut yontem) ---
document.getElementById("btn-calib-start").addEventListener("click", async () => {
  const mac = getCalibMac(); // bos olabilir - backend en guclu sinyali otomatik hedef alir
  const step = parseFloat(document.getElementById("calib-step").value) || 30;
  const duration = parseFloat(document.getElementById("calib-duration").value) || 12;

  const progress = document.getElementById("calib-progress");
  progress.innerHTML = "";
  await apiCall("calibration_reset");

  const angles = [];
  for (let a = 0; a < 360; a += step) angles.push(a);

  for (const angle of angles) {
    await new Promise((resolve) => {
      const card = document.createElement("div");
      card.className = "step-card";
      card.innerHTML = `<strong>${angle}°</strong> ${t("calib.precise.place_at")} `;
      const btn = document.createElement("button");
      btn.className = "primary";
      btn.textContent = t("calib.measure_btn");
      card.appendChild(btn);
      const result = document.createElement("div");
      card.appendChild(result);
      progress.appendChild(card);

      btn.addEventListener("click", async () => {
        btn.disabled = true;
        result.textContent = t("calib.measuring");
        const res = await apiCall("calibration_step", { mac, angle, duration });
        if (res.ok) {
          card.classList.add("done");
          result.textContent = `${t("calib.target_info", { ssid: res.data.ssid || t("live.no_ssid"), mac: res.data.mac || "" })} — ${t("calib.readings_suffix", { json: JSON.stringify(res.data.readings) })}`;
          resolve();
        } else {
          result.textContent = `${t("common.error_prefix")} ${res.error}`;
          btn.disabled = false;
        }
      });
    });
  }

  const finishCard = document.createElement("div");
  finishCard.className = "step-card";
  const finishBtn = document.createElement("button");
  finishBtn.className = "primary";
  finishBtn.textContent = t("calib.compute_btn");
  finishCard.appendChild(finishBtn);
  const finishResult = document.createElement("div");
  finishCard.appendChild(finishResult);
  progress.appendChild(finishCard);

  finishBtn.addEventListener("click", async () => {
    finishBtn.disabled = true;
    const res = await apiCall("calibration_finish");
    if (res.ok) {
      finishResult.textContent = t("calib.computed", { gmax: res.data.g_max.toFixed(1), gmin: res.data.g_min.toFixed(1), n: res.data.n.toFixed(2) });
      await refreshStatus();
    } else {
      finishResult.textContent = `${t("common.error_prefix")} ${res.error}`;
      finishBtn.disabled = false;
    }
  });
});

// --- 3) Tak-Cikar kalibrasyonu: tek anten, ON -> SOL -> SAG -> ARKA ---
// Kullanicinin isteği uzerine: otomatik USB alg1lama YOK, her adim
// kullanicinin kendi onayladigi butonlarla ilerler ("Taktım, Devam Et" /
// "Sıradaki Antene Geç"). Sistem sadece HANGI yonun sirada oldugunu soyler.

const SOLO_DELTAS = [0, 45, 90, 135, 180, 225, 270, 315];
const SOLO_ORDER = ["front", "left", "right", "back"];
const soloProgress = { front: 0, right: 0, back: 0, left: 0 };
let soloStepIndex = -1;       // -1 = sihirbaz henuz baslamadi
let soloAwaitingPlug = true;  // true = "taktım" onayi bekleniyor, false = olcum asamasinda

function buildSoloDeltaButtons() {
  const box = document.getElementById("solo-delta-buttons");
  box.innerHTML = "";
  for (const delta of SOLO_DELTAS) {
    const btn = document.createElement("button");
    // NOT: bu aci, cihazin "On"une gore DEGIL, o an takili olan TEK antenin
    // KENDI baktigi yone gore (0=tam onu) - diger modlardaki "Ön (0°)" gibi
    // cihaz-geneli acilarla karistirilmasin diye ayri sekilde etiketlenir.
    btn.textContent = delta === 0 ? t("calib.solo.delta_front") : t("calib.solo.delta_other", { d: delta });
    btn.className = "secondary";
    btn.addEventListener("click", () => soloMeasure(delta, btn));
    box.appendChild(btn);
  }
}
buildSoloDeltaButtons();

function renderSoloProgress() {
  const tbody = document.querySelector("#solo-progress-table tbody");
  tbody.innerHTML = "";
  for (const d of DIRECTIONS) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${dirLabel(d)}</td><td>${soloProgress[d]}</td>`;
    tbody.appendChild(tr);
  }
}
renderSoloProgress();

function soloCurrentDirection() {
  return soloStepIndex >= 0 && soloStepIndex < SOLO_ORDER.length ? SOLO_ORDER[soloStepIndex] : null;
}

function renderSoloStep() {
  const direction = soloCurrentDirection();
  const statusLine = document.getElementById("solo-status-line");
  const plugStep = document.getElementById("solo-plug-step");
  const measureStep = document.getElementById("solo-measure-step");
  const completeBtn = document.getElementById("btn-solo-complete");
  const nextBtn = document.getElementById("btn-solo-next-antenna");

  if (!direction) {
    document.getElementById("solo-wizard").hidden = true;
    return;
  }
  document.getElementById("solo-wizard").hidden = false;
  const isLast = soloStepIndex === SOLO_ORDER.length - 1;

  if (soloAwaitingPlug) {
    statusLine.innerHTML = `${t("calib.solo.only_prefix")} <span style="color:var(--accent)">"${dirLabel(direction)}"</span> ${t("calib.solo.only_suffix")}`;
    plugStep.hidden = false;
    measureStep.hidden = true;
  } else {
    statusLine.innerHTML = `${t("calib.solo.ready_prefix")} "${dirLabel(direction)}" ${t("calib.solo.ready_suffix")}`;
    plugStep.hidden = true;
    measureStep.hidden = false;
    nextBtn.hidden = isLast;
    completeBtn.hidden = !isLast;
  }
}

document.getElementById("btn-solo-begin").addEventListener("click", async () => {
  await apiCall("solo_calibration_reset"); // MAC secmek opsiyonel - backend en guclu sinyali otomatik hedef alir
  for (const d of DIRECTIONS) soloProgress[d] = 0;
  renderSoloProgress();
  soloStepIndex = 0;
  soloAwaitingPlug = true;
  document.getElementById("solo-measure-result").textContent = "";
  document.getElementById("solo-finish-result").textContent = "";
  renderSoloStep();
});

document.getElementById("btn-solo-confirm-plug").addEventListener("click", () => {
  soloAwaitingPlug = false;
  document.getElementById("solo-measure-result").textContent = "";
  renderSoloStep();
});

document.getElementById("btn-solo-next-antenna").addEventListener("click", () => {
  if (soloStepIndex < SOLO_ORDER.length - 1) {
    soloStepIndex += 1;
    soloAwaitingPlug = true;
    document.getElementById("solo-measure-result").textContent = "";
    renderSoloStep();
  }
});

async function soloMeasure(delta, btn) {
  const mac = getCalibMac(); // bos olabilir - backend en guclu sinyali otomatik hedef alir
  const direction = soloCurrentDirection();
  if (!direction) { alert(t("calib.solo.need_begin")); return; }
  const duration = parseFloat(document.getElementById("calib-duration").value) || 5;
  const result = document.getElementById("solo-measure-result");

  btn.disabled = true;
  result.textContent = t("calib.solo.measuring", { dir: dirLabel(direction), delta });
  const res = await apiCall("solo_calibration_step", { direction, mac, delta, duration });
  btn.disabled = false;
  if (res.ok) {
    soloProgress[direction] = res.data.count;
    renderSoloProgress();
    const targetInfo = t("calib.target_info", { ssid: res.data.ssid || t("live.no_ssid"), mac: res.data.mac || "?" });
    result.textContent = t("calib.solo.recorded", { dir: dirLabel(direction), delta, rssi: res.data.rssi.toFixed(1), targetInfo, n: res.data.count });
  } else {
    result.textContent = `${t("common.error_prefix")} ${res.error}`;
  }
}

document.getElementById("btn-solo-reset").addEventListener("click", async () => {
  await apiCall("solo_calibration_reset");
  for (const d of DIRECTIONS) soloProgress[d] = 0;
  renderSoloProgress();
  soloStepIndex = -1;
  soloAwaitingPlug = true;
  document.getElementById("solo-wizard").hidden = true;
  document.getElementById("solo-measure-result").textContent = t("calib.solo.reset_done");
  document.getElementById("solo-finish-result").textContent = "";
});

document.getElementById("btn-solo-complete").addEventListener("click", async () => {
  const btn = document.getElementById("btn-solo-complete");
  const box = document.getElementById("solo-finish-result");
  btn.disabled = true;
  const res = await apiCall("solo_calibration_finish");
  btn.disabled = false;
  if (res.ok) {
    box.innerHTML = `<strong style="color:var(--good)">${t("calib.solo.complete_done")}</strong> g_max=${res.data.g_max.toFixed(1)} g_min=${res.data.g_min.toFixed(1)} n=${res.data.n.toFixed(2)}`;
    for (const d of DIRECTIONS) soloProgress[d] = 0;
    renderSoloProgress();
    soloStepIndex = -1;
    soloAwaitingPlug = true;
    document.getElementById("solo-wizard").hidden = true;
    await refreshStatus();
  } else {
    box.textContent = `${t("common.error_prefix")} ${res.error}`;
  }
});

// --- 4) Dogrulama: bilinen gercek yonle hesaplanan yonu karsilastir ---

let verifyAngle = 0;
let verifyAngleKey = "compass.0";

function buildVerifyCompassButtons() {
  const box = document.getElementById("verify-compass-buttons");
  const label = document.getElementById("verify-angle-label");
  box.innerHTML = "";
  for (const { deg, key } of COMPASS_8) {
    const text = t(key);
    const btn = document.createElement("button");
    btn.textContent = `${text} (${deg}°)`;
    btn.className = "secondary";
    btn.addEventListener("click", () => {
      verifyAngle = deg;
      verifyAngleKey = key;
      label.textContent = `${text} (${deg}°)`;
    });
    box.appendChild(btn);
  }
  label.textContent = `${t(verifyAngleKey)} (${verifyAngle}°)`;
}
buildVerifyCompassButtons();

document.getElementById("btn-verify").addEventListener("click", async () => {
  const mac = getCalibMac();
  const box = document.getElementById("verify-result");
  if (!mac) { alert(t("verify.need_mac")); return; }

  box.textContent = t("verify.checking");
  const res = await apiCall("get_devices");
  if (!res.ok) { box.textContent = `${t("common.error_prefix")} ${res.error}`; return; }
  const dev = res.data.devices.find((d) => d.mac.toLowerCase() === mac.toLowerCase());
  if (!dev) { box.textContent = t("verify.not_visible"); return; }

  const measured = dev.smoothed_bearing_deg !== null ? dev.smoothed_bearing_deg : dev.bearing_deg;
  if (measured === null) { box.textContent = t("verify.no_bearing"); return; }

  const err = Math.abs(circularDiff(verifyAngle, measured));
  let verdict, color;
  if (err <= 10) { verdict = t("verify.good"); color = "var(--good)"; }
  else if (err <= 25) { verdict = t("verify.medium"); color = "var(--warn)"; }
  else { verdict = t("verify.bad"); color = "var(--bad)"; }

  let calibNote = "";
  if (dev.readings && Object.keys(dev.readings).length >= 3) {
    const addRes = await apiCall("calibration_add_round", { angle: verifyAngle, readings: dev.readings });
    if (addRes.ok) {
      const n = addRes.data.rounds_done;
      if (n >= 4) {
        const fin = await apiCall("calibration_finish");
        calibNote = fin.ok
          ? `<br><span style="color:var(--good)">${t("verify.calib_added")}</span> ${t("verify.calib_added_points", { gmax: fin.data.g_max.toFixed(1), gmin: fin.data.g_min.toFixed(1), n: fin.data.n.toFixed(2), count: n })}`
          : `<br><span class="muted">${t("verify.calib_added_fail", { n, err: fin.error })}</span>`;
        await refreshStatus();
      } else {
        calibNote = `<br><span class="muted">${t("verify.calib_added_pending", { n })}</span>`;
      }
    }
  }

  box.innerHTML = `
    ${t("verify.result", { real: verifyAngle, measured: measured.toFixed(1), err: err.toFixed(1) })}
    <span style="color:${color};font-weight:600;margin-left:8px">${verdict}</span>
    ${dev.locked ? "" : `<br><span class="muted">${t("verify.not_locked_note")}</span>`}
    ${calibNote}
  `;
});

// ---------------------------------------------------------------------
// Konum (ucgenleme)
// ---------------------------------------------------------------------

document.getElementById("btn-record-station").addEventListener("click", async () => {
  const x = parseFloat(document.getElementById("station-x").value) || 0;
  const y = parseFloat(document.getElementById("station-y").value) || 0;
  const duration = parseFloat(document.getElementById("station-duration").value) || 8;
  const btn = document.getElementById("btn-record-station");
  const log = document.getElementById("station-log");
  btn.disabled = true;
  const entry = document.createElement("p");
  entry.textContent = t("pos.recording", { x, y });
  log.appendChild(entry);

  const res = await apiCall("record_station", { x, y, duration });
  btn.disabled = false;
  entry.textContent = res.ok
    ? t("pos.recorded", { x, y, count: res.data.count })
    : t("pos.record_error", { x, y, err: res.error });
});

document.getElementById("btn-fix-targets").addEventListener("click", async () => {
  const box = document.getElementById("fix-results");
  box.textContent = t("pos.calculating");
  const res = await apiCall("fix_targets");
  if (!res.ok) { box.textContent = `${t("common.error_prefix")} ${res.error}`; return; }
  const results = res.data.results;
  if (!results.length) { box.textContent = t("pos.no_records"); return; }
  const table = document.createElement("table");
  table.innerHTML = `<thead><tr><th>${t("pos.th_mac")}</th><th>${t("pos.th_ssid")}</th><th>${t("pos.th_position")}</th><th>${t("pos.th_stations")}</th><th>${t("pos.th_note")}</th></tr></thead>`;
  const tbody = document.createElement("tbody");
  for (const r of results) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${r.mac}</td><td>${r.ssid}</td>` +
      (r.ok
        ? `<td>x=${r.x.toFixed(1)}, y=${r.y.toFixed(1)}</td><td>${r.stations}</td><td>${t("pos.residual_prefix")}=${r.residual.toFixed(1)}</td>`
        : `<td>-</td><td>-</td><td>${r.reason}</td>`);
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  box.innerHTML = "";
  box.appendChild(table);
});

// ---------------------------------------------------------------------
// Dil degisikligi: sayfa yuklendiginde bir kere olusturulan (statik
// HTML'in disindaki) dinamik metinleri (pusula butonlari, Tak-Cikar
// ilerleme tablosu, sistem durumu) yeniden olustur. Canli Takip
// sekmesindeki tablo/radar/istatistikler zaten 1sn'de bir yeniden
// cizildigi icin (pollDevices) ayrica ele alinmasina gerek yok.
// ---------------------------------------------------------------------

document.addEventListener("langchange", () => {
  buildPreciseCompassButtons();
  buildVerifyCompassButtons();
  buildSoloDeltaButtons();
  renderSoloProgress();
  renderSoloStep();
  refreshStatus();
});

// ---------------------------------------------------------------------
// HUD saati - salt kozmetik, "canli sistem" hissi verir
// ---------------------------------------------------------------------

function tickClock() {
  const el = document.getElementById("hud-clock");
  if (!el) return;
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  el.textContent = `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}
tickClock();
setInterval(tickClock, 1000);

// ---------------------------------------------------------------------
// Baslangic
// ---------------------------------------------------------------------

refreshStatus();
setInterval(refreshStatus, 5000);
