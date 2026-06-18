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
    const uptime = status?.uptime || "-";
    const ram = status?.ram || "-";
    const storage = status?.storage || "-";
    const camera = status?.camera || "-";
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
          <div><dt>IP</dt><dd>${escapeHtml(device.ip || "-")}</dd></div>
          <div><dt>Uptime</dt><dd>${escapeHtml(uptime)}</dd></div>
          <div><dt>RAM</dt><dd>${escapeHtml(ram)}</dd></div>
          <div><dt>Storage</dt><dd>${escapeHtml(storage)}</dd></div>
          <div><dt>Camera</dt><dd>${escapeHtml(camera)}</dd></div>
        </dl>
        ${error}
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

async function refreshStatus() {
  const button = $("#refresh-status");
  button.disabled = true;
  button.textContent = "확인 중";
  try {
    // Status checks are manual by design. The document says periodic refresh is a
    // future option, so there is no timer here.
    const payload = await request("/api/status", { method: "POST", body: "{}" });
    state.statuses = new Map(payload.statuses.map((status) => [status.id, status]));
    render();
    toast("상태 확인을 마쳤습니다.");
  } finally {
    button.disabled = false;
    button.textContent = "상태 확인";
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

$("#refresh-status").addEventListener("click", () => refreshStatus().catch((error) => toast(error.message)));
loadDevices().catch((error) => toast(error.message));
