const viewer = document.getElementById("avatar-viewer");
const launchButton = document.getElementById("launch-ar");
const launchLabel = document.getElementById("launch-label");
const message = document.getElementById("ar-message");
const progressFill = document.getElementById("progress-fill");

let modelLoaded = false;
let modelFailed = false;

function setMessage(text, error = false) {
  message.textContent = text;
  message.classList.toggle("error", error);
}

function updateAvailability() {
  if (modelFailed) return;
  if (!modelLoaded) {
    launchButton.disabled = true;
    launchLabel.textContent = "ARを準備しています";
    return;
  }
  const available = viewer.canActivateAR === true;
  launchButton.disabled = !available;
  launchLabel.textContent = available ? "ARで置く" : "AR非対応の端末です";
  setMessage(
    available
      ? "カメラで床を映して、好きな位置をタップしてください。"
      : "スマホのSafariまたはChromeで開くと、ARで配置できます。"
  );
}

viewer.addEventListener("progress", (event) => {
  const progress = Math.round((event.detail?.totalProgress ?? 0) * 100);
  progressFill.style.width = progress + "%";
  if (!modelLoaded) setMessage("3Dモデルを読み込んでいます… " + progress + "%");
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
  launchButton.disabled = true;
  launchLabel.textContent = "読み込みに失敗しました";
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
      setMessage("カメラで床を映し、置きたい場所をタップしてください。");
      break;
    case "object-placed":
      setMessage("配置できました。近づいたり、回り込んだりしてみてください。");
      break;
    case "failed":
      setMessage("ARを起動できませんでした。SafariまたはChromeで開き直してください。", true);
      break;
    case "not-presenting":
      updateAvailability();
      break;
  }
});

launchButton.addEventListener("click", () => {
  if (!modelLoaded || !viewer.canActivateAR) return;
  setMessage("ARを開いています…");
  // Quick Look and Scene Viewer require this call directly inside the tap handler.
  viewer.activateAR().catch(() => {
    setMessage("ARを起動できませんでした。ブラウザーとカメラの設定を確認してください。", true);
  });
});

window.addEventListener("focus", () => {
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
