---
name: x-research
description: >
  Deep intelligence gathering from X (Twitter). Use when asked to research a
  topic on X, analyze a tweet thread, scan a hashtag, profile a community,
  or gather competitive intelligence from social signals.
  Invokes AskUserQuestion to clarify scope, then runs a systematic
  multi-pass research loop: discovery → signal filtering → deep read →
  video download & frame analysis → documentation → checkpoint with user.
---

# X Research Skill

Systematic, non-skimming intelligence gathering from X/Twitter. Produces a
structured markdown document with raw sources and synthesised insights.

**This skill is rigid.** Follow every phase in order. Never skim. Never
summarise from a single pass. Keep looping until the user says stop.

---

## Phase 0 — Requirements Intake

Before touching any browser tools, use AskUserQuestion:

```
AskUserQuestion({
  questions: [
    {
      question: "What is the seed for this research?",
      header: "Seed",
      multiSelect: false,
      options: [
        { label: "Tweet URL",      description: "Start from a specific tweet and read its full thread + replies" },
        { label: "Hashtag",        description: "Scan everything under a hashtag (#vibejam, #buildinpublic…)" },
        { label: "Search query",   description: "Full X search syntax: from:user, since:date, keyword" },
        { label: "Account",        description: "Mine a specific user's recent posts" }
      ]
    },
    {
      question: "What is the research goal?",
      header: "Goal",
      multiSelect: false,
      options: [
        { label: "Competitive intel",  description: "What are others building / shipping / saying?" },
        { label: "Thread deep-dive",   description: "Extract everything of value from one thread + its context" },
        { label: "Community scan",     description: "Map the landscape: who's active, what topics dominate" },
        { label: "Signal extraction",  description: "Find the highest-value posts in a noisy feed" }
      ]
    },
    {
      question: "How deep should the research go?",
      header: "Depth",
      multiSelect: false,
      options: [
        { label: "Quick scan (Recommended)", description: "Top 10–15 signal posts, poster thumbnails only, ~10 min" },
        { label: "Standard",                 description: "20–30 posts, follow quoted tweets, check author profiles, poster thumbnails" },
        { label: "Exhaustive",               description: "Everything: full threads, quoted tweets, author histories, download videos + frame analysis" }
      ]
    }
  ]
})
```

After answers: if seed is not a full URL/query, ask for it before proceeding.

---

## Phase 1 — Browser Setup

Load all tools upfront so they're ready:

```
ToolSearch("select:mcp__claude-in-chrome__tabs_context_mcp")
ToolSearch("select:mcp__claude-in-chrome__navigate")
ToolSearch("select:mcp__claude-in-chrome__javascript_tool")
ToolSearch("select:mcp__claude-in-chrome__computer")
ToolSearch("select:mcp__claude-in-chrome__get_page_text")
ToolSearch("select:mcp__claude-in-chrome__read_network_requests")

mcp__claude-in-chrome__tabs_context_mcp({ createIfEmpty: true })
```

**Rule**: always use the MCP tab group. Never navigate a user's existing tab
without confirmation. Create a new tab if in doubt.

---

## Phase 2 — Discovery

### 2a. Navigate to seed

| Seed type     | URL                                                               |
|---------------|-------------------------------------------------------------------|
| Tweet URL     | Navigate directly                                                 |
| Hashtag       | `https://x.com/search?q=%23{tag}&src=typed_query&f=live`        |
| Hashtag (Top) | `https://x.com/search?q=%23{tag}&src=typed_query&f=top`         |
| Search        | `https://x.com/search?q={encoded}&src=typed_query&f=live`       |
| Date-bounded  | append `+since%3AYYYY-MM-DD+until%3AYYYY-MM-DD` to search URL   |
| From user     | append `+from%3A{username}` to search URL                        |
| Profile       | `https://x.com/{username}`                                        |

### 2b. Anti-autoplay — MANDATORY after every single navigation

Run this JS immediately, before any screenshot or scroll:

```javascript
document.querySelectorAll('video').forEach(v => {
  v.pause();
  v.autoplay = false;
  v.muted = true;
});
// Returns count so you know it ran
`Paused ${document.querySelectorAll('video').length} videos`;
```

**CRITICAL — do NOT `.remove()` videos from the DOM.** Removing videos
breaks the X page layout and stops new content from lazy-loading.
Only pause + mute.

