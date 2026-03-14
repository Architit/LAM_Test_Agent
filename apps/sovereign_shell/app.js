
const hexGrid = document.getElementById("hex-grid");
const logStream = document.getElementById("log-stream");
const pulseBtn = document.getElementById("pulse-btn");

async function updateClock() {
    const clock = document.getElementById("clock");
    const now = new Date();
    clock.innerText = now.toUTCString().split(" ")[4];
}

async function fetchOrgans() {
    try {
        const res = await fetch("/api/organs");
        const data = await res.json();
        hexGrid.innerHTML = "";
        data.forEach(organ => {
            const btn = document.createElement("button");
            btn.className = `organ-hex ${organ.status}`;
            btn.innerHTML = `<span>${organ.name.replace(/_/g, " ")}</span>`;
            btn.setAttribute("aria-label", `Organ: ${organ.name}, Status: ${organ.status}`);
            hexGrid.appendChild(btn);
        });
    } catch (e) { console.error("API error", e); }
}

async function fetchLogs() {
    try {
        const res = await fetch("/api/logs");
        const data = await res.json();
        logStream.innerHTML = data.logs.map(line => `<div>> ${line}</div>`).join("");
        logStream.scrollTop = logStream.scrollHeight;
    } catch (e) { console.error("Log error", e); }
}

pulseBtn.addEventListener("click", async () => {
    await fetch("/api/trigger", { method: "POST" });
    logStream.innerHTML += "<div style=\"color: white\">*** GLOBAL PULSE INITIATED ***</div>";
});

setInterval(updateClock, 1000);
setInterval(fetchOrgans, 5000);
setInterval(fetchLogs, 3000);

fetchOrgans();
fetchLogs();
updateClock();
