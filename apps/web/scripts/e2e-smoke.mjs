import { chromium } from "playwright";

const SHOTS = "/tmp/claude-0/-home-user-citydata/cc8a09c1-c497-5cdc-9bad-e5b667541405/scratchpad/shots";
const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium" });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, permissions: ["clipboard-read", "clipboard-write"] });
const page = await ctx.newPage();
const logs = [];
page.on("console", (m) => m.type() === "error" && logs.push(m.text()));

// 1. main app
await page.goto("http://localhost:3100/chicago", { waitUntil: "networkidle" });
await page.waitForTimeout(2500);
await page.screenshot({ path: `${SHOTS}/1-main.png` });

// grab top-5 ranking
const top = async () =>
  page.$$eval("ol > li", (els) => els.slice(0, 5).map((el) => el.querySelector("span.flex-1")?.textContent));
const before = await top();
console.log("top5 (balanced):", before);

// 2. crank walkability to 5, zero safety-ish sliders -> expect re-rank
await page.locator("#w-walkability").fill("5");
// zero every other ENABLED slider so walkability dominates
for (const id of await page.$$eval("input[type=range]:not([disabled])", (els) => els.map((e) => e.id))) {
  if (id && id !== "w-walkability" && id.startsWith("w-")) await page.locator(`#${id}`).fill("0");
}
await page.waitForTimeout(400);
const after = await top();
console.log("top5 (walkability-max):", after);
await page.screenshot({ path: `${SHOTS}/2-walkability.png` });
if (JSON.stringify(before) === JSON.stringify(after)) console.log("WARN: ranking did not change");

// 3. open detail for #1
await page.locator("ol > li").first().click();
await page.waitForTimeout(500);
await page.screenshot({ path: `${SHOTS}/3-detail.png` });
const detailText = await page.textContent("aside:last-of-type");
console.log("detail mentions contribution:", detailText.includes("pts"));

// expand first criterion row
await page.locator("aside:last-of-type button").nth(1).click().catch(() => {});
await page.waitForTimeout(300);
await page.screenshot({ path: `${SHOTS}/4-detail-expanded.png` });

// 4. add a pin via coordinates (Loop) and weight it
await page.locator('aside input[placeholder="Label (e.g. Office)"]').fill("Office");
await page.locator('aside input[placeholder="Address"]').fill("41.8837, -87.6289");
await page.getByRole("button", { name: "Pin" }).click();
await page.waitForTimeout(600);
await page.locator("#w-places").fill("5");
await page.waitForTimeout(400);
// close detail to see list
await page.locator('aside [aria-label="Close details"]').click().catch(() => {});
await page.waitForTimeout(400);
const withPin = await top();
console.log("top5 (office pin, weight 5):", withPin);
await page.screenshot({ path: `${SHOTS}/5-pin.png` });

// 5. share URL round-trip
await page.getByRole("button", { name: /Share|Copied/ }).click();
const url = await page.evaluate(() => navigator.clipboard.readText().catch(() => ""));
console.log("share url length:", url.length, url.slice(0, 60));

console.log("console errors:", logs.length ? logs.slice(0, 5) : "none");
await browser.close();
