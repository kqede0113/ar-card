const viewer = document.getElementById("avatar-viewer");
const launchButton = document.getElementById("launch-ar");
const launchLabel = document.getElementById("launch-label");
const message = document.getElementById("ar-message");
const progressFill = document.getElementById("progress-fill");
const androidHelp = document.getElementById("android-help");
const openInBrowser = document.getElementById("open-ar-page");
const isAndroid = /Android/i.test(navigator.userAgent);
const framedAndroid = isAndroid && window.self !== window.top;
if (isAndroid) {
  // Scene Viewer requires the baseline GLB; use a new URL to bypass previously
  // cached Draco-compressed model data. iPhone's Quick Look USDZ stays unchanged.
  viewer.setAttribute("src", "./avatar-ar.glb?v=android-compatible-20261029");
}
let androidLaunch = "idle";
let androidLaunchTimer;

// A plain HTTPS link opens outside Hark's sandbox. Never fall back to navigating
// the iframe: that traps the AR page and breaks its return link.
if (framedAndroid) {
  launchButton.hidden = true;
  openInBrowser.hidden = false;
  document.querySelectorAll(".site-header a").forEach(link => {
    link.target = "_blank";
    link.rel = "noopener noreferrer";
  });
}

function showAndroidHelp(text) {
  clearTimeout(androidLaunchTimer);
  androidLaunch = "failed";
  androidHelp.hidden = false;
  launchButton.disabled = !modelLoaded || !viewer.canActivateAR;
  launchLabel.textContent = viewer.canActivateAR ? "もう一度ARで開く" : "この端末では3Dで楽しめます";
  setMessage(text, true);
}

function androidVisibilityChanged() {
  if (!isAndroid || framedAndroid) return;
  if (document.hidden && androidLaunch === "pending") {
    clearTimeout(androidLaunchTimer);
    androidLaunch = "away";
  } else if (!document.hidden && androidLaunch === "away") {
    androidLaunch = "idle";
    updateAvailability();
    setMessage("ARから戻りました。カメラが開かなかった場合は、下の「ARが開かないとき」を確認してください。");
    androidHelp.hidden = false;
  }
}
document.addEventListener("visibilitychange", androidVisibilityChanged);
window.addEventListener("pagehide", () => {
  if (isAndroid && androidLaunch === "pending") {
    clearTimeout(androidLaunchTimer);
    androidLaunch = "away";
  }
});
window.addEventListener("pageshow", androidVisibilityChanged);

let modelLoaded = false;
let modelFailed = false;

function setMessage(text, error = false) {
  message.textContent = text;
  message.classList.toggle("error", error);
}

function updateAvailability() {
  if (framedAndroid) {
    setMessage("ARは別の画面で開きます。上のボタンを押して続けてください。");
    return;
  }
  if (isAndroid && androidLaunch !== "idle") return;
  if (modelFailed) return;
  if (!modelLoaded) {
    launchButton.disabled = true;
    launchLabel.textContent = "ARを準備しています";
    return;
  }
  const available = viewer.canActivateAR === true;
  launchButton.disabled = !available;
  launchLabel.textContent = available ? "ARで置く" : "AR非対応の端末です";
  if (isAndroid && !available) {
    // Capability detection can finish after the model load event. Keep the
    // scheduled availability checks active instead of recording a launch failure.
    androidHelp.hidden = false;
    launchLabel.textContent = "この端末では3Dで楽しめます";
    setMessage("この端末・ブラウザーではARを利用できません。3Dモデルはこのまま回して楽しめます。");
    return;
  }
  setMessage(
    available
      ? "カメラで床を映して、好きな位置をタップしてください。"
      : "スマホのSafariまたはChromeで開くと、ARで配置できます。"
  );
}

viewer.addEventListener("progress", (event) => {
  const progress = Math.round((event.detail?.totalProgress ?? 0) * 100);
  progressFill.style.width = progress + "%";
  if (!modelLoaded && !framedAndroid) setMessage("3Dモデルを読み込んでいます… " + progress + "%");
});

viewer.addEventListener("load", () => {
  modelLoaded = true;
  progressFill.style.width = "100%";
  updateAvailability();
  setTimeout(updateAvailability, 800);
  setTimeout(updateAvailability, 2200);
});

viewer.addEventListener("error", (event) => {
  modelFailed = true;
  if (isAndroid) clearTimeout(androidLaunchTimer);
  launchButton.disabled = true;
  launchLabel.textContent = "読み込みに失敗しました";
  if (framedAndroid) { updateAvailability(); return; }
  setMessage(
    event.detail?.type === "webglcontextlost"
      ? "表示に必要なメモリが足りません。ページを再読み込みしてください。"
      : "モデルを読み込めませんでした。通信を確認してページを再読み込みしてください。",
    true
  );
});

viewer.addEventListener("ar-status", (event) => {
  switch (event.detail?.status) {
    case "session-started":
      if (isAndroid) { clearTimeout(androidLaunchTimer); androidLaunch = "presenting"; androidHelp.hidden = true; }
      setMessage("カメラで床を映し、置きたい場所をタップしてください。");
      break;
    case "object-placed":
      setMessage("配置できました。近づいたり、回り込んだりしてみてください。");
      break;
    case "failed":
      if (isAndroid) {
        showAndroidHelp("ARを起動できませんでした。下の案内を確認して、もう一度お試しください。");
        break;
      }
      setMessage("ARを起動できませんでした。SafariまたはChromeで開き直してください。", true);
      break;
    case "not-presenting":
      if (isAndroid && androidLaunch === "presenting") androidLaunch = "idle";
      updateAvailability();
      break;
  }
});

launchButton.addEventListener("click", () => {
  if (!modelLoaded || !viewer.canActivateAR) return;
  if (framedAndroid) return;
  if (isAndroid) {
    clearTimeout(androidLaunchTimer);
    androidLaunch = "pending";
    androidHelp.hidden = true;
    launchButton.disabled = true;
    launchLabel.textContent = "ARを開いています";
    androidLaunchTimer = setTimeout(() => {
      if (androidLaunch === "pending" && !document.hidden) {
        showAndroidHelp("AR画面が開いていない場合は、下の案内を確認してください。この画面で3Dを見ることもできます。");
      }
    }, 12000);
  }
  setMessage("ARを開いています…");
  // Quick Look and Scene Viewer require this call directly inside the tap handler.
  viewer.activateAR().catch(() => {
    if (isAndroid) {
      showAndroidHelp("ARを起動できませんでした。下の案内を確認して、もう一度お試しください。");
      return;
    }
    setMessage("ARを起動できませんでした。ブラウザーとカメラの設定を確認してください。", true);
  });
});

window.addEventListener("focus", () => {
  if (isAndroid) androidVisibilityChanged();
  if (modelLoaded && !modelFailed) updateAvailability();
});

setTimeout(() => {
  if (!customElements.get("model-viewer")) {
    modelFailed = true;
    launchButton.disabled = true;
    launchLabel.textContent = "読み込みに失敗しました";
    setMessage("ARの表示機能を読み込めませんでした。通信を確認して再読み込みしてください。", true);
  }
}, 15000);

if (framedAndroid) updateAvailability();
