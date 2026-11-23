# Brag plan: Bagdar

Made with the brag-slim rules (github.com/latent-spaces/brag): one short film, the real interface, its own soundtrack.

- **What it is:** a study tool that works like a GPS: it finds what you know, plans the shortest route to your exam and picks each next step.
- **Who it is for:** a student preparing for an exam.
- **What sets it apart:** every decision shows its numbers; nothing is a black box.
- **Hook:** "You scored 7 out of 10. Which 7 did you guess?" A score hides guesses; that is the whole problem in one line.
- **Tone:** polished. Calm, large type, long holds, soft dips through the background.
- **Visual identity:** the app's own stylesheets (web/kit.css, web/app.css): near-white ground, Source Serif 4 headings at weight 300, Medeo Mono labels, one purple accent (hue 305), the ruler motif.
- **Format:** landscape 1920x1080, 30 fps, 20 seconds.
- **Music:** 120 BPM, C major / A minor, synthesised in tools/brag/music.py. A beat is 0.5 s; every cut is on a beat.

| # | Time | Scene | On screen | Sound |
|---|---|---|---|---|
| 1 | 0-3 s | Hook | "You scored 7 out of 10." typed; "Which 7 did you guess?" lands on beat 3 | Pad only; a tick per character; a bell on the question |
| 2 | 3-6 s | Reveal | "A GPS for learning."; the ruler draws; the marker travels; locate, route, steer appear on beats | Kick and arpeggio enter |
| 3 | 6-10 s | Locate | "It knows what you really know."; a press on "Not sure"; the real belief bars move from 0.50/0.30/0.20 to 0.71/0.20/0.09 | Bass and hats enter |
| 4 | 10-14 s | Route | "It plans the shortest way."; the real skill map; 13 stops light up one per quarter second | Each stop is a note of the scale |
| 5 | 14-17 s | Steer | "It picks the next step."; lesson 3.77, question 3.64, move on -10.69; the mark lands on lesson | Bell when the mark lands |
| 6 | 17-20 s | Outro | "Bagdar. Know where you are. Get where you're going."; repository address | Resolve to C major, fade |

Every number on screen is produced by the engine for the same situation shown in the app (prior belief, one wrong and hesitant answer, the "Defense day" route). No personal data, secrets or invented claims appear.
