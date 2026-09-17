const { chromium } = require("playwright-core");

async function main() {
  const appUrl = process.env.APP_URL || "http://127.0.0.1:3000";
  const browser = await chromium.launch({
    executablePath: "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    headless: true
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];

  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });

  await page.goto(`${appUrl}/login`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "进入平台" }).click();
  await page.waitForURL("**/dashboard", { timeout: 15000 });

  await page.evaluate(() => {
    window.__persistentSidebar = document.querySelector("aside");
    window.__persistentHeader = document.querySelector("header");
  });

  await page.getByRole("link", { name: "地图风险监测" }).click();
  await page.waitForURL("**/map", { timeout: 15000 });
  const mapPersistence = await page.evaluate(() => ({
    sameSidebar: document.querySelector("aside") === window.__persistentSidebar,
    sameHeader: document.querySelector("header") === window.__persistentHeader
  }));

  await page.getByRole("link", { name: "AI 农技助手" }).click();
  await page.waitForURL("**/assistant", { timeout: 15000 });
  const before = await page.evaluate(() => {
    const list = document.querySelector("[data-message-scroll]");
    return {
      pageHeight: document.documentElement.scrollHeight,
      listHeight: list?.clientHeight || 0,
      overflowY: list ? getComputedStyle(list).overflowY : "missing"
    };
  });

  await page.getByRole("button", { name: "番茄早疫病怎么防治？" }).click();
  await page.getByText("正在检索农业知识库并融合当前风险数据，请稍候...").waitFor({ timeout: 5000 });
  const during = await page.evaluate(() => {
    const list = document.querySelector("[data-message-scroll]");
    return {
      pageHeight: document.documentElement.scrollHeight,
      listHeight: list?.clientHeight || 0,
      listScrollHeight: list?.scrollHeight || 0,
      userMessages: Array.from(document.querySelectorAll("[data-message-scroll] *")).filter((node) => node.textContent === "用户提问").length
    };
  });

  console.log(JSON.stringify({
    mapPersistence,
    assistant: {
      ...before,
      pageHeightDuringRequest: during.pageHeight,
      listHeightDuringRequest: during.listHeight,
      listScrollHeightDuringRequest: during.listScrollHeight,
      userMessages: during.userMessages,
      pageHeightStable: Math.abs(during.pageHeight - before.pageHeight) <= 2,
      listHeightStable: Math.abs(during.listHeight - before.listHeight) <= 2
    },
    errors
  }, null, 2));

  await browser.close();
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
