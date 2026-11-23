// Records the demo video and the README screenshots by driving the real app in a real browser.
// It doubles as an end-to-end check: any console error or missing element fails the run.
//
//   node tools/record_demo.mjs            (needs: npm i playwright, Google Chrome, ffmpeg)
//
// The script starts the app itself on a free port, plays one scripted session with captions,
// stops the app, and converts the recording to docs/media/bagdar-demo.mp4.
// Lines come from tools/demo_lines.json. If tools/narrate.mjs has produced voice clips, the film
// is timed to the voice and the clips are mixed in; otherwise it is a silent film with captions.

import { spawn, spawnSync } from "node:child_process";
import { createRequire } from "node:module";
import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(process.env.PLAYWRIGHT_FROM || import.meta.url);
const { chromium } = require("playwright");

const PORT = 8791;
const BASE = `http://127.0.0.1:${PORT}`;
const SIZE = { width: 1366, height: 768 };
const media = join(root, "docs", "media");
const raw = join(media, "raw");
mkdirSync(raw, { recursive: true });

// The answer key, so the scripted learner can answer right or wrong on purpose.
const key = new Map();
for (const file of readdirSync(join(root, "content")).filter((name) => name.startsWith("part_"))) {
  for (const item of JSON.parse(readFileSync(join(root, "content", file), "utf8")).items) key.set(item.prompt, item.answer);
}

const LINES = Object.fromEntries(JSON.parse(readFileSync(join(root, "tools", "demo_lines.json"), "utf8")).map((line) => [line.id, line]));
const narration = join(media, "narration");
const VOICE = existsSync(join(narration, "manifest.json")) ? JSON.parse(readFileSync(join(narration, "manifest.json"), "utf8")) : null;
const SPEED = 1.0;  // playback speed of the voice clips (raise slightly if the film runs over three minutes)
const TRIM = 0.6;  // seconds cut from the start of the recording (blank page before the app loads)
const timeline = [];  // [{ id, at }] in milliseconds from the start of the recording

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const server = spawn(process.env.PYTHON || "python3", ["-m", "bagdar", "serve", "--no-browser", "--port", String(PORT)], { cwd: root, stdio: "ignore" });
let browser;
let failed = false;

