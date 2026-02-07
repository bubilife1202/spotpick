const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();
  await page.goto("http://localhost:3030");
  console.log("Browser opened at http://localhost:3030");
  // Keep alive
  await new Promise(() => {});
})();
