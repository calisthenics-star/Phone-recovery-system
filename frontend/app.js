const API = "http://10.0.2.15:8000";

const loginScreen = document.getElementById("loginScreen");
const dashboardScreen = document.getElementById("dashboardScreen");

const loginForm = document.getElementById("loginForm");
const loginMessage = document.getElementById("loginMessage");

const devicesGrid = document.getElementById("devicesGrid");
const dashboardMessage = document.getElementById("dashboardMessage");

const devicePanel = document.getElementById("devicePanel");
const historyPanel = document.getElementById("historyPanel");
const historyList = document.getElementById("historyList");

let selectedDeviceId = null;
let map = null;
let mapMarker = null;

function getToken() {
    return sessionStorage.getItem("session_token");
}

function authHeaders() {
    return {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${getToken()}`
    };
}

function showDashboard() {
    loginScreen.classList.add("hidden");
    dashboardScreen.classList.remove("hidden");
    loadDevices();
}

function showLogin() {
    dashboardScreen.classList.add("hidden");
    loginScreen.classList.remove("hidden");
}

loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    loginMessage.textContent = "";

    const recoveryId = document.getElementById("recoveryId").value.trim();
    const password = document.getElementById("password").value;

    try {
        const response = await fetch(`${API}/owners/login`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                recovery_id: recoveryId,
                password: password
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Login failed");
        }

        sessionStorage.setItem("session_token", data.session_token);

        loginForm.reset();
        showDashboard();

    } catch (error) {
        loginMessage.textContent = error.message;
    }
});

async function loadDevices() {
    dashboardMessage.textContent = "";
    devicesGrid.innerHTML = "Loading devices...";

    try {
        const response = await fetch(`${API}/owners/me/devices`, {
            headers: {
                "Authorization": `Bearer ${getToken()}`
            }
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Could not load devices");
        }

        renderDevices(data.devices);

    } catch (error) {
        devicesGrid.innerHTML = "";
        dashboardMessage.textContent = error.message;

        if (responseIsUnauthorized(error)) {
            logout();
        }
    }
}

function responseIsUnauthorized(error) {
    return error.message.toLowerCase().includes("session");
}

function renderDevices(devices) {
    devicesGrid.innerHTML = "";

    if (!devices.length) {
        devicesGrid.innerHTML = `
            <div class="device-card">
                <h3>No devices</h3>
                <p class="device-model">No registered phones found.</p>
            </div>
        `;
        return;
    }

    devices.forEach((device) => {
        const card = document.createElement("div");
        card.className = "device-card";

        card.innerHTML = `
            <h3>${escapeHtml(device.device_name)}</h3>
            <p class="device-model">${escapeHtml(device.device_model)}</p>
            <span class="status ${device.status}">
                ${escapeHtml(device.status)}
            </span>
        `;

        card.addEventListener("click", () => {
            loadDevice(device.device_id);
        });

        devicesGrid.appendChild(card);
    });
}

function updateMap(latitude, longitude) {
    if (!map) {
        map = L.map("map").setView([latitude, longitude], 15);

        L.tileLayer(
            "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            {
                maxZoom: 19,
                attribution: "&copy; OpenStreetMap contributors"
            }
        ).addTo(map);
    } else {
        map.setView([latitude, longitude], 15);
    }

    if (mapMarker) {
        mapMarker.setLatLng([latitude, longitude]);
    } else {
        mapMarker = L.marker([latitude, longitude])
            .addTo(map)
            .bindPopup("Last known location")
            .openPopup();
    }
}

async function loadDevice(deviceId) {
    selectedDeviceId = deviceId;
    historyPanel.classList.add("hidden");

    try {
        const response = await fetch(`${API}/devices/${deviceId}`, {
            headers: {
                "Authorization": `Bearer ${getToken()}`
            }
        });

        const device = await response.json();

        if (!response.ok) {
            throw new Error(device.detail || device.message || "Device not found");
        }

        devicePanel.classList.remove("hidden");

        document.getElementById("deviceId").textContent = device.device_id;
        document.getElementById("deviceName").textContent = device.device_name;
        document.getElementById("deviceModel").textContent = device.device_model;
        document.getElementById("lastSeen").textContent =
            formatDate(device.last_seen);
        document.getElementById("registeredAt").textContent =
            formatDate(device.registered_at);

        const status = document.getElementById("deviceStatus");
        status.textContent = device.status;
        status.className = `status ${device.status}`;
	const lostBtn = document.getElementById("lostBtn");
	if (device.status === "lost") {
    	  lostBtn.textContent = "Already Lost";
    	  lostBtn.disabled = true;
	} else {
    	  lostBtn.textContent = "Mark as Lost";
    	  lostBtn.disabled = false;
	}
        if (device.latest_location) {
            const location = device.latest_location;

            document.getElementById("locationText").textContent =
                `${location.latitude}, ${location.longitude}`;

            document.getElementById("accuracyText").textContent =
                `Accuracy: ${location.accuracy ?? "N/A"} m`;
            updateMap(location.latitude, location.longitude);

        } else {
            document.getElementById("locationText").textContent =
                "No location available";
            document.getElementById("accuracyText").textContent = "";
        }

        devicePanel.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

    } catch (error) {
        dashboardMessage.textContent = error.message;
    }
}

document.getElementById("historyBtn").addEventListener("click", async () => {
    if (!selectedDeviceId) return;

    historyPanel.classList.remove("hidden");
    historyList.innerHTML = "Loading history...";

    try {
        const response = await fetch(
            `${API}/devices/locations/history`,
            {
                method: "POST",
                headers: authHeaders(),
                body: JSON.stringify({
                    device_id: selectedDeviceId
                })
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Could not load history");
        }

        renderHistory(data.locations);

    } catch (error) {
        historyList.innerHTML = `<p class="message">${escapeHtml(error.message)}</p>`;
    }
});

function renderHistory(locations) {
    historyList.innerHTML = "";

    if (!locations.length) {
        historyList.innerHTML = "<p>No location history available.</p>";
        return;
    }

    locations.forEach((location) => {
        const item = document.createElement("div");
        item.className = "history-item";

        item.innerHTML = `
            <strong>
                ${location.latitude}, ${location.longitude}
            </strong>
            <span>
                Accuracy: ${location.accuracy ?? "N/A"} m
                · ${formatDate(location.reported_at)}
            </span>
        `;

        historyList.appendChild(item);
    });
}

document.getElementById("lostBtn").addEventListener("click", async () => {
    if (!selectedDeviceId) return;

    const confirmed = confirm(
        "Mark this device as lost?"
    );

    if (!confirmed) return;

    try {
        const response = await fetch(
            `${API}/devices/lost-mode`,
            {
                method: "POST",
                headers: authHeaders(),
                body: JSON.stringify({
                    device_id: selectedDeviceId
                })
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Could not enable Lost Mode");
        }

        await loadDevice(selectedDeviceId);
        await loadDevices();

	dashboardMessage.textContent = "Lost Mode enabled successfully.";
	dashboardMessage.style.color = "#16733a";

    } catch (error) {
        dashboardMessage.textContent = error.message;
    }
});

document.getElementById("refreshBtn").addEventListener(
    "click",
    loadDevices
);

document.getElementById("logoutBtn").addEventListener(
    "click",
    logout
);

function logout() {
    sessionStorage.removeItem("session_token");
    selectedDeviceId = null;

    devicePanel.classList.add("hidden");
    historyPanel.classList.add("hidden");
    devicesGrid.innerHTML = "";

    showLogin();
}

function formatDate(value) {
    if (!value) {
        return "Never";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return value;
    }

    return date.toLocaleString();
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

if (getToken()) {
    showDashboard();
}
