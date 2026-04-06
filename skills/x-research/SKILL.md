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

Before touching any browser tools, gather requirements with AskUserQuestion.
Keep the structured questions to **what actually changes the agent's behaviour**
— the rest is gathered as plain-text follow-ups so the user has full freedom.

```
AskUserQuestion({
  questions: [
    {
      question: "What kind of seed(s) are you starting from? (you'll provide the actual values next — and you can combine multiple kinds)",
      header: "Seed type",
      multiSelect: true,
      options: [
        { label: "Hashtag(s)",      description: "Scan everything under one or more hashtags" },
        { label: "Account(s)",      description: "Mine specific X handles for posts on a topic" },
        { label: "Tweet URL(s)",    description: "Deep-read specific tweets including thread, replies, quoted tweets" },
        { label: "Search query",    description: "Free-form X search syntax with operators (from:, lang:, since:, etc.)" }
      ]
    },
    {
      question: "How aggressively should the agent expand from each seed?",
      header: "Expansion",
      multiSelect: false,
      options: [
        { label: "Tight",         description: "Only the seed posts themselves — no following links" },
        { label: "Standard (Recommended)", description: "Follow quoted tweets and top replies on each high-signal post" },
        { label: "Aggressive",    description: "Also profile each high-signal author and read their related recent posts" },
        { label: "Exhaustive",    description: "Also follow external links (websites, repos, blogs, products linked in tweets)" }
      ]
    },
    {
      question: "What output format do you want?",
      header: "Output",
      multiSelect: false,
      options: [
        { label: "Index + interlinked raw (Recommended)", description: "research/{topic}/index.md as a navigation hub + raw/{handle}-{id}.md per tweet, with wikilink-style cross-references" },
        { label: "Raw dump only",  description: "One flat file with every source captured, no synthesis" },
        { label: "Synthesis only", description: "A single insights.md with patterns and conclusions, no raw archive" },
        { label: "Index + raw + synthesis", description: "All of the above — full research artefact" }
      ]
    }
  ]
})
```

**Then, in plain text, ask the user two follow-ups (no AskUserQuestion):**

1. **Concrete seed values** — "OK, give me the actual hashtag / handles / tweet URLs / search query you want to start from."
2. **Research question** — "What specifically are you trying to learn? The more concrete the question, the better the research. Examples: *'What are devs complaining about with Cursor's pricing?'*, *'Which AI agent frameworks are gaining traction this month?'*, *'Map the range of opinions on shipping AI features without evals.'*"

The research question is the **most important input** — it shapes signal scoring,
checkpoint priorities, and synthesis. Do not skip it. If the user doesn't give
one, ask again.

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

  // External links (websites, repos, products, etc.)
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
| Contains embedded video (demo, talk, etc.)    | High   | `videoPosters` array non-empty                      |
| Directly answers the user's research question | High   | Keyword match against the research question text    |
| Contains a live URL (.com, .io, .me, .app)    | Medium | `externalLinks` array non-empty                     |
| Technical content (tips, bullets, code)       | Medium | Keywords: "tip", "trick", "learned", "→", numbered |
| Zero engagement, <50 views                    | Low    | Skip unless author is known-high-signal             |
| Pure promotional, no content                  | Low    | Skip                                                |
| AI-generated reply (see heuristics below)     | Low    | Skip — these are noise                              |

Rank items. Deep-read High first, Medium if depth budget allows.

### Reply scoring (within a thread)

Replies have their own signal hierarchy. When deep-reading a thread, score
each reply individually:

```javascript
// For each reply article, extract engagement
const replyMetrics = Array.from(document.querySelectorAll('article')).map(a => {
  const text = a.innerText.replace(/\n+/g, ' ').trim();
  // Engagement numbers are at the end of the article text
  // Pattern: "{replies} {reposts} {likes} {bookmarks} {views}"
  const numbers = text.match(/(\d+(?:\.\d+)?[KM]?)\s*$/g);
  const handle = a.querySelector('[data-testid="User-Name"] a')?.href?.split('/').pop();
  return { handle, text: text.substring(0, 400), numbers };
});
JSON.stringify(replyMetrics);
```

For replies, prioritise by:
1. **Engagement ratio relative to the original tweet** — a reply with 50 likes
   on a tweet with 200 views is high signal; same reply on a 200K-view tweet
   is medium signal
