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
const SIZE = { width: 1920, height: 1080 };
const APP = { width: 1344, height: 651, scale: 1728 / 1344 };
const FRAME = { left: 96, top: 120 };
const media = join(root, "docs", "media");
const raw = join(media, "raw");
mkdirSync(raw, { recursive: true });

const LINES = Object.fromEntries(JSON.parse(readFileSync(join(root, "tools", "demo_lines.json"), "utf8")).map((line) => [line.id, line]));
const narration = join(media, "narration");
const VOICE = existsSync(join(narration, "manifest.json")) ? JSON.parse(readFileSync(join(narration, "manifest.json"), "utf8")) : null;
const TRIM = 0.6;
const timeline = [];

const key = new Map();
for (const file of readdirSync(join(root, "content")).filter((name) => name.startsWith("part_"))) {
  for (const item of JSON.parse(readFileSync(join(root, "content", file), "utf8")).items) key.set(item.prompt, item.answer);
}

const STAGE = `<!doctype html><html lang="en" data-theme="light"><head><meta charset="utf-8"><title>Meje demo</title>
<link rel="stylesheet" href="/kit.css">
<style>
  @font-face { font-family: "Source Serif 4"; src: url("/fonts/SourceSerif4-latin.woff2") format("woff2"); font-weight: 200 900; }
  html, body { margin: 0; width: 1920px; height: 1080px; overflow: hidden; background: var(--bg); }
  .serif { font-family: "Source Serif 4", Georgia, serif; font-weight: 300; letter-spacing: -0.022em; }
  .mono { font: 400 26px/1.2 var(--font-mono); color: var(--mut); text-transform: lowercase; }
  #top { position: absolute; left: 96px; right: 96px; top: 0; height: 120px; display: flex; align-items: center; gap: 44px; }
  #brand { display: flex; align-items: center; gap: 14px; color: var(--fg); }
  #brand::before { content: ""; width: 14px; height: 14px; background: var(--fg); }
  #chapter { flex: 1; font-size: 46px; line-height: 1; opacity: 0; transition: opacity .45s; white-space: nowrap; }
  #progress { position: relative; width: 400px; height: 30px; border-bottom: 2px solid var(--line); }
  #progress i { position: absolute; bottom: 0; width: 2px; height: 14px; background: var(--tick); }
  #progress b { position: absolute; left: -8px; bottom: 22px; width: 16px; height: 16px; background: var(--acc); transition: transform .9s cubic-bezier(.22,1.16,.36,1); }
  #frame { position: absolute; left: ${FRAME.left}px; top: ${FRAME.top}px; width: 1728px; height: 837px; border: 1px solid var(--line); border-radius: 18px; overflow: hidden; }
  #app { display: block; width: ${APP.width}px; height: ${APP.height}px; border: 0; transform: scale(${APP.scale}); transform-origin: 0 0; }
  #spot { position: absolute; border-radius: 18px; pointer-events: none; opacity: 0; outline: 2px solid var(--tick);
    box-shadow: 0 0 0 3000px color-mix(in oklch, var(--bg) 72%, transparent); transition: opacity .4s, top .5s, left .5s, width .5s, height .5s; }
  #bottom { position: absolute; left: 160px; right: 160px; bottom: 0; height: 123px; display: flex; align-items: center; justify-content: center; text-align: center; }
  #caption { font: 400 32px/1.3 var(--font-sans); opacity: 0; transition: opacity .3s; }
  #cursor { position: absolute; left: -12px; top: -12px; z-index: 50; width: 24px; height: 24px; border-radius: 50%; background: var(--fg); opacity: 0;
    transition: transform .55s cubic-bezier(.32,.72,0,1), opacity .3s; pointer-events: none; }
  #card { position: absolute; inset: 0; z-index: 60; background: var(--bg); display: flex; flex-direction: column; justify-content: center; padding: 0 190px;
    opacity: 0; transition: opacity .45s; pointer-events: none; }
  #card h1 { font-size: 150px; line-height: 1.02; margin: 0; }
  #card .mono { font-size: 28px; }
  #card .mono + h1, #card h1 + h1 { margin-top: 22px; }
  #card h1 + .mono { margin-top: 44px; }
</style></head><body>
  <div id="top"><span id="brand" class="mono">meje</span><span id="chapter" class="serif"></span><div id="progress"><b id="marker"></b></div></div>
  <div id="frame"><iframe id="app" src="/" title="Meje"></iframe><div id="spot"></div></div>
  <div id="bottom"><span id="caption"></span></div>
  <div id="cursor"></div>
  <div id="card"></div>
  <script>
    const progress = document.getElementById("progress");
    for (let i = 0; i <= 4; i += 1) { const tick = document.createElement("i"); tick.style.left = (i * 25) + "%"; progress.append(tick); }
  </script>
</body></html>`;

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const server = spawn(process.env.PYTHON || "python3", ["-m", "meje", "serve", "--no-browser", "--port", String(PORT)], { cwd: root, stdio: "ignore" });
let browser;
let failed = false;