### 2c. Full-page article scrape

```javascript
document.querySelectorAll('video').forEach(v => { v.pause(); v.autoplay = false; });

const articles = document.querySelectorAll('article');
const tweets = Array.from(articles).map((a, i) => {
  const text = a.innerText.replace(/\n+/g, ' ').trim();

  // Status links = tweet links (exclude analytics)
  const links = Array.from(a.querySelectorAll('a[href*="/status/"]'))
    .map(l => l.href)
    .filter(l => !l.includes('/analytics') && !l.includes('/photo/'))
    .slice(0, 4);

  // Video poster thumbnails (first frame previews)
  const videoPosters = Array.from(a.querySelectorAll('video'))
    .map(v => v.poster)
    .filter(Boolean);

  // External links (game URLs, github, etc.)
  const externalLinks = Array.from(a.querySelectorAll('a[href^="https://t.co"]'))
    .map(l => l.textContent.trim())
    .filter(Boolean);

  return { i, text: text.substring(0, 900), links, videoPosters, externalLinks };
});

JSON.stringify(tweets);
```

**Note on `[BLOCKED: Cookie/query string data]` error**: this fires when you
return raw DOM content that X embeds cookies/tokens into. Always return
structured JS objects — never return `document.innerText` or `document.body.innerHTML` raw.

### 2d. Load more content (lazy load loop)

```javascript
document.querySelectorAll('video').forEach(v => { v.pause(); v.autoplay = false; });
window.scrollTo(0, document.body.scrollHeight);
`height: ${document.body.scrollHeight} | articles: ${document.querySelectorAll('article').length}`;
```

Run → wait 3 seconds → re-scrape. Repeat until article count stops growing.
Stop after 5 cycles to avoid infinite scroll traps.

---

## Phase 3 — Signal Filtering

Score every scraped tweet before deciding what to deep-read.

### Scoring table

| Signal                                        | Weight | Detection                                           |
|-----------------------------------------------|--------|-----------------------------------------------------|
| Engagement ratio (likes ÷ views) > 1%         | High   | Parse numbers from article text                     |
| Quoted by a high-follower or verified account | High   | "Quote" block present in article text               |
| Has both replies AND likes                    | High   | Reply count > 0 AND likes > 5                       |
| Contains embedded video (game demo)           | High   | `videoPosters` array non-empty                      |
| Posted by the seed author themselves          | High   | Username match                                      |
| Contains a live URL (.com, .io, .me, .app)    | Medium | `externalLinks` array non-empty                     |
| Technical content (tips, bullets, code)       | Medium | Keywords: "tip", "trick", "learned", "→", numbered |
| Zero engagement, <50 views                    | Low    | Skip unless author is known-high-signal             |
| Pure promotional, no content                  | Low    | Skip                                                |

Rank items. Deep-read High first, Medium if depth budget allows.

---

## Phase 4 — Deep Read Protocol

For each high-signal tweet, execute all applicable sub-phases below.

### 4a. Full thread read

1. Navigate to the tweet's own URL (not a search result listing)
2. Run anti-autoplay JS
3. Scrape all `article` elements — ALL of them, not just the top tweet
4. Scroll to load replies → wait 3s → re-scrape → repeat until stable
5. Extract: main tweet, every reply, every quoted tweet preview visible

### 4b. Follow quoted tweets

Every "Quote" block is a breadcrumb. The author thought this was important
enough to amplify — that makes it high-signal by definition.

1. Extract the quoted tweet URL from the article's link list
2. Navigate to it
3. Full thread read as per 4a
4. Log what the original author found remarkable about it

### 4c. Top replies

1. After full thread scrape, identify replies with the most engagement
2. Read them completely — corrections, pushback, and "+1 with more info" are
   often where the real signal lives
3. Note any disagreements or corrections to the original tweet

### 4d. Author profile sweep

1. Navigate to `https://x.com/{username}`
2. Anti-autoplay JS
3. Scrape visible posts → filter for topic-relevant ones
4. Check the pinned post — often the most important thing they've said
5. Look for posts that aren't in the hashtag feed (related but not tagged)

### 4e. Video — poster thumbnail (fast path)

For quick/standard depth: read the poster image without playing the video.

