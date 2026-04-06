# x-research

A Claude Code plugin that gives your agent systematic, non-skimming intelligence
gathering from X (Twitter).

Born from a research session where naive scroll-and-skim kept getting hijacked
by autoplaying videos and lazy-loaded content. Every technique in this skill
was discovered the hard way. It works for any topic: game jams, product launches,
research communities, tech trends, founder spaces, competitive intel.

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

### Claude Code (plugin marketplace)
```bash
/plugin install x-research
```

### Manual (symlink method)
```bash
git clone https://github.com/YOUR_USERNAME/x-research ~/.claude/plugins/x-research
ln -s ~/.claude/plugins/x-research/skills/x-research ~/.claude/skills/x-research
```

## Usage

```
/x-research
```

Or trigger naturally — if you ask Claude to "research what's being built for #vibejam"
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
- Frame extraction at 1 fps: ✅ 23 frames produced
- `Read` tool on extracted frames: ✅ Claude reads each frame as an image and extracts NPC names, dialogue, HUD state, mechanics
- Local Whisper audio transcription: ✅ 2:24 talking-head video transcribed in 26s with `tiny` model on CPU; output included product name, architecture details, plans, even hesitations

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

- Game jam / hackathon competitive intel
- Product launch community reaction
- Academic / research field pulse
- Founder communities and trends
- Tech announcement analysis
- Political or cultural discourse mapping

## License

MIT
