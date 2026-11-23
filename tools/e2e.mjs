import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { mkdirSync, readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const { chromium } = createRequire(process.env.PLAYWRIGHT_FROM || import.meta.url)("playwright");
const shots = process.argv[2] || null;
if (shots) mkdirSync(shots, { recursive: true });

const PORT = 8793;
const REMOTE = process.env.BASE_URL || null;
const BASE = REMOTE || `http://127.0.0.1:${PORT}`;
const VIEWPORTS = [[390, 844], [768, 1024], [1024, 768], [1366, 768], [1920, 1080]];
const failures = [];
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const key = new Map();
for (const file of readdirSync(join(root, "content")).filter((name) => name.startsWith("part_"))) {
  for (const item of JSON.parse(readFileSync(join(root, "content", file), "utf8")).items) key.set(item.prompt, item.answer);
}

function startServer() {
  if (REMOTE) return { kill() {} };
  return spawn(process.env.PYTHON || "python3", ["-m", "meje", "serve", "--no-browser", "--port", String(PORT)], { cwd: root, stdio: "ignore" });
}
async function waitForServer() {
  for (let i = 0; i < 80; i += 1) {
    try { if ((await fetch(`${BASE}/health`)).ok) return; } catch {}
    await sleep(100);
  }
  throw new Error("the app did not start");
}

async function audit(page, phone) {
  return page.evaluate((isPhone) => {
    const problems = [];
    const root = document.documentElement;
    if (root.scrollWidth > root.clientWidth + 1) problems.push(`page scrolls sideways by ${root.scrollWidth - root.clientWidth}px`);
    const scrollers = [".mapscroll", ".tablewrap", ".formula", "pre"];
    const visible = (node) => { const r = node.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
    for (const node of document.querySelectorAll("main *, header *, nav *")) {
      if (!visible(node) || node.closest(scrollers.join(","))) continue;
      const style = getComputedStyle(node);
      if (node.scrollWidth > node.clientWidth + 1 && style.overflowX !== "visible" && style.textOverflow !== "ellipsis" && node.clientWidth > 0) {
        problems.push(`clipped content in <${node.tagName.toLowerCase()} class="${node.getAttribute("class") || ""}">`);
      }
      const rect = node.getBoundingClientRect();
      if (rect.right > root.clientWidth + 1 && !node.closest("svg")) {
        problems.push(`<${node.tagName.toLowerCase()} class="${node.getAttribute("class") || ""}"> sticks out on the right by ${Math.round(rect.right - root.clientWidth)}px`);
      }
    }
    if (isPhone) {
      for (const node of document.querySelectorAll(".btn, .option[role=radio], .destination, #dock a, .seg button")) {
        if (visible(node) && node.getBoundingClientRect().height < 40) problems.push(`touch target under 40px: ${node.textContent.trim().slice(0, 30)}`);
      }
    }
    const families = ["Medeo Sans", "Medeo Mono", ...(document.querySelector("main h1, main h2") ? ["Source Serif 4"] : [])];
    for (const family of families) {
      if (!document.fonts.check(`16px "${family}"`)) problems.push(`font not loaded: ${family}`);
    }
    return [...new Set(problems)].slice(0, 8);
  }, phone);
}

async function dockClear(page) {
  return page.evaluate(async () => {
    window.scrollTo(0, document.documentElement.scrollHeight);
    await new Promise((resolve) => setTimeout(resolve, 60));
    const dock = document.getElementById("dock");
    if (dock.hidden) return [];
    const d = dock.getBoundingClientRect();
    const covered = [...document.querySelectorAll("main .btn, main .textlink")].filter((node) => {
      const r = node.getBoundingClientRect();
      return r.height > 0 && r.bottom > d.top + 1 && r.top < d.bottom - 1 && r.right > d.left + 1 && r.left < d.right - 1;
    });
    window.scrollTo(0, 0);
    return covered.map((node) => `dock covers "${node.textContent.trim()}" at the end of the page`);
  });
}

async function check(page, name, phone) {
  await sleep(1000);
  for (const problem of [...await audit(page, phone), ...await dockClear(page)]) failures.push(`${name}: ${problem}`);
  if (shots) await page.screenshot({ path: join(shots, `${name}.png`), fullPage: phone });
}

async function answer(page, { correct, sure }) {
  await page.waitForSelector(".option[role=radio]");
  const prompt = await page.locator(".prompt").innerText();
  const right = key.get(prompt);
  if (right === undefined) throw new Error(`no answer key for: ${prompt}`);
  await page.click(`.option >> nth=${correct ? right : (right + 1) % 4}`);
  await page.click(sure ? "#sure" : "#unsure");
  await page.waitForSelector("#continue");
}

let server = startServer();
let browser;
try {
  await waitForServer();
  browser = await chromium.launch({ channel: "chrome", headless: true });

  for (const [width, height] of VIEWPORTS) {
    for (const theme of ["light", "dark"]) {
      const phone = width < 600;
      const tag = `${width}-${theme}`;
      const context = await browser.newContext({ viewport: { width, height }, colorScheme: theme, hasTouch: phone });
      const page = await context.newPage();
      page.on("console", (message) => { if (message.type() === "error") failures.push(`${tag}: console error: ${message.text()}`); });
      page.on("pageerror", (error) => failures.push(`${tag}: page error: ${error.message}`));

      await page.goto(BASE);
      await page.waitForSelector(".destination");
      await check(page, `${tag}-1-start`, phone);
      await page.click(".destination >> nth=4");
      await page.click("text=Plan my route");
      await page.waitForSelector(".option[role=radio]");
      await check(page, `${tag}-2-question`, phone);

      await answer(page, { correct: false, sure: false });
      await check(page, `${tag}-3-feedback`, phone);
      await page.click("#continue");
      await page.waitForSelector(".lesson");
      await check(page, `${tag}-4-lesson`, phone);
      await page.click("#continue");

      await page.click("#dock a[data-view=map]");
      await page.waitForSelector("svg.map");
      await check(page, `${tag}-5-map`, phone);
      await page.click("#dock a[data-view=engine]");
      for (const [index, tab] of ["hmm", "mdp", "astar", "evidence"].entries()) {
        await page.click(`.seg button >> nth=${index}`);
        if (tab === "astar") await page.click("text=Compare with UCS");
        await page.waitForSelector(".sheet table");
        await check(page, `${tag}-6-engine-${tab}`, phone);
      }

      await page.click("#dock a[data-view=drive]");
      await page.waitForSelector(".option[role=radio]");
      const before = await page.locator(".prompt").innerText();
      await page.reload();
      await page.waitForSelector(".option[role=radio]");
      if (await page.locator(".prompt").innerText() !== before) failures.push(`${tag}: the step changed after a reload`);

      for (let guard = 0; guard < 60 && !(await page.$(".arrived")); guard += 1) {
        if (await page.$(".lesson")) { await page.click("#continue"); continue; }
        if (await page.$(".verdict")) { await page.keyboard.press("Enter"); await sleep(120); continue; }
        const right = key.get(await page.locator(".prompt").innerText());
        await page.keyboard.press(String(right + 1));
        await page.keyboard.press("s");
        await page.waitForSelector("#continue");
      }
      if (!(await page.$(".arrived"))) failures.push(`${tag}: the route never ended`);
      await check(page, `${tag}-7-arrived`, phone);

      await page.goto(`${BASE}/#/`);
      await page.waitForSelector(".destination");
      await page.click("text=erase progress");
      await page.click("text=press again to erase everything");
      await sleep(200);
      if (await page.$("text=answers kept on this device")) failures.push(`${tag}: erase did not clear the history`);
      await context.close();
    }
  }

  if (REMOTE) throw Object.assign(new Error("skip"), { skip: true });
  const context = await browser.newContext({ viewport: { width: 1366, height: 768 } });
  const page = await context.newPage();
  await page.goto(BASE);
  await page.click("text=Plan my route");
  await page.waitForSelector(".option[role=radio]");
  server.kill("SIGINT");
  await sleep(700);
  await page.click(".option >> nth=0");
  await page.click("#sure");
  await page.waitForSelector(".error");
  if (!(await page.locator(".error").innerText()).includes("Nothing is lost")) failures.push("recovery: the error state does not reassure the learner");
  if (shots) await page.screenshot({ path: join(shots, "recovery-error.png") });
  server = startServer();
  await waitForServer();
  await page.click("text=Try again");
  await page.waitForSelector("#continue");
  await context.close();
} catch (error) {
  if (!error.skip) failures.push(`the run stopped: ${error.message}`);
} finally {
  if (browser) await browser.close();
  server.kill("SIGINT");
}

if (failures.length) {
  console.error(`${failures.length} problem(s):`);
  for (const failure of [...new Set(failures)]) console.error(`  - ${failure}`);
  process.exit(1);
}
console.log(`interface check passed: ${VIEWPORTS.length} sizes x 2 themes, every screen, plus persistence, keyboard, erase and recovery`);