**Step 1**: Extract poster URLs from JS:
```javascript
const posters = Array.from(document.querySelectorAll('video'))
  .map(v => ({ poster: v.poster, currentSrc: v.currentSrc }))
  .filter(v => v.poster);
JSON.stringify(posters);
```

**Step 2**: Navigate directly to the poster URL:
```
https://pbs.twimg.com/amplify_video_thumb/{VIDEO_ID}/img/{HASH}.jpg
```
The VIDEO_ID is the large number in the poster URL path. Take a screenshot
after navigating — Claude can read the image directly.

**What to extract from poster image:**
- Game genre (shooter, city-builder, puzzle, racing…)
- Visual fidelity (3D/2D, shaders, particle effects, lighting)
- HUD/UI elements visible (health bar, minimap, inventory)
- Number of visible players/characters
- Overall polish level
- Any text labels (game name, instructions, menus)

### 4f. Video — full download + frame analysis (exhaustive depth only)

Poster thumbnails show one frame. Frame analysis reveals gameplay mechanics,
NPC behaviour, dialogue, multiplayer interactions, UI state changes — things
no static thumbnail can show.

**This entire pipeline has been tested end-to-end. Follow it exactly.**

**Step 1 — Capture video URLs from network traffic.**

X uses MSE (Media Source Extensions): the `<video>` element's `src` is
always a `blob:` URL, and the Performance API will NOT show the underlying
streams. You MUST use `read_network_requests` to get the real URLs.

**Critical**: enable network tracking BEFORE the video segments load.
Workflow:

1. Navigate to the tweet URL (this starts network tracking automatically on first call)
2. Call `read_network_requests({ tabId, clear: true })` to clear baseline
3. Reload the page so segments fetch fresh: `javascript_tool` with `location.reload(); 'reloading'`
4. Wait 4 seconds for the page + video segments to load
5. Run anti-autoplay JS
6. Call `read_network_requests({ tabId, urlPattern: "video.twimg.com" })`

X auto-prefetches video segments for autoplay, so the URLs are captured even
without clicking play.

**Step 2 — Identify the right URL.**

The network capture returns many URLs per video. Pattern guide:

| URL pattern | What it is | Use? |
|-------------|-----------|------|
| `/pl/{hash}.m3u8?variant_version=...` | Master playlist (multi-bitrate) | Yes if no quality variants visible |
| `/pl/avc1/1920x1080/{hash}.m3u8` | 1080p video-only playlist | **Best — use this** |
| `/pl/avc1/480x270/{hash}.m3u8` | 270p video playlist | Fallback for low bandwidth |
| `/pl/mp4a/128000/{hash}.m3u8` | Audio-only playlist | Skip (handled by master) |
| `/vid/avc1/{start}/{end}/{res}/{hash}.m4s` | Individual video segment | Skip |
| `/vid/avc1/0/0/{res}/{hash}.mp4` | **MP4 init segment ONLY (~900 bytes)** | **DO NOT use — not the full video** |
| `/aud/mp4a/.../{hash}.m4s` or `.mp4` | Audio segments / init | Skip |

**Each tweet video has a unique numeric ID** (e.g. `2040901888518782976`).
Match URLs to videos by this ID. The poster URL contains the same ID.

**The 1080p `.m3u8` playlist is the right URL.** It tells ffmpeg how to
assemble all the segments into a single video.

**Step 3 — Download and assemble with ffmpeg.**