try {
  for (let i = 0; i < 80; i += 1) {
    try { if ((await fetch(`${BASE}/health`)).ok) break; } catch { /* not up yet */ }
    await sleep(100);
  }
  browser = await chromium.launch({ channel: "chrome", headless: true });
  // bypassCSP: the caption and cursor overlays are injected by this script, which the app's own policy would block
  const context = await browser.newContext({ viewport: SIZE, colorScheme: "light", bypassCSP: true, recordVideo: { dir: raw, size: SIZE } });
  const page = await context.newPage();
  const started = Date.now();
  const errors = [];
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  page.on("pageerror", (error) => errors.push(error.message));

  // A visible cursor, a caption bar and title cards, drawn by the recording script only (not part of the app).
  await page.addInitScript(() => {
    window.addEventListener("DOMContentLoaded", () => {
      const style = document.createElement("style");
      style.textContent = `
        #demo-cursor { position: fixed; z-index: 99; width: 14px; height: 14px; margin: -7px 0 0 -7px; border-radius: 50%;
          background: var(--fg); opacity: .55; pointer-events: none; }
        #demo-caption { position: fixed; z-index: 98; left: 50%; top: 10px; transform: translateX(-50%); width: min(900px, 92vw);
          padding: 13px 20px; border-radius: 13px; background: var(--fg); color: var(--bg); font: 400 17px/1.4 "Medeo Sans", sans-serif;
          text-align: center; opacity: 0; transition: opacity .35s; pointer-events: none; }
        #demo-spot { position: fixed; z-index: 96; border-radius: 16px; pointer-events: none; opacity: 0;
          box-shadow: 0 0 0 200vmax color-mix(in oklch, var(--bg) 70%, transparent); outline: 1px solid var(--tick);
          transition: opacity .4s, top .45s, left .45s, width .45s, height .45s; }
        #demo-card { position: fixed; inset: 0; z-index: 97; display: grid; place-content: center; gap: 18px; background: var(--bg);
          text-align: center; opacity: 0; transition: opacity .5s; pointer-events: none; }
        #demo-card h1 { font-size: 76px; } #demo-card p { margin: 0 auto; font: 400 15px/1.5 "Medeo Mono", monospace; color: var(--mut); }`;
      document.head.append(style);
      for (const id of ["demo-spot", "demo-card", "demo-caption", "demo-cursor"]) {
        const node = document.createElement("div");
        node.id = id;
        document.body.append(node);
      }
      window.addEventListener("mousemove", (event) => {
        const cursor = document.getElementById("demo-cursor");
        cursor.style.left = `${event.clientX}px`;
        cursor.style.top = `${event.clientY}px`;
      });
    });
  });

  // say() starts a line (caption and voice) and returns at once, so actions can happen while it is spoken;
  // rest() waits until the line is over.
  let lineEnds = 0;
  const say = async (id, silentHold = 4500) => {
    const line = LINES[id];
    timeline.push({ id, at: Date.now() - started });
    lineEnds = Date.now() + (VOICE ? (VOICE[id] / SPEED) * 1000 + 350 : silentHold);
    await page.evaluate((text) => {
      const node = document.getElementById("demo-caption");
      if (text) node.textContent = text;
      node.style.opacity = text ? "1" : "0";
    }, line.show);
  };
  const rest = async (extra = 0) => { await sleep(Math.max(0, lineEnds - Date.now()) + extra); };
  const card = async (id, title, rows) => {
    await page.evaluate(([heading, lines]) => {
      const node = document.getElementById("demo-card");
      node.innerHTML = "";
      const h1 = document.createElement("h1");
      h1.innerHTML = heading;
      node.append(h1, ...lines.map((row) => Object.assign(document.createElement("p"), { textContent: row })));
      node.style.opacity = "1";
    }, [title, rows]);
    await sleep(500);
    await say(id, 4200);
    await rest(300);
    await page.evaluate(() => { document.getElementById("demo-card").style.opacity = "0"; });
    await sleep(600);
  };
  // spot() dims everything except one element, so the viewer knows where to look while a line is spoken
  const spot = async (selector, pad = 14) => {
    await page.evaluate(([target, space]) => {
      const node = document.querySelector(target);
      const ring = document.getElementById("demo-spot");
      if (!node) { ring.style.opacity = "0"; return; }
      const box = node.getBoundingClientRect();
      Object.assign(ring.style, { top: `${box.top - space}px`, left: `${box.left - space}px`,
        width: `${box.width + 2 * space}px`, height: `${box.height + 2 * space}px`, opacity: "1" });
    }, [selector, pad]);
  };
  const unspot = async () => { await page.evaluate(() => { document.getElementById("demo-spot").style.opacity = "0"; }); await sleep(250); };
  const click = async (selector, pause = 500) => {
    await page.locator(selector).first().scrollIntoViewIfNeeded();
    const box = await page.locator(selector).first().boundingBox();
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 28 });
    await sleep(220);
    await page.mouse.down();
    await sleep(90);
    await page.mouse.up();
    await sleep(pause);
  };
  const answer = async ({ correct, sure, pause = 900 }) => {
    await page.waitForSelector(".option[role=radio]");
    const prompt = await page.locator(".prompt").innerText();
    if (!key.has(prompt)) throw new Error(`no answer key for: ${prompt}`);
    const right = key.get(prompt);
    await click(`.option >> nth=${correct ? right : (right + 1) % 4}`, 450);
    await click(sure ? "#sure" : "#unsure", pause);
    await page.waitForSelector("#continue");
  };
  // screenshots for the README are taken without the caption and the cursor
  const shot = (name) => page.screenshot({ path: join(media, `${name}.png`), style: "#demo-caption, #demo-cursor, #demo-spot { display: none !important; }" });

  // ------------------------------------------------------------------ the film
  await page.goto(BASE);
  await page.waitForSelector(".destination");
  await card("intro", 'Bagdar: a <span class="acc">GPS</span> for learning', ["AI Fundamentals final project · Mustafa Kassym · QAIRU, 2026", "hmm locates · a* routes · mdp steers"]);
  await say("problem");
  await shot("01-start");
  await rest();

  await say("route");
  await sleep(1300);
  await click("text=Plan my route", 1100);
  await page.waitForSelector(".option");
  await spot(".journey", 10);
  await rest();
  await say("prior");
  await spot(".why > section:nth-of-type(1)");
  await shot("02-question");
  await rest();
  await unspot();

  await say("bayes");
  await answer({ correct: false, sure: false });
  await spot(".why > section:nth-of-type(1)");
  await shot("03-feedback");
  await rest();
  await unspot();
  await click("#continue", 900);
  await say("lesson");
  await spot(".why > section:nth-of-type(2)");
  await shot("04-lesson");
  await rest();
  await unspot();
  await click("#continue", 900);

  await say("question");
  await answer({ correct: true, sure: true });
  await rest(300);
  await click("#continue", 800);
  await answer({ correct: true, sure: true });
  await say("threshold");
  await spot(".verdict");
  await shot("05-checkpoint");
  await rest();
  await unspot();
  await click("#continue", 800);

  await say("fast");
  for (let i = 0; i < 4; i += 1) {
    await answer({ correct: true, sure: true, pause: 500 });
    await sleep(350);
    await click("#continue", 500);
  }
  await shot("06-progress");
  await rest();

  await click("#dock a[data-view=map]", 1100);
  await say("map");
  await shot("07-map");
  await rest();
  await say("control");
  await click(".map .node >> nth=19", 800);  // perceptron: unlocked, off the route, so the detour has a price
  await click("text=Study this now", 1500);
  await page.locator("text=Your detour adds").scrollIntoViewIfNeeded();
  await spot(".why > section:nth-of-type(3)");
  await rest(900);
  await unspot();
  await click("text=back to the planned route", 1000);

  await click("#dock a[data-view=engine]", 1100);
  await say("hmm");
  await shot("08-engine-hmm");
  await rest();
  await click(".seg button >> nth=1", 800);
  await say("mdp");
  await shot("09-engine-mdp");
  await sleep(3800);
  await page.mouse.wheel(0, 420);
  await rest();
  await click(".seg button >> nth=2", 800);
  await say("astar");
  await click("text=Compare with UCS", 1100);
  await page.mouse.wheel(0, 500);
  await shot("10-engine-astar");
  await rest();
  await click(".seg button >> nth=3", 1100);
  await page.waitForSelector(".sheet table");
  await say("real");
  await shot("11-evidence");
  await rest();
  await page.locator("text=your own ledger").first().scrollIntoViewIfNeeded();
  await say("ledger");
  await rest();
  await page.mouse.wheel(0, -6000);
  await page.evaluate(() => { document.getElementById("demo-caption").style.opacity = "0"; });
  await click("#theme", 1000);
  await click("#dock a[data-view=drive]", 1400);
  await shot("12-dark");
  await card("outro", "Bagdar", ["hmm locates · a* routes · mdp steers", "81 tests · zero dependencies · python -m bagdar", "github.com/user1618phi/bagdar"]);
  await sleep(700);

  if (errors.length) throw new Error(`console errors: ${errors.join(" | ")}`);
  await context.close();
} catch (error) {
  failed = true;
  console.error(`recording failed: ${error.message}`);
} finally {
  if (browser) await browser.close();
  server.kill("SIGINT");
}

