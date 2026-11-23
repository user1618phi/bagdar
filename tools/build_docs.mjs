// Builds the PDFs that are handed in: slides, technical report and statements.
//
//   node tools/build_docs.mjs        (needs: npm i playwright marked, Google Chrome)
//
// Markdown is rendered with the same fonts and tokens as the app, then printed by Chrome.

import { createRequire } from "node:module";
import { mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const docs = join(root, "docs");
const { chromium } = createRequire(process.env.PLAYWRIGHT_FROM || import.meta.url)("playwright");
const { marked } = createRequire(process.env.MARKED_FROM || import.meta.url)("marked");

const PAGES = [
  ["REPORT.md", "Bagdar_Technical_Report.pdf"],
  ["TEAM_CONTRIBUTION.md", "Bagdar_Team_Contribution_Statement.pdf"],
  ["AI_USAGE_DECLARATION.md", "Bagdar_AI_Usage_Declaration_Template.pdf"],
  ["COMPETITION.md", "Bagdar_Competition.pdf"],
  ["DESIGN.md", "Bagdar_Design_Decisions.pdf"],
  ["DEFENSE.md", "Bagdar_Defense_Notes.pdf"],
];

const PRINT_CSS = `
  @font-face { font-family: "Source Serif 4"; src: url("../../web/fonts/SourceSerif4-latin.woff2") format("woff2"); font-weight: 200 900; }
  @page { size: A4; margin: 19mm 18mm 20mm; }
  html { font-size: 10.4pt; line-height: 1.5; }
  body { min-height: 0; }
  h1, h2, h3 { font-family: "Source Serif 4", Georgia, serif; font-weight: 400; letter-spacing: -0.012em; line-height: 1.15; break-after: avoid; }
  h1 { font-size: 27pt; font-weight: 300; margin: 0 0 12pt; }
  h2 { font-size: 16.5pt; margin: 22pt 0 7pt; padding-top: 9pt; border-top: 1px solid var(--line); }
  h3 { font-size: 12.5pt; margin: 14pt 0 4pt; }
  p, ul, ol { margin: 0 0 7pt; max-width: none; }
  li { margin-bottom: 2.5pt; }
  table { font-size: 8.7pt; margin: 6pt 0 11pt; break-inside: auto; }
  tr { break-inside: avoid; }
  th { font-size: 7.8pt; }
  th, td { padding: 4pt 8pt 4pt 0; }
  code { font-size: 0.88em; }
  pre { font-size: 8.2pt; line-height: 1.45; padding: 8pt 10pt; margin: 6pt 0 10pt; white-space: pre-wrap; break-inside: avoid; }
  img { max-width: 100%; margin: 6pt 0 10pt; }
  a { text-decoration: none; color: var(--acc-text); word-break: break-word; }
  strong { font-weight: 550; }
`;

const build = join(docs, ".build");
mkdirSync(build, { recursive: true });
const browser = await chromium.launch({ channel: "chrome", headless: true });
try {
  const page = await browser.newPage();

  await page.goto(pathToFileURL(join(docs, "slides.html")).href);
  await page.evaluate(() => document.fonts.ready);
  await page.pdf({ path: join(docs, "Bagdar_Slides.pdf"), width: "1280px", height: "720px", printBackground: true });
  console.log("Bagdar_Slides.pdf");

  for (const [source, target] of PAGES) {
    let markdown;
    try { markdown = readFileSync(join(docs, source), "utf8"); } catch { console.log(`skipped ${source} (not found)`); continue; }
    markdown = markdown.replace(/```mermaid[\s\S]*?```/g, "![How the three algorithms are chained](../media/architecture.svg)")
      .replace(/\]\(media\//g, "](../media/");
    const html = `<!doctype html><html lang="en" data-theme="light"><head><meta charset="utf-8"><title>${target}</title>
      <link rel="stylesheet" href="../../web/kit.css"><style>${PRINT_CSS}</style></head><body>${marked.parse(markdown)}</body></html>`;
    const file = join(build, source.replace(".md", ".html"));
    writeFileSync(file, html);
    await page.goto(pathToFileURL(file).href);
    await page.evaluate(() => document.fonts.ready);
    await page.pdf({ path: join(docs, target), format: "A4", printBackground: true, preferCSSPageSize: true,
      displayHeaderFooter: true, headerTemplate: "<span></span>",
      footerTemplate: `<div style="width:100%;font:7pt Menlo,monospace;color:#777;padding:0 18mm;display:flex;justify-content:space-between"><span>bagdar · ${source.replace(".md", "").toLowerCase().replaceAll("_", " ")}</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>` });
    console.log(target);
  }
} finally {
  await browser.close();
  rmSync(build, { recursive: true, force: true });
}
