import { spawnSync } from "node:child_process";
import { createRequire } from "node:module";
import { copyFileSync, mkdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..");
const { chromium } = createRequire(process.env.PLAYWRIGHT_FROM || import.meta.url)("playwright");
const out = join(root, "brag-output");
const work = join(out, "work");
mkdirSync(work, { recursive: true });

const FPS = 30;
const SECONDS = 20;
const POSTER_AT = 19.2;
const skills = JSON.parse(readFileSync(join(root, "content", "skills.json"), "utf8")).skills;
const stillsOnly = process.argv[2] === "stills";

const browser = await chromium.launch({ channel: "chrome", headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  await page.addInitScript((data) => { window.SKILLS = data; }, skills);
  await page.goto(pathToFileURL(join(here, "film.html")).href);
  await page.waitForFunction(() => window.READY === true);
  const frame = async (t, file, type = "png") => {
    await page.evaluate((time) => window.renderAt(time), t);
    await page.screenshot({ path: file, type, ...(type === "jpeg" ? { quality: 92 } : {}) });
  };

  if (stillsOnly) {
    for (const t of [1.0, 2.5, 2.9, 3.15, 4.8, 5.9, 6.2, 8.8, 9.9, 10.2, 13.8, 14.2, 16.4, 17.2, 19.2]) {
      await frame(t, join(work, `still_${t.toFixed(2)}.png`));
    }
    console.log(`stills in ${work}`);
  } else {
    for (let i = 0; i < FPS * SECONDS; i += 1) await frame(i / FPS, join(work, `frame_${String(i).padStart(4, "0")}.png`));
    await frame(POSTER_AT, join(out, "brag.jpg"), "jpeg");
    await frame(POSTER_AT, join(work, "poster.png"));
    copyFileSync(join(work, "poster.png"), join(work, "frame_0000.png"));
    const music = spawnSync(process.env.PYTHON || "python3", [join(here, "music.py"), join(work, "music.wav")], { stdio: "inherit" });
    if (music.status !== 0) throw new Error("music synthesis failed");
    const encode = spawnSync("ffmpeg", ["-y", "-framerate", String(FPS), "-i", join(work, "frame_%04d.png"), "-i", join(work, "music.wav"),
      "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "slow", "-c:a", "aac", "-b:a", "192k",
      "-movflags", "+faststart", "-shortest", join(out, "brag.mp4")], { stdio: "ignore" });
    if (encode.status !== 0) throw new Error("ffmpeg failed");
    console.log(`saved ${join(out, "brag.mp4")}`);
  }
} finally {
  await browser.close();
}
