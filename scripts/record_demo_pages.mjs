import fs from "node:fs/promises";
import path from "node:path";
import playwright from "../frontend/node_modules/playwright-core/index.js";

const { chromium } = playwright;

const root = path.resolve(import.meta.dirname, "..");
const outputDir = path.join(root, "submission_artifacts", "video_real", "captures");
const storagePath = path.join(outputDir, "storage.json");
const browserPath = "C:/Program Files/Google/Chrome/Application/chrome.exe";

await fs.mkdir(outputDir, { recursive: true });

const browser = await chromium.launch({
  headless: true,
  executablePath: browserPath,
  args: ["--disable-dev-shm-usage", "--disable-background-timer-throttling"]
});

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function settle(page, ms = 1800) {
  await page.waitForLoadState("domcontentloaded").catch(() => {});
  await page.waitForLoadState("networkidle", { timeout: 8000 }).catch(() => {});
  await sleep(ms);
}

async function safe(action) {
  try {
    await action();
  } catch (error) {
    console.warn("capture step skipped:", error.message);
  }
}

async function finishAt(start, seconds) {
  const remaining = seconds * 1000 - (Date.now() - start);
  if (remaining > 0) await sleep(remaining);
}

async function record(name, seconds, action, options = {}) {
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
    colorScheme: "dark",
    reducedMotion: "no-preference",
    storageState: options.storage ? storagePath : undefined,
    recordVideo: { dir: outputDir, size: { width: 1920, height: 1080 } }
  });
  const page = await context.newPage();
  const video = page.video();
  const start = Date.now();
  await action(page);
  await finishAt(start, seconds);
  if (options.saveStorage) await context.storageState({ path: storagePath });
  await context.close();
  await video.saveAs(path.join(outputDir, `${name}.webm`));
  console.log(`${name}: ${((Date.now() - start) / 1000).toFixed(1)}s`);
}

await record("01_problem", 25, async (page) => {
  await page.goto("http://localhost:3000/login");
  await settle(page, 3500);
  await safe(async () => {
    await page.getByRole("button", { name: "县域管理员" }).hover();
    await sleep(1200);
    await page.getByRole("button", { name: /进入平台/ }).click();
    await page.waitForURL(/dashboard/, { timeout: 12000 });
    await settle(page, 4500);
  });
}, { saveStorage: true });

await record("02_data", 55, async (page) => {
  await page.goto("http://localhost:3000/data");
  await settle(page, 4500);
  await page.mouse.move(1410, 430, { steps: 18 });
  await sleep(1800);
  await page.mouse.wheel(0, 620);
  await sleep(4200);
  await safe(async () => {
    const select = page.locator("select").first();
    await select.selectOption("sensor_records");
  });
  await sleep(3200);
  await page.mouse.wheel(0, -620);
  await sleep(3500);
  await page.goto("http://localhost:3000/dashboard");
  await settle(page, 4500);
  await page.mouse.wheel(0, 560);
  await sleep(3500);
}, { storage: true });

await record("03_spark", 60, async (page) => {
  await page.goto("http://localhost:3000/data");
  await settle(page, 4200);
  await page.mouse.wheel(0, 690);
  await sleep(4200);
  await page.goto("http://localhost:8000/docs");
  await settle(page, 5000);
  await safe(async () => {
    const section = page.locator(".opblock-tag").filter({ hasText: "dashboard" }).first();
    if (await section.count()) await section.click();
  });
  await sleep(3500);
  await page.mouse.wheel(0, 650);
  await sleep(3500);
  await page.goto("http://localhost:3000/predictions");
  await settle(page, 5500);
  await page.mouse.wheel(0, 520);
  await sleep(4200);
}, { storage: true });

await record("04_risk", 50, async (page) => {
  await page.goto("http://localhost:3000/predictions");
  await settle(page, 5200);
  await safe(async () => {
    const select = page.locator("select").first();
    const options = await select.locator("option").count();
    if (options > 4) await select.selectOption({ index: 4 });
  });
  await sleep(5200);
  await page.mouse.wheel(0, 520);
  await sleep(4200);
  await page.goto("http://localhost:3000/map");
  await settle(page, 5200);
  await safe(async () => {
    const selects = page.locator("select");
    await selects.nth(2).selectOption("高");
    await sleep(3500);
    const polygon = page.locator(".leaflet-interactive").first();
    if (await polygon.count()) await polygon.click({ force: true });
  });
  await sleep(4200);
}, { storage: true });

await record("05_system", 60, async (page) => {
  await page.goto("http://localhost:3000/dashboard");
  await settle(page, 3000);
  await page.goto("http://localhost:3000/map");
  await settle(page, 3000);
  await safe(async () => {
    const polygon = page.locator(".leaflet-interactive").first();
    if (await polygon.count()) await polygon.click({ force: true });
  });
  await sleep(2500);
  await page.goto("http://localhost:3000/disease");
  await settle(page, 2500);
  await safe(async () => {
    await page.locator('input[type="file"]').setInputFiles(path.join(root, "data", "generated", "plantdoc_yolo", "images", "val", "val_02330.jpg"));
    await sleep(1000);
    await page.getByRole("button", { name: /开始识别/ }).click();
    await page.getByText(/置信度|识别结果/).last().waitFor({ timeout: 15000 });
  });
  await sleep(2800);
  await page.goto("http://localhost:3000/alerts");
  await settle(page, 2500);
  await safe(async () => {
    const button = page.getByRole("button", { name: "生成巡检" }).first();
    if (await button.count()) await button.click();
  });
  await sleep(2200);
  await page.goto("http://localhost:3000/assistant");
  await settle(page, 2500);
  await safe(async () => {
    await page.getByRole("button", { name: "哪些地块应该优先巡检？" }).click();
    await page.getByText("农智云瞰助手").last().waitFor({ timeout: 13000 });
  });
  await sleep(2500);
  await page.goto("http://localhost:3000/reports");
  await settle(page, 2200);
  await safe(async () => {
    await page.getByRole("button", { name: /生成日报/ }).click();
    await page.getByText(/报告ID/).waitFor({ timeout: 10000 });
  });
  await sleep(2200);
}, { storage: true });

await record("06_engineering", 25, async (page) => {
  await page.goto("http://localhost:3000/inspections");
  await settle(page, 4000);
  await page.mouse.wheel(0, 500);
  await sleep(3500);
  await page.goto("http://localhost:8000/docs");
  await settle(page, 4000);
  await page.mouse.wheel(0, 430);
  await sleep(2500);
}, { storage: true });

await record("07_close", 15, async (page) => {
  await page.goto("http://localhost:3000/dashboard");
  await settle(page, 5000);
  await page.mouse.move(1520, 410, { steps: 20 });
  await sleep(2000);
}, { storage: true });

await browser.close();