2. **Length & specificity** — replies that quote or paraphrase the original
   are higher signal than generic agreement
3. **Pushback / disagreement** — corrections often contain the real signal
4. **Replies that themselves got replies** — conversation depth is signal

### AI-generated reply detection (filter out)

AI-generated replies are pure noise. They inflate engagement counts but
contribute nothing. Filter aggressively. Heuristics:

| Tell | Example |
|------|---------|
| Generic affirmation with no specifics | "Great point!", "Absolutely!", "100% this", "Couldn't agree more" |
| Em-dash–heavy "thoughtful" sentences | "It's not just X — it's Y. And that's powerful." |
| Reframes the original tweet as a "key insight" | "The real insight here is that..." (no new content) |
| Bullet-list reply on a non-list parent tweet | 3-bullet "key takeaways" structure |
| Marketing-speak vocabulary | "leverage", "unlock", "elevate", "game-changer", "supercharge", "synergy" |
| Excessive emoji punctuation | 🚀🔥💯 at end of every line |
| Account is unverified, < 6 months old, low follower count | Check the @handle profile briefly if in doubt |
| Reply doesn't reference any specific noun or number from the parent tweet | Generic reaction, not engagement |
| Uses "this 👇" or "saving this" with nothing else | Bookmark farming |

JS heuristic to flag suspect replies:

```javascript
const aiPhrases = [
  /great point/i, /absolutely/i, /100%/i, /couldn'?t agree/i,
  /the real insight/i, /key takeaway/i, /this is everything/i,
  /game.?changer/i, /supercharge/i, /unlock/i, /leverage/i,
  /this 👇/i, /saving this/i, /worth the read/i
];
const looksAI = (text) => aiPhrases.some(p => p.test(text)) ||
                          (text.length < 50 && /[🚀🔥💯✨]/.test(text)) ||
                          (text.match(/—/g) || []).length >= 2;
```

When a reply matches 2+ heuristics, treat as Low signal and skip.

When in doubt, click through to the replier's profile — if they have < 200
followers and reply to many big accounts with similar generic comments,
they're a bot or engagement farmer.

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
- Any text labels (product name, instructions, menus, captions)

### 4f. Video — full download + frame analysis (exhaustive depth only)

Poster thumbnails show one frame. Frame analysis reveals on-screen mechanics,
character/UI behaviour, dialogue, interactions, and state changes over time —
things no static thumbnail can show.

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

**Step 4 — Extract frames.**

The right approach depends on video length:

**Short clips (< 30s) — fixed-rate sampling:**
```bash
mkdir -p /tmp/xresearch_frames
ffmpeg -y -i /tmp/xresearch_video.mp4 \
  -vf "fps=1" \
  /tmp/xresearch_frames/frame_%04d.jpg
```

For very short clips (< 15s) bump to `fps=2`.

**Long clips (> 30s) — scene detection (recommended):**

ffmpeg has built-in scene change detection. This collapses 100+ frames
into the handful where something visually changed — typically a 20-30x
reduction with no loss of signal.

```bash
mkdir -p /tmp/xresearch_frames
ffmpeg -y -i /tmp/xresearch_video.mp4 \
  -vf "select='gt(scene,0.3)',showinfo" \
  -vsync vfr \
  /tmp/xresearch_frames/frame_%04d.jpg
```

Threshold tuning:
- `gt(scene,0.2)` — sensitive, captures small changes (e.g. UI updates, dialog appearing)
- `gt(scene,0.3)` — **default**, catches scene cuts and major content changes
- `gt(scene,0.4)` — strict, only major cuts
- `gt(scene,0.5)` — very strict, hard cuts only

**Tested result**: a 2:24 talking-head + screen recording video produced
**145 frames at fps=1** vs **7 frames at scene threshold 0.3** vs
**5 frames at threshold 0.4**. Each scene-detected frame was a distinct
new context (different app, different dialog, different topic on screen).

If scene detection returns too few frames (< 3), drop the threshold to 0.2.
If it returns too many (> 30), bump to 0.5.

**Always use scene detection for videos > 30s.** Reading 145 frames will
blow up Claude's context — reading 7 won't.

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
- **Events** — what changed since the last frame?
- **UI state** — buttons, dialog, status, captions, indicators
- **Character / actor behaviour** — did anyone speak, move, react?
- **Mechanics or workflows revealed** — what is the user doing on screen?
- **Visual quality** — production polish, design language, branding
- **Text overlays** — names, instructions, captions, code, links

