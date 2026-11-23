import { spawnSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const out = join(root, "docs", "media", "narration");
const { ELEVENLABS_API_KEY: key, ELEVENLABS_VOICE_ID: voice } = process.env;
if (!key || !voice) {
  console.error("Set ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID in the environment.");
  process.exit(1);
}
mkdirSync(out, { recursive: true });
const lines = JSON.parse(readFileSync(join(root, "tools", "demo_lines.json"), "utf8"));
const manifest = {};

for (const [index, line] of lines.entries()) {
  const response = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voice}?output_format=mp3_44100_128`, {
    method: "POST",
    headers: { "xi-api-key": key, "Content-Type": "application/json" },
    body: JSON.stringify({
      text: line.say,
      model_id: "eleven_multilingual_v2",
      voice_settings: { stability: 0.5, similarity_boost: 0.8, style: 0.0, use_speaker_boost: true },
      previous_text: lines[index - 1]?.say,
      next_text: lines[index + 1]?.say,
    }),
  });
  if (!response.ok) {
    console.error(`${line.id}: ElevenLabs answered ${response.status} ${(await response.text()).slice(0, 200)}`);
    process.exit(1);
  }
  const file = join(out, `${line.id}.mp3`);
  writeFileSync(file, Buffer.from(await response.arrayBuffer()));
  const probe = spawnSync("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", file], { encoding: "utf8" });
  manifest[line.id] = Number(probe.stdout.trim());
  console.log(`${line.id.padEnd(10)} ${manifest[line.id].toFixed(2)} s`);
}
writeFileSync(join(out, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
console.log(`total speech ${Object.values(manifest).reduce((a, b) => a + b, 0).toFixed(1)} s`);
