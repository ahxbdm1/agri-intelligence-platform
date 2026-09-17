const { chromium } = require("playwright-core");

async function main() {
  const appUrl = process.env.APP_URL || "http://127.0.0.1:3000";
  const browser = await chromium.launch({
    executablePath: "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    headless: true
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });

  await page.goto(`${appUrl}/login`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "进入平台" }).click();
  await page.waitForURL("**/dashboard", { timeout: 15000 });
  await page.goto(`${appUrl}/assistant`, { waitUntil: "networkidle" });
  await page.getByText("远程在线", { exact: true }).waitFor({ timeout: 15000 });

  const [response] = await Promise.all([
    page.waitForResponse((item) => item.url().includes("/api/assistant/chat"), { timeout: 150000 }),
    page.getByRole("button", { name: "发送" }).click()
  ]);
  const payload = await response.json();
  await page.screenshot({ path: "../artifacts/desktop-assistant-ragflow.png", fullPage: false });
  console.log(JSON.stringify({
    httpStatus: response.status(),
    mode: payload.mode,
    provider: payload.provider,
    citations: payload.citations?.length || 0,
    warning: payload.warning || null,
    errors
  }, null, 2));
  await browser.close();
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