Do NOT use `curl` directly on `.m3u8` files (they're playlists, not video).
Do NOT use the `0/0/` MP4 URLs (they're init-only, ~900 bytes).
Use ffmpeg with the M3U8 playlist URL:

```bash
ffmpeg -y \
  -headers $'Referer: https://x.com/\r\nOrigin: https://x.com\r\nUser-Agent: Mozilla/5.0\r\n' \
  -i "https://video.twimg.com/amplify_video/{VIDEO_ID}/pl/avc1/1920x1080/{HASH}.m3u8" \
  -c copy \
  /tmp/xresearch_video.mp4
```

Notes:
- `-headers` uses `\r\n` to separate header lines (use `$'...'` syntax for
  bash escape interpretation)
- `-c copy` copies streams without re-encoding (fast, preserves quality)
- Output is video-only since we used the video-only playlist. If you need
  audio, use the master `.m3u8?variant_version=...` URL instead

**Tested result**: assembles a 23-second 1080p video from ~12 segments in
under 1 second. Output ~2.7MB, 1404 frames at 60fps.

**Step 4 — Extract frames at 1 fps.**

```bash
mkdir -p /tmp/xresearch_frames
ffmpeg -y -i /tmp/xresearch_video.mp4 \
  -vf "fps=1" \
  /tmp/xresearch_frames/frame_%04d.jpg
ls /tmp/xresearch_frames/
```

For short clips (< 15s) where you want more granularity, use `fps=2`.
For long clips where you want a sparse overview, use `fps=0.5`.

**Step 5 — Read frames as images.**

Claude is multimodal — the `Read` tool returns JPEG files as visible images.
Read 3-5 frames spaced across the video:

```
Read("/tmp/xresearch_frames/frame_0001.jpg")  # opening
Read("/tmp/xresearch_frames/frame_0008.jpg")  # ~1/3
Read("/tmp/xresearch_frames/frame_0015.jpg")  # ~2/3
Read("/tmp/xresearch_frames/frame_0022.jpg")  # ending
```

For each frame, extract:
- **Gameplay events** — what changed since the last frame?
- **UI state** — health, ammo, score, dialogue, menus
- **NPC behaviour** — did an NPC react, speak, move?
- **Mechanics revealed** — combat? dialogue? building? exploration?
- **Visual quality** — geometry, lighting, shadows, effects
- **Text overlays** — character names, instructions, scores

**Step 6 — Clean up between videos.**

```bash
rm -rf /tmp/xresearch_frames /tmp/xresearch_video.mp4
```

---

## Phase 5 — Checkpoint with User

After each discovery + deep-read cycle, STOP and surface findings.
Build the AskUserQuestion options from the **actual findings** — never
use generic placeholder text.

Build options from the **actual findings**. Example:

```
AskUserQuestion({
  questions: [
    {
      question: "Found [N] high-signal posts on [topic]. [One-line summary of top finding]. What next?",
      header: "Direction",
      multiSelect: false,
      options: [
        { label: "Deep-dive [specific finding]",  description: "Download video / follow thread further" },
        { label: "Scan more on [related angle]",  description: "Widen the search to [related query]" },
        { label: "Profile @[high-signal author]", description: "Read all their recent posts on this topic" },
        { label: "Synthesise now",                description: "Stop gathering, write up full insights doc" }
      ]
    }
  ]
})
```

Never present generic placeholder options — every option must reflect a real
finding from the current session.

---

## Phase 6 — Documentation

**File**: `research/{topic}-{YYYY-MM-DD}.md`
Append to existing file if it exists. Never overwrite.

### Structure

```markdown
# [Topic] Research
*Session: YYYY-MM-DD HH:MM*
*Seed: [URL or query]*
*Goal: [stated goal]*

---

## Raw Sources

### @handle — [date] — [tweet URL]
- **Engagement**: {likes} likes / {views} views ({ratio:.1f}% ratio)
- **Full text**: [complete tweet text, not summarised]
- **Quoted tweet**: [URL + full text if followed]
- **Video**: [poster description OR frame-by-frame analysis if downloaded]
- **Key replies**:
  - @replier: [reply text]
- **External links**: [URLs, repos, products mentioned]

[repeat per source — one entry per tweet, no skipping]

---

## Signal Summary

### Recurring themes
[what topics / ideas / claims keep appearing across multiple accounts]

### High-signal accounts (and why)
[handles + why they're worth following on this topic]

### Key claims & facts
[specific assertions made — with attribution so they can be verified]

### Opposing views / pushback
[disagreements, corrections, contrarian takes found in replies]

### Gaps — what is NOT being discussed
[angles, questions, or approaches absent from the conversation]

---

## Insights

[3–7 non-obvious synthesised observations — things you'd only know from
reading the whole field together, not visible in any single tweet]
```

---

## Phase 7 — Continuation Loop

Loop back to Phase 2 after every checkpoint unless user chooses "synthesise".

Maintain a running de-duplication list:
- Already-visited tweet URLs
- Already-profiled authors
- Already-followed quoted tweets

Flag to the user when the feed is starting to repeat known content.

---

## Known Gotchas

All of these were observed and confirmed during testing.

| Symptom | Cause | Fix |
|---------|-------|-----|
| Screen goes black on scroll | Video autoplayed fullscreen | Press Escape → immediately run anti-autoplay JS |
| `scrollHeight` stops growing | Content loaded, or page broke | Re-navigate to URL fresh |
| Only 1–3 articles visible | Page still loading | Wait 5s, re-check |
| `[BLOCKED: Cookie/query string data]` | Returned raw DOM text with embedded tokens | Return structured JS objects only — never raw `innerHTML`/`innerText` of `body` |
| Removing videos breaks layout | DOM tree dependency | Never `.remove()` — only `.pause()` + `.autoplay = false` |
| `performance.getEntriesByType('resource')` returns no video URLs | X uses MSE (blob: URLs); Performance API doesn't see the underlying segment fetches | Use `read_network_requests({ urlPattern: "video.twimg.com" })` instead |
| `<video>.src` is `blob:https://x.com/...` | Expected — that's the MSE blob | Don't try to download the blob URL. Use `read_network_requests` |
| curl download returns 904 bytes | Used the `0/0/{res}/.mp4` URL — that's the init segment, not the full file | Use the M3U8 playlist URL with ffmpeg instead |
| curl download returns 403 | Missing auth headers | Add `-H "Referer: https://x.com/"` and User-Agent |
| ffmpeg `Server returned 403` on M3U8 | Headers not passed to segment fetches | Use `-headers $'Referer: https://x.com/\r\nOrigin: https://x.com\r\nUser-Agent: Mozilla/5.0\r\n'` (note `\r\n` and `$'...'` bash syntax) |
| Network requests empty after navigation | Tracking starts on first call to `read_network_requests` | Call once with `clear: true`, then `location.reload()`, wait, then read again |
| Thread replies not loading | Wrong URL (search result vs tweet URL) | Navigate to direct tweet URL: `https://x.com/{user}/status/{id}` |
| Quoted tweet content truncated | Inline preview only shows part | Navigate to the quoted tweet's own URL |
| Search `from:user` not working | Operator not supported in `f=live` for some accounts | Use `https://x.com/search?q=...&f=top` or Advanced Search |
| Video has no audio after ffmpeg `-c copy` | Used video-only playlist (`/pl/avc1/1920x1080/...`) | Use the master playlist (`/pl/{hash}.m3u8?variant_version=...`) which includes audio |

---

## Alternative: Chrome CDP / Puppeteer backend

This skill is written for the [`claude-in-chrome`](https://github.com/anthropics/claude-in-chrome) MCP server, but the same techniques work with any Chromium-driven backend. The mappings:

| claude-in-chrome tool | chrome-cdp equivalent | Puppeteer equivalent |
|-----------------------|-----------------------|----------------------|
| `mcp__claude-in-chrome__navigate` | `cdp.mjs nav <target> <url>` | `page.goto(url)` |
| `mcp__claude-in-chrome__javascript_tool` | `cdp.mjs eval <target> <expr>` | `page.evaluate(fn)` |
| `mcp__claude-in-chrome__read_network_requests` | `cdp.mjs net <target>` (resource timing) — see note below | `page.on('request', ...)` |
| `mcp__claude-in-chrome__computer` (screenshot) | `cdp.mjs shot <target> <file>` | `page.screenshot()` |
| `mcp__claude-in-chrome__get_page_text` | `cdp.mjs eval <target> 'document.body.innerText'` | `page.evaluate(() => document.body.innerText)` |

**Network requests with chrome-cdp**: the `net` command returns Performance API
resource timing entries — which, as we learned, will NOT include MSE-streamed
video segments. To capture X video URLs via CDP, you need to enable the
`Network` domain and listen to `Network.requestWillBeSent` events directly.
The chrome-cdp `evalraw` escape hatch lets you do this:

```bash
# Enable Network domain
cdp.mjs evalraw <target> Network.enable

# Then use a separate listener mechanism — chrome-cdp doesn't have a built-in
# request log, so consider using puppeteer for video URL capture, or extend
# chrome-cdp with a `cdp.mjs netlog <target>` command.
```

**Recommendation**: for the video pipeline specifically, `claude-in-chrome`'s
built-in `read_network_requests` is the path of least resistance — it captures
all XHR/Fetch requests including the MSE segment fetches. If you must use
chrome-cdp or vanilla Puppeteer, set up a request listener before navigating.

**chrome-cdp repo**: https://github.com/seahyc/chrome-cdp *(replace with the actual repo URL once published)*