if (failed) process.exit(1);

const source = join(raw, readdirSync(raw).find((name) => name.endsWith(".webm")));
const target = join(media, "bagdar-demo.mp4");
const args = ["-y", "-ss", String(TRIM), "-i", source];
const video = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "21", "-preset", "slow", "-movflags", "+faststart"];
if (VOICE) {
  // each clip is sped up a little and delayed to the moment its caption appeared, then all are mixed
  const filters = timeline.map(({ id, at }, index) => {
    const delay = Math.max(0, Math.round(at - TRIM * 1000));
    args.push("-i", join(narration, `${id}.mp3`));
    return `[${index + 1}:a]atempo=${SPEED},adelay=${delay}|${delay}[a${index}]`;
  });
  const mixed = `${timeline.map((_, index) => `[a${index}]`).join("")}amix=inputs=${timeline.length}:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[voice]`;
  args.push("-filter_complex", `${filters.join(";")};${mixed}`, "-map", "0:v", "-map", "[voice]", ...video, "-c:a", "aac", "-b:a", "160k", target);
} else {
  args.push(...video, "-an", target);
}
const result = spawnSync("ffmpeg", args, { stdio: "ignore" });
rmSync(raw, { recursive: true, force: true });
if (result.status !== 0) { console.error("ffmpeg failed"); process.exit(1); }
console.log(`saved ${target}${VOICE ? " (with narration)" : ""}`);
