# x-research

A Claude Code plugin that gives your agent systematic, non-skimming intelligence
gathering from X (Twitter).

Born from a research session where naive scroll-and-skim kept getting hijacked
by autoplaying videos and lazy-loaded content. Every technique in this skill
was discovered the hard way. It works for any topic: product launches,
research communities, tech trends, founder spaces, market intel, discourse mapping.

## What it does

Runs a structured multi-pass research loop:

1. **Intake** — asks you for seed (tweet URL / hashtag / search / profile), goal, and depth
2. **Discovery** — navigates X, scrapes all articles with engagement metrics + video posters
3. **Signal filtering** — scores each post by engagement ratio, quoted-by status, video presence
4. **Deep read** — full threads, quoted tweets, top replies, author profile sweeps
5. **Video analysis** — bypasses autoplay by navigating to poster thumbnail URLs directly
6. **Checkpoint** — pauses and asks you where to go next based on real findings
7. **Documentation** — writes structured markdown: raw sources + patterns + insights

## Installation

### Via [skills.sh](https://skills.sh) (Recommended — works on Claude Code, Cursor, Codex, Cline, Copilot, +41 more agents)

```bash
npx skills add seahyc/x-research
```

The Skills CLI auto-discovers `skills/x-research/SKILL.md` in this repo and installs it to whichever agent directory you're using (Claude Code's `~/.claude/skills/`, Cursor's, etc).

Optional flags:
```bash
npx skills add seahyc/x-research --global   # install to user dir, not project
npx skills add seahyc/x-research --copy     # copy files instead of symlinking
npx skills add seahyc/x-research --list     # preview what gets installed first
```

**Then install the runtime dependencies** (the Skills CLI handles the skill files, but ffmpeg + whisper are separate system tools):

```bash
# macOS
brew install ffmpeg openai-whisper

# Linux
sudo apt-get install ffmpeg
pip install openai-whisper
```

Or run our installer to handle dependency checks + a Chromium browser check:

```bash
git clone https://github.com/seahyc/x-research ~/Code/x-research
cd ~/Code/x-research && ./install.sh
```

### Manual installation (no Skills CLI)

```bash
# 1. Clone the repo
git clone https://github.com/seahyc/x-research ~/Code/x-research

# 2. Symlink the skill into Claude Code's skills directory
ln -s ~/Code/x-research/skills/x-research ~/.claude/skills/x-research

# 3. Install runtime deps (see above)
```

### Verifying the install

In Claude Code, ask: *"research what people are saying about [topic] on X"* — the skill should auto-invoke. Or explicitly: *"use the x-research skill"*.

## Usage

```
/x-research
```

Or trigger naturally — if you ask Claude to "research this topic on X"
or "deep-dive this thread", the skill auto-invokes.

## Requirements

- Claude Code (or any agent harness with a similar Skill mechanism)
- One of: `claude-in-chrome` MCP server **(recommended — has built-in `read_network_requests`)**, or [chrome-cdp](https://github.com/seahyc/chrome-cdp), or vanilla Puppeteer
- `ffmpeg` and `curl` on PATH (video download + frame extraction)
- `whisper` (OpenAI's local Whisper) for audio transcription — install via `pip install openai-whisper` or `brew install whisper-cpp`
- An active Chrome / Chromium / Brave / Edge / Arc browser session

## Tested

The full pipeline has been validated end-to-end:
- Anti-autoplay JS: ✅ paused 12 videos on a search page
- Article scrape with structured JS: ✅ avoided the `[BLOCKED]` error
- `read_network_requests` for video URL capture: ✅ captured 34+ video.twimg.com URLs without clicking play (X auto-prefetches)
- ffmpeg M3U8 download: ✅ assembled a 23s 1080p video in <1s, a 2:24 video in <4s
- Frame extraction at 1 fps: ✅ 23 frames from a 23s clip
- ffmpeg scene detection on long video: ✅ 2:24 video collapsed from 145 frames → 7 keyframes at threshold 0.3 (20x reduction, no signal loss)
- `Read` tool on extracted frames: ✅ Claude reads each frame as an image and extracts on-screen text, UI state, character names, dialogue, and visible context
- Local Whisper audio transcription: ✅ 2:24 talking-head video transcribed in 26s with `tiny` model on CPU; output included product name, architecture details, plans, even hesitations
- Multimodal cross-correction: ✅ frames corrected Whisper's "Pharsa Pedia" → actual UI showed "Farzapedia"

## Techniques codified

| Technique | Why it matters |
|-----------|---------------|
| Anti-autoplay JS | X videos fullscreen on scroll, making the screen go black |
| Poster URL navigation | View video content without triggering the player |
| Article JS scraping | Extract all tweet text + engagement in one pass |
| Scroll-and-wait loop | Trigger X's lazy loading to surface all content |
| Quoted tweet follow-through | Quoted tweets = what the author found remarkable = high signal |
| Engagement ratio scoring | Likes ÷ views > 1% filters noise from genuine signal |
| Author profile sweep | Finds related posts not visible in the hashtag feed |
| Local Whisper audio transcription | Captures the *why* behind videos — speaker intent, architecture details, asks, and references that no frame can show |
| Structured markdown output | Raw sources + synthesised insights, appendable across sessions |

## Works for any research domain

**Primary use case: founders doing user research** — deep-dive into what an
X community actually thinks about a topic, problem, product category, or pain
point. Surface unmet needs, complaints, workarounds, and feature requests
straight from the people you're trying to serve.

Other use cases:
- Product launch community reaction
- Academic / research field pulse
- Founder community trends and sentiment
- Tech announcement analysis
- Discourse mapping on a contentious topic
- Competitive intelligence on any topic

## License

MIT