**Step 6 — Audio transcription (when video has speech).**

Frame analysis shows what's *visible*. For videos with voiceover, narration,
or dialogue, you also need the audio. Use local Whisper — fast, free, no API.

When to use: any tweet where someone is talking on camera, doing a screen
recording with narration, explaining a product, or interviewing someone.
When to skip: silent demos, music-only videos, ambient footage.

Quick check first — does the video even have an audio stream?

```bash
ffprobe -v error -show_entries stream=codec_type,codec_name -of default=noprint_wrappers=1 /tmp/xresearch_av.mp4
```

If you see `codec_type=audio`, proceed. Note: the video file must come from
the **master M3U8 playlist** (`/pl/{hash}.m3u8?variant_version=...`), not the
video-only quality variant — the latter has no audio stream at all.

**Extract audio** as 16kHz mono MP3 (Whisper's preferred input):

```bash
ffmpeg -y -i /tmp/xresearch_av.mp4 \
  -vn -acodec libmp3lame -ar 16000 -ac 1 \
  /tmp/xresearch_audio.mp3
```

**Transcribe** with local Whisper:

```bash
whisper /tmp/xresearch_audio.mp3 \
  --model tiny \
  --output_dir /tmp/xresearch_transcript \
  --output_format txt \
  --language en
```

Model selection:
- `tiny` (~75MB) — fastest, good enough for clear speech, ~10x realtime on CPU
- `base` (~150MB) — better punctuation and proper-noun accuracy
- `small` (~500MB) — much better for accents, technical terms, multi-speaker
- `medium` (~1.5GB) — near-human quality, slower
- `large-v3` (~3GB) — best quality, only for critical content

For most research scans, `tiny` is enough. Bump to `small` if the speaker has
an accent, uses jargon, or the audio is noisy.

**Tested result**: 2:24 video transcribed by `tiny` in 26 seconds on CPU.
First run downloads the model (~1s on fast network). Output is a clean `.txt`
file with `[start --> end]` timestamps per line.

Read the transcript:

```
Read("/tmp/xresearch_transcript/xresearch_audio.txt")
```

What audio reveals that frames don't:
- **The "why"** — the speaker's motivation and intent
- **Architecture explanations** — how things work behind the UI
- **Plans / asks** — "I might make this a product next week, DM me"
- **Hesitations and corrections** — signal of authenticity vs scripted demo
- **Names and references** — products, people, tweets, citations the speaker mentions

**Multimodal cross-correction**: read frames AND transcript together. They
correct each other's failure modes:
- Whisper mishears proper nouns (e.g. "Pharsa Pedia" instead of "Farzapedia")
  → frames show the actual product name in the UI
- Frames show UI but not the speaker's intent
  → audio explains what they're trying to do
- Frames show a tool / library being used
  → audio explains why they chose it and what they tried before

**Step 7 — Clean up between videos.**

```bash
rm -rf /tmp/xresearch_frames /tmp/xresearch_video.mp4 \
       /tmp/xresearch_av.mp4 /tmp/xresearch_audio.mp3 \
       /tmp/xresearch_transcript
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

Output is a self-contained, interlinked research artefact — never a single
flat file. Structure:

```
research/{topic-slug}-{YYYY-MM-DD}/
├── index.md                    # navigation hub + link graph
├── raw/
│   ├── {handle}-{tweet-id}.md  # one file per source tweet
│   ├── {handle}-{tweet-id}.md
│   └── ...
├── transcripts/                # whisper outputs (if audio)
│   └── {handle}-{tweet-id}.txt
├── frames/                     # extracted video frames (if any)
│   └── {handle}-{tweet-id}/
│       ├── frame_0001.jpg
│       └── ...
└── insights.md                 # synthesis (if requested in Phase 0)
```

### `index.md` — the navigation hub

**This is the most important file.** It's not just a list of sources — it
encodes the *web-link structure* of the research so the reader can follow
the conversation graph.

Structure:

```markdown
# [Topic] Research
*Generated: YYYY-MM-DD HH:MM*
*Research question: [the user's actual question]*
*Seeds: [list of starting points]*
*Expansion: [tight / standard / aggressive / exhaustive]*

## Quick stats
- {N} source tweets captured
- {N} unique authors
- {N} videos analyzed (frames + transcripts)
- {N} external links followed
- {N} AI-generated replies filtered out

## Source index
*(by author, alphabetical)*

- **@handle1** ({N} posts)
  - [{date} — first 60 chars of tweet text](raw/handle1-12345.md)
  - [{date} — first 60 chars](raw/handle1-67890.md)
- **@handle2** ({N} posts)
  - ...

## Conversation graph
*(who quotes / replies to whom — the conversation as a tree)*

```text
@handle1 (raw/handle1-12345.md)
├── quotes → @handle2 (raw/handle2-99999.md)
│   └── replied by @handle3 (raw/handle3-11111.md)
└── replied by @handle4 (raw/handle4-22222.md)

@handle5 (raw/handle5-33333.md)
└── quotes → @handle1 (raw/handle1-12345.md)
```

## Topic clusters
*(group related sources by sub-theme)*

### [Sub-theme 1]
- [@handle1 on X](raw/handle1-12345.md)
- [@handle3 on X](raw/handle3-11111.md)

### [Sub-theme 2]
- ...

## External link map
*(every external URL referenced in any source, with which sources reference it)*

| URL | Referenced by |
|-----|---------------|
| https://example.com/post | [@handle1](raw/handle1-12345.md), [@handle4](raw/handle4-22222.md) |

## Author map
*(brief profile note per author — handle, follower context, why they matter)*

- **@handle1** — [bio snippet] — [why they're high signal in this research]
```

### Per-source files: `raw/{handle}-{tweet-id}.md`

Each tweet gets its own file. Use frontmatter for structured metadata, then
the body has full content + interlinks to other sources in the same research.

```markdown
---
handle: handle1
tweet_id: 12345
url: https://x.com/handle1/status/12345
date: 2026-04-06T15:30:00Z
likes: 320
reposts: 20
replies: 51
views: 148700
ratio: 0.215
has_video: true
captured: 2026-04-07T00:30:00Z
---

# @handle1 — 2026-04-06

> Full tweet text here. Verbatim. No summarising.
> Including line breaks
> And formatting.

## Quoted tweet
- **From**: [@handle2](handle2-99999.md) *(in this research)*
- **Date**: 2026-04-03
- **Text**: > [full text of the quoted tweet]

## Replies (high-signal only — AI-replies filtered)

### [@handle3](handle3-11111.md) — 32 likes / 5K views
> [full reply text]

### @handle_external — 18 likes / 2K views *(not in this research — original-only)*
> [full reply text]

## Video analysis
- **Source**: amplify_video/{video_id}
- **Duration**: 23.4s
- **Frames**: see [frames/handle1-12345/](../frames/handle1-12345/) — N keyframes via scene detection
- **Transcript**: see [transcripts/handle1-12345.txt](../transcripts/handle1-12345.txt)
- **Key visual content**: [1-2 sentence summary of what frames showed]
- **Key audio content**: [1-2 sentence summary of what was said]

## External links
- [domain.com/path](https://domain.com/path) — [why it was linked / what it is]
- ...

## Cross-references in this research
*(other source files in this research that reference, are referenced by, or relate to this one)*
- Quoted by: [@handle5](handle5-33333.md)
- Replied to by: [@handle3](handle3-11111.md), [@handle4](handle4-22222.md)
- Same topic: [@handle7](handle7-55555.md)
```

**Interlinking rules**:
- Every author handle should link to their source file *if it exists in the research*
- Every quoted tweet should link to its source file *if it exists in the research*
- Every reply that became a separate source should link to its file
- For sources NOT captured in this research, just include the X URL — don't fake a local link

### Optional: `insights.md`

Only created if the user chose "synthesis" or "all" in Phase 0.

```markdown
# [Topic] — Insights

*Research question: [the user's question]*

## TL;DR
[3-5 sentences answering the research question directly]

## Recurring themes
[what claims / pain points / ideas appeared in multiple sources]

## High-signal accounts
[2-5 handles + why each is worth following on this topic, with links to their sources in the research]

## Key claims & facts
[specific verifiable assertions, each with attribution to a source file]

## Opposing views / pushback
[disagreements found in replies — captured even if minority view]

## Gaps — what is NOT being discussed
[angles, questions, or approaches absent from the conversation]

## Non-obvious observations
[3–7 things you'd only know from reading the whole field together, not visible in any single source]
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
