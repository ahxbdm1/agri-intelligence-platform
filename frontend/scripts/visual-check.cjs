const { chromium } = require("playwright-core");

async function main() {
  const appUrl = process.env.APP_URL || "http://127.0.0.1:3000";
  const browser = await chromium.launch({
    executablePath: "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    headless: true
  });
  const results = [];

  async function inspect(name, viewport) {
    const context = await browser.newContext({ viewport, deviceScaleFactor: 1 });
    const page = await context.newPage();
    const errors = [];
    page.on("console", (message) => {
      if (message.type() === "error") errors.push(`console: ${message.text()}`);
    });
    page.on("pageerror", (error) => errors.push(`page: ${error.message}`));
    page.on("response", (response) => {
      if (response.status() >= 400) errors.push(`http ${response.status()}: ${response.url()}`);
    });

    await page.goto(`${appUrl}/login`, { waitUntil: "networkidle" });
    await page.screenshot({ path: `../artifacts/${name}-login.png`, fullPage: true });
    await page.getByRole("button", { name: "进入平台" }).click();
    await page.waitForTimeout(2500);
    if (!page.url().includes("/dashboard")) {
      const loginText = await page.locator("body").innerText();
      await page.screenshot({ path: `../artifacts/${name}-login-failed.png`, fullPage: true });
      throw new Error(`登录未跳转，当前地址 ${page.url()}，浏览器错误：${errors.join(" | ")}，页面信息：${loginText.slice(-240)}`);
    }
    await page.waitForLoadState("networkidle");
    const dashboard = await page.evaluate(() => ({
      innerWidth,
      scrollWidth: document.documentElement.scrollWidth,
      bodyWidth: document.body.getBoundingClientRect().width,
      mainTop: document.querySelector("main")?.getBoundingClientRect().top,
      cards: document.querySelectorAll(".glass-card").length
    }));
    await page.screenshot({ path: `../artifacts/${name}-dashboard.png`, fullPage: false });

    const routes = ["map", "disease", "predictions", "alerts", "inspections", "assistant", "data", "reports"];
    const pages = [];
    for (const route of routes) {
      await page.goto(`${appUrl}/${route}`, { waitUntil: "networkidle" });
      await page.waitForTimeout(route === "map" ? 900 : 180);
      const metrics = await page.evaluate(() => ({
        innerWidth,
        scrollWidth: document.documentElement.scrollWidth,
        runtimeError: document.body.innerText.includes("Runtime Error"),
        cards: document.querySelectorAll(".glass-card").length,
        maps: document.querySelectorAll(".leaflet-container").length
      }));
      pages.push({ route, ...metrics });
      if (["map", "disease", "assistant", "reports"].includes(route)) {
        await page.screenshot({ path: `../artifacts/${name}-${route}.png`, fullPage: false });
      }
    }

    const interactions = {};
    if (name === "desktop") {
      await page.goto(`${appUrl}/disease`, { waitUntil: "networkidle" });
      await page.getByRole("button", { name: "开始识别" }).click();
      await page.getByText("人工复核", { exact: true }).waitFor({ timeout: 15000 });
      interactions.disease = "ok";

      await page.goto(`${appUrl}/assistant`, { waitUntil: "networkidle" });
      await page.getByRole("button", { name: "发送" }).click();
      await page.getByText("农智云瞰助手", { exact: true }).waitFor({ timeout: 120000 });
      interactions.assistant = "ok";

      await page.goto(`${appUrl}/reports`, { waitUntil: "networkidle" });
      await page.getByRole("button", { name: "生成日报" }).click();
      await page.getByText(/报告ID：/).waitFor({ timeout: 15000 });
      interactions.reports = "ok";
    }

    results.push({ name, dashboard, pages, interactions, errors: [...new Set(errors)] });
    await context.close();
  }

  await inspect("desktop", { width: 1440, height: 1000 });
  await inspect("mobile", { width: 390, height: 844 });
  console.log(JSON.stringify(results, null, 2));
  await browser.close();
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