try {
  for (let i = 0; i < 80; i += 1) {
    try { if ((await fetch(`${BASE}/health`)).ok) break; } catch {}
    await sleep(100);
  }
  browser = await chromium.launch({ channel: "chrome", headless: true });
  const context = await browser.newContext({ viewport: SIZE, colorScheme: "light", recordVideo: { dir: raw, size: SIZE } });
  await context.route(`${BASE}/**`, async (route) => {
    const response = await route.fetch();
    const headers = { ...response.headers() };
    delete headers["x-frame-options"];
    delete headers["content-security-policy"];
    await route.fulfill({ response, headers });
  });
  await context.route(`${BASE}/__stage`, (route) => route.fulfill({ contentType: "text/html; charset=utf-8", body: STAGE }));
  const page = await context.newPage();
  const started = Date.now();
  const errors = [];
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto(`${BASE}/__stage`);
  const app = page.frameLocator("#app");
  await app.locator(".destination").first().waitFor();
  await page.evaluate(() => document.fonts.ready);

  let lineEnds = 0;
  const say = async (id, silentHold = 4000) => {
    timeline.push({ id, at: Date.now() - started });
    lineEnds = Date.now() + (VOICE ? VOICE[id] * 1000 + 350 : silentHold);
    await page.evaluate((text) => {
      const node = document.getElementById("caption");
      if (text) node.textContent = text;
      node.style.opacity = text ? "1" : "0";
    }, LINES[id].show);
  };
  const rest = async (extra = 0) => { await sleep(Math.max(0, lineEnds - Date.now()) + extra); };
  const quiet = () => page.evaluate(() => { document.getElementById("caption").style.opacity = "0"; });

  const card = async (id, { label = "", title, second = "", sub = "" }, hold = 300) => {
    await page.evaluate(([l, t, s2, s]) => {
      const node = document.getElementById("card");
      node.innerHTML = (l ? `<span class="mono">${l}</span>` : "") + `<h1 class="serif">${t}</h1>` + (s2 ? `<h1 class="serif acc">${s2}</h1>` : "") + (s ? `<span class="mono">${s}</span>` : "");
      node.style.opacity = "1";
    }, [label, title, second, sub]);
    await sleep(450);
    await say(id);
    await rest(hold);
  };
  const uncard = async () => { await page.evaluate(() => { document.getElementById("card").style.opacity = "0"; }); await sleep(550); };
  const chapter = (index, title) => page.evaluate(([i, t]) => {
    const node = document.getElementById("chapter");
    node.innerHTML = t;
    node.style.opacity = "1";
    document.getElementById("marker").style.transform = `translateX(${i * 100}px)`;
  }, [index, title]);

  const moveCursor = async (box) => {
    await page.evaluate(([x, y]) => {
      const cursor = document.getElementById("cursor");
      cursor.style.opacity = "0.5";
      cursor.style.transform = `translate(${x}px, ${y}px)`;
    }, [box.x + box.width / 2, box.y + Math.min(box.height / 2, 40)]);
    await sleep(620);
  };
  const click = async (selector, pause = 600) => {
    const target = app.locator(selector).first();
    await target.scrollIntoViewIfNeeded();
    await sleep(150);
    await moveCursor(await target.boundingBox());
    await target.click();
    await sleep(pause);
  };
  const spot = async (selector, pad = 12) => {
    const target = app.locator(selector).first();
    await target.scrollIntoViewIfNeeded();
    await sleep(200);
    const box = await target.boundingBox();
    await page.evaluate(([b, p, f]) => {
      Object.assign(document.getElementById("spot").style, {
        left: `${b.x - f.left - p}px`, top: `${b.y - f.top - p}px`, width: `${b.width + 2 * p}px`, height: `${b.height + 2 * p}px`, opacity: "1" });
    }, [box, pad, FRAME]);
  };
  const unspot = async () => { await page.evaluate(() => { document.getElementById("spot").style.opacity = "0"; }); await sleep(300); };
  const answer = async ({ correct, sure, pause = 800 }) => {
    await app.locator(".option[role=radio]").first().waitFor();
    const prompt = await app.locator(".prompt").innerText();
    if (!key.has(prompt)) throw new Error(`no answer key for: ${prompt}`);
    const right = key.get(prompt);
    await click(`.option >> nth=${correct ? right : (right + 1) % 4}`, 400);
    await click(sure ? "#sure" : "#unsure", pause);
    await app.locator("#continue").waitFor();
  };
  const shot = async () => {};

  await card("hook", { title: "You scored 7 out of 10.", second: "Which 7 did you guess?" }, 500);
  await card("intro", { label: "ai fundamentals · final project · mustafa kassym", title: 'Meje: a <span class="acc">GPS</span> for learning', sub: "where am i · what next · which way" }, 400);
  await shot("01-start");
  await chapter(0, "Choose a destination");
  await uncard();
  await say("dest");
  await click("text=Plan my route", 900);
  await app.locator(".option").first().waitFor();
  await spot(".journey", 8);
  await rest(500);
  await unspot();
  await quiet();

  await card("q1", { label: "question 1 of 3 · hidden markov model", title: 'Where <span class="acc">am I</span>?' });
  await chapter(1, 'Where am I? <span class="mono">&nbsp; hidden markov model</span>');
  await uncard();
  await shot("02-question");
  await say("answer");
  await answer({ correct: false, sure: false });
  await rest(200);
  await say("belief");
  await spot(".why > section:nth-of-type(1)");
  await shot("03-feedback");
  await rest(300);
  await unspot();
  await quiet();

  await card("q2", { label: "question 2 of 3 · markov decision process", title: 'What should I do <span class="acc">now</span>?' });
  await chapter(2, 'What should I do now? <span class="mono">&nbsp; markov decision process</span>');
  await click("#continue", 700);
  await uncard();
  await say("decide");
  await spot(".why > section:nth-of-type(2)");
  await shot("04-lesson");
  await rest(300);
  await unspot();
  await say("moveon");
  await click("#continue", 700);
  await answer({ correct: true, sure: true });
  await click("#continue", 600);
  await answer({ correct: true, sure: true });
  await spot(".verdict");
  await shot("05-checkpoint");
  await rest(900);
  await unspot();
  await quiet();

  await card("q3", { label: "question 3 of 3 · a* search", title: 'Which way is the <span class="acc">shortest</span>?' });
  await chapter(3, 'Which way is the shortest? <span class="mono">&nbsp; a* search</span>');
  await click("#continue", 500);
  await click("#dock a[data-view=map]", 900);
  await uncard();
  await say("route");
  await shot("07-map");
  await rest(400);
  await say("detour");
  await click(".map .node >> nth=19", 700);
  await click("text=Study this now", 1300);
  await spot(".why > section:nth-of-type(3)");
  await shot("06-progress");
  await rest(900);
  await unspot();
  await click("text=back to the planned route", 800);
  await quiet();

  await card("q4", { label: "and one more", title: 'Can I <span class="acc">check</span> it?' });
  await chapter(4, 'Can I check it? <span class="mono">&nbsp; every number is shown</span>');
  await click("#dock a[data-view=engine]", 900);
  await uncard();
  await say("open");
  await shot("08-engine-hmm");
  await sleep(1700);
  await click(".seg button >> nth=1", 1500);
  await shot("09-engine-mdp");
  await click(".seg button >> nth=2", 900);
  await click("text=Compare with UCS", 900);
  await shot("10-engine-astar");
  await rest(300);
  await click(".seg button >> nth=3", 900);
  await app.locator(".sheet table").first().waitFor();
  await say("proof");
  await shot("11-evidence");
  await rest(500);
  await quiet();

  await card("outro", { title: "Meje", second: "Know where you are.<br>Get where you're going.", sub: "meje-delta.vercel.app · github.com/user1618phi/meje" }, 1400);

  if (errors.length) throw new Error(`console errors: ${errors.join(" | ")}`);
  await context.close();

  const still = await browser.newContext({ viewport: { width: 1366, height: 768 }, colorScheme: "light" });
  const view = await still.newPage();
  const snap = async (name) => { await sleep(1100); await view.screenshot({ path: join(media, `${name}.png`) }); };
  const reply = async (correct, sure) => {
    await view.waitForSelector(".option[role=radio]");
    const right = key.get(await view.locator(".prompt").innerText());
    await view.click(`.option >> nth=${correct ? right : (right + 1) % 4}`);
    await view.click(sure ? "#sure" : "#unsure");
    await view.waitForSelector("#continue");
  };
  await view.goto(BASE);
  await view.waitForSelector(".destination");
  await snap("01-start");
  await view.click("text=Plan my route");
  await view.waitForSelector(".option");
  await snap("02-question");
  await reply(false, false);
  await snap("03-feedback");
  await view.click("#continue");
  await snap("04-lesson");
  await view.click("#continue");
  await reply(true, true);
  await view.click("#continue");
  await reply(true, true);
  await snap("05-checkpoint");
  await view.click("#continue");
  for (let i = 0; i < 4; i += 1) { await reply(true, true); await view.click("#continue"); }
  await snap("06-progress");
  await view.click("#dock a[data-view=map]");
  await snap("07-map");
  await view.click("#dock a[data-view=engine]");
  await snap("08-engine-hmm");
  await view.click(".seg button >> nth=1");
  await snap("09-engine-mdp");
  await view.click(".seg button >> nth=2");
  await view.click("text=Compare with UCS");
  await view.mouse.wheel(0, 500);
  await snap("10-engine-astar");
  await view.click(".seg button >> nth=3");
  await view.waitForSelector(".sheet table");
  await snap("11-evidence");
  await view.click("#theme");
  await view.click("#dock a[data-view=drive]");
  await snap("12-dark");
  await still.close();
} catch (error) {
  failed = true;
  console.error(`recording failed: ${error.message}`);
} finally {
  if (browser) await browser.close();
  server.kill("SIGINT");
}

