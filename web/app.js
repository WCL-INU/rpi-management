const state = {
  devices: [],
  statuses: new Map(),
};

const $ = (selector) => document.querySelector(selector);

function toast(message) {
  const node = $("#toast");
  node.textContent = message;
  node.classList.add("visible");
  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => node.classList.remove("visible"), 2400);
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { "content-type": "application/json" },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "요청에 실패했습니다.");
  return payload;
}

// The status label stays separate from rendering so online/offline/unknown styling
// remains consistent across summary counts and individual cards.
function statusLabel(status) {
  if (!status) return ["미확인", "unknown"];
  return status.online ? ["온라인", "online"] : ["오프라인", "offline"];
}

function formatCheckedAt(statuses) {
  if (!statuses.length) return "-";
  const latest = Math.max(...statuses.map((status) => status.checkedAt * 1000));
  return new Date(latest).toLocaleTimeString();
}

function extractIPv4(value) {
  const match = String(value || "").match(/\b(?:\d{1,3}\.){3}\d{1,3}\b/);
  return match ? match[0] : "";
}

function streamUrlFor(device, status) {
  // Prefer the runtime IP from Network after a status check. Before that exists,
  // use the configured host so operators can still open the stream page directly.
  const target = extractIPv4(status?.network) || device.host || device.id || "";
  return target ? `http://${target}:8000` : "";
}

function renderSummary() {
  const statuses = state.devices
    .map((device) => state.statuses.get(device.id))
    .filter(Boolean);
  const online = statuses.filter((status) => status.online).length;
  const offline = statuses.length ? statuses.length - online : null;

  // Summary numbers answer the operator's first question: how many are alive now?
  $("#device-count").textContent = String(state.devices.length);
  $("#online-count").textContent = statuses.length ? String(online) : "-";
  $("#offline-count").textContent = offline === null ? "-" : String(offline);
  $("#checked-at").textContent = formatCheckedAt(statuses);
}

function renderDeviceCards() {
  const cards = state.devices.map((device) => {
    const status = state.statuses.get(device.id);
    const [label, className] = statusLabel(status);

    // Keep each card focused on runtime health. Configuration fields such as
    // programs or env keys are intentionally not rendered on this page.
    const checkedAt = status?.checkedAt ? new Date(status.checkedAt * 1000).toLocaleTimeString() : "-";
    const uptime = status?.uptime || "-";
    const ram = status?.ram || "-";
    const storage = status?.storage || "-";
    const cpu = status?.cpu || "-";
    const network = status?.network || "-";
    const cpuTemp = status?.cpuTemp || "-";
    const camera = status?.camera || "-";
    const streamUrl = streamUrlFor(device, status);
    const streamLink = streamUrl
      ? `<a class="stream-link" href="${escapeAttr(streamUrl)}" target="_blank" rel="noreferrer">스트리밍 열기</a>`
      : `<span class="stream-link disabled">스트리밍 주소 없음</span>`;
    const error = status && !status.online ? `<div class="error">${escapeHtml(status.error || "SSH connection failed.")}</div>` : "";

    return `
      <article class="device-card ${className}">
        <div class="card-head">
          <div>
            <strong>${escapeHtml(device.id || "-")}</strong>
            <span>${escapeHtml(device.host || "-")}</span>
          </div>
          <span class="status ${className}">${label}</span>
        </div>
        <dl class="status-details">
          <div><dt>Checked</dt><dd>${escapeHtml(checkedAt)}</dd></div>
          <div><dt>Uptime</dt><dd>${escapeHtml(uptime)}</dd></div>
          <div><dt>RAM</dt><dd>${escapeHtml(ram)}</dd></div>
          <div><dt>Storage</dt><dd>${escapeHtml(storage)}</dd></div>
          <div><dt>CPU</dt><dd>${escapeHtml(cpu)}</dd></div>
          <div><dt>Network</dt><dd>${escapeHtml(network)}</dd></div>
          <div><dt>CPU Temp</dt><dd>${escapeHtml(cpuTemp)}</dd></div>
          <div><dt>Camera</dt><dd>${escapeHtml(camera)}</dd></div>
        </dl>
        ${error}
        <div class="card-actions">
          ${streamLink}
          <button class="refresh-device" data-device-id="${escapeAttr(device.id || "")}">이 장비 새로고침</button>
        </div>
      </article>
    `;
  }).join("");

  $("#device-cards").innerHTML = cards || `<p class="empty">등록된 장비가 없습니다.</p>`;
}

function render() {
  renderSummary();
  renderDeviceCards();
}

async function loadDevices() {
  const payload = await request("/api/devices");
  state.devices = payload.devices;
  render();
}

function mergeStatuses(statuses) {
  for (const status of statuses) {
    state.statuses.set(status.id, status);
  }
}

async function refreshAll(button) {
  button.disabled = true;
  const originalText = button.textContent;
  button.textContent = "확인 중";
  try {
    // The all-device path is still manual. It is useful for an initial sweep,
    // while per-card refresh stays available for focused follow-up checks.
    const payload = await request("/api/status", { method: "POST", body: "{}" });
    mergeStatuses(payload.statuses);
    render();
    toast("전체 상태를 갱신했습니다.");
  } finally {
    button.disabled = false;
    button.textContent = originalText;
  }
}

async function refreshDevice(deviceId, button) {
  button.disabled = true;
  const originalText = button.textContent;
  button.textContent = "확인 중";
  try {
    // Refresh only the requested device. Other cards keep their last known status,
    // which makes partial checks fast and avoids hiding useful stale information.
    const payload = await request("/api/status", {
      method: "POST",
      body: JSON.stringify({ deviceId }),
    });
    mergeStatuses(payload.statuses);
    render();
    toast(`${deviceId} 상태를 갱신했습니다.`);
  } finally {
    button.disabled = false;
    button.textContent = originalText;
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttr(value) {
  return escapeHtml(value);
}

document.addEventListener("click", (event) => {
  const deviceButton = event.target.closest(".refresh-device");
  if (deviceButton) {
    refreshDevice(deviceButton.dataset.deviceId, deviceButton).catch((error) => toast(error.message));
    return;
  }

  const allButton = event.target.closest("#refresh-all");
  if (allButton) {
    refreshAll(allButton).catch((error) => toast(error.message));
  }
});

loadDevices().catch((error) => toast(error.message));
