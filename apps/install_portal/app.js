const installBtn = document.getElementById("installBtn");
const copyBtn = document.getElementById("copyBtn");
const detectedOsEl = document.getElementById("detectedOs");
const commandBox = document.getElementById("commandBox");
const domainHintEl = document.getElementById("domainHint");

const BRAND_DOMAIN = "radriloniuma";
const OS_SUBDOMAIN = `os.${BRAND_DOMAIN}`;
const OS_BRAND_LABEL = "RADRILONIUMA OS"; // swap to "OS RADRILONIUMA" if needed

function detectOs() {
  const ua = (navigator.userAgent || "").toLowerCase();
  if (ua.includes("windows")) return "windows";
  if (ua.includes("android")) return "android";
  if (ua.includes("iphone") || ua.includes("ipad") || ua.includes("ios")) return "ios";
  if (ua.includes("mac os") || ua.includes("macintosh")) return "macos";
  if (ua.includes("linux")) return "linux";
  return "unknown";
}

function installCommandFor(os) {
  if (os === "linux") {
    return "cd /home/architit/work/LAM_Test_Agent && sudo scripts/install_oneclick.sh";
  }
  if (os === "windows") {
    return "powershell -ExecutionPolicy Bypass -File scripts/windows/install_oneclick.ps1";
  }
  if (os === "android" || os === "ios" || os === "macos") {
    return "Open Linux host portal and run: sudo scripts/install_oneclick.sh";
  }
  return "Use Linux installer: sudo scripts/install_oneclick.sh";
}

function updateUi() {
  const os = detectOs();
  detectedOsEl.textContent = `Detected OS: ${os}`;
  if (domainHintEl) {
    domainHintEl.textContent = `Main site: ${BRAND_DOMAIN} | OS subdomain: ${OS_SUBDOMAIN}`;
  }
  if (installBtn) {
    installBtn.textContent = `Install ${OS_BRAND_LABEL}`;
  }
  commandBox.textContent = installCommandFor(os);
}

async function copyCommand() {
  const cmd = commandBox.textContent || "";
  try {
    await navigator.clipboard.writeText(cmd);
    copyBtn.textContent = "Copied";
    setTimeout(() => { copyBtn.textContent = "Copy Command"; }, 1200);
  } catch {
    copyBtn.textContent = "Copy Failed";
    setTimeout(() => { copyBtn.textContent = "Copy Command"; }, 1200);
  }
}

installBtn.addEventListener("click", () => {
  updateUi();
  void copyCommand();
});
copyBtn.addEventListener("click", () => { void copyCommand(); });

updateUi();