if (failed) process.exit(1);

const source = join(raw, readdirSync(raw).find((name) => name.endsWith(".webm")));
const target = join(media, "meje-demo.mp4");
const args = ["-y", "-ss", String(TRIM), "-i", source];
const video = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "slow", "-movflags", "+faststart"];
if (VOICE) {
  const filters = timeline.map(({ id, at }, index) => {
    const delay = Math.max(0, Math.round(at - TRIM * 1000));
    args.push("-i", join(narration, `${id}.mp3`));
    return `[${index + 1}:a]adelay=${delay}|${delay}[a${index}]`;
  });
  const mixed = `${timeline.map((_, index) => `[a${index}]`).join("")}amix=inputs=${timeline.length}:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[voice]`;
  const seconds = Math.ceil(timeline[timeline.length - 1].at / 1000 + VOICE[timeline[timeline.length - 1].id] + 3);
  const bed = join(raw, "bed.wav");
  const made = spawnSync(process.env.PYTHON || "python3", [join(root, "tools", "brag", "music.py"), bed, "--bed", String(seconds)], { stdio: "inherit" });
  if (made.status === 0) {
    args.push("-i", bed);
    const index = timeline.length + 1;
    args.push("-filter_complex", `${filters.join(";")};${mixed};[${index}:a]volume=0.5[bed];[voice][bed]amix=inputs=2:normalize=0,alimiter=limit=0.7[out]`,
      "-map", "0:v", "-map", "[out]", ...video, "-c:a", "aac", "-b:a", "160k", "-shortest", target);
  } else {
    args.push("-filter_complex", `${filters.join(";")};${mixed}`, "-map", "0:v", "-map", "[voice]", ...video, "-c:a", "aac", "-b:a", "160k", target);
  }
} else {
  args.push(...video, "-an", target);
}
const result = spawnSync("ffmpeg", args, { stdio: "ignore" });
if (result.status !== 0) { console.error("ffmpeg failed"); process.exit(1); }
rmSync(raw, { recursive: true, force: true });
console.log(`saved ${target}${VOICE ? " (with narration)" : ""}`);
