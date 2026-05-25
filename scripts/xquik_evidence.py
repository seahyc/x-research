#!/usr/bin/env python3
"""Collect secondary X evidence through Xquik read APIs."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "https://xquik.com"
DEFAULT_OUT_DIR = "research/x-evidence"
SEARCH_PATH = "/api/v1/x/tweets/search"


@dataclass(frozen=True)
class Config:
    api_key: str
    base_url: str


@dataclass(frozen=True)
class Metrics:
    replies: int | None
    reposts: int | None
    quotes: int | None
    likes: int | None
    views: int | None


@dataclass(frozen=True)
class TweetEvidence:
    query: str
    tweet_id: str
    author: str
    text: str
    url: str
    created_at: str
    metrics: Metrics


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key:
            values[key] = value
    return values


def get_config(
    env: dict[str, str] | None = None,
    dotenv: dict[str, str] | None = None,
) -> Config:
    env_values = env if env is not None else os.environ
    dotenv_values = dotenv if dotenv is not None else load_dotenv(repo_root() / ".env")
    return Config(
        api_key=env_values.get("XQUIK_API_KEY") or dotenv_values.get("XQUIK_API_KEY") or "",
        base_url=env_values.get("XQUIK_BASE_URL") or dotenv_values.get("XQUIK_BASE_URL") or DEFAULT_BASE_URL,
    )


def build_search_url(base_url: str, query: str, limit: int) -> str:
    root = (base_url or DEFAULT_BASE_URL).rstrip("/")
    return f"{root}{SEARCH_PATH}?{urlencode({'q': query, 'limit': str(limit)})}"


def build_headers(api_key: str) -> dict[str, str]:
    token = api_key.strip()
    headers = {"Accept": "application/json"}
    if token.lower().startswith("bearer "):
        headers["Authorization"] = token
    else:
        headers["x-api-key"] = token
    return headers


def fetch_json(url: str, headers: dict[str, str], timeout: int = 30) -> Any:
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")[:800]
        raise RuntimeError(f"HTTP {error.code}: {body}") from error
    except URLError as error:
        raise RuntimeError(f"Network error: {error.reason}") from error


def is_record(value: Any) -> bool:
    return isinstance(value, dict)


def first_string(record: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, (int, float)):
            return str(value)
    return ""


def first_number(record: dict[str, Any], keys: list[str]) -> int | None:
    for key in keys:
        value = record.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str) and value.strip():
            parsed = value.replace(",", "")
            try:
                return int(float(parsed))
            except ValueError:
                continue
    return None


def nested_record(record: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    for key in keys:
        value = record.get(key)
        if is_record(value):
            return value
    return {}


def metric_value(raw: dict[str, Any], metrics_record: dict[str, Any], keys: list[str]) -> int | None:
    direct = first_number(raw, keys)
    return direct if direct is not None else first_number(metrics_record, keys)


def clean_handle(value: str) -> str:
    return value.strip().lstrip("@")


def extract_tweet_list(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if not is_record(payload):
        return []

    for key in ("tweets", "items", "results", "posts"):
        value = payload.get(key)
        if isinstance(value, list):
            return value

    for key in ("data", "result", "response"):
        nested = extract_tweet_list(payload.get(key))
        if nested:
            return nested
    return []


def normalize_tweet(raw: Any, query: str) -> TweetEvidence | None:
    if not is_record(raw):
        return None

    author_record = nested_record(raw, ["author", "user", "creator"])
    metrics_record = nested_record(raw, ["metrics", "public_metrics", "stats"])
    tweet_id = first_string(raw, ["id", "id_str", "tweet_id", "tweetId", "rest_id"])
    text = first_string(raw, ["text", "full_text", "content", "body"])
    if not text:
        return None

    author = clean_handle(
        first_string(raw, ["username", "screen_name", "handle", "author_username"])
        or first_string(author_record, ["username", "screen_name", "handle", "name"])
    )
    url = first_string(raw, ["url", "tweet_url", "permalink"])
    if not url and tweet_id:
        url = f"https://x.com/{author}/status/{tweet_id}" if author else f"https://x.com/i/web/status/{tweet_id}"

    return TweetEvidence(
        query=query,
        tweet_id=tweet_id,
        author=f"@{author}" if author else "",
        text=text,
        url=url,
        created_at=first_string(raw, ["created_at", "createdAt", "date", "time"]),
        metrics=Metrics(
            replies=metric_value(raw, metrics_record, ["reply_count", "replies"]),
            reposts=metric_value(raw, metrics_record, ["retweet_count", "repost_count", "retweets", "reposts"]),
            quotes=metric_value(raw, metrics_record, ["quote_count", "quotes"]),
            likes=metric_value(raw, metrics_record, ["like_count", "favorite_count", "likes", "favorites"]),
            views=metric_value(raw, metrics_record, ["view_count", "views", "impression_count", "impressions"]),
        ),
    )


def metric_text(metrics: Metrics) -> str:
    values = [
        ("replies", metrics.replies),
        ("reposts", metrics.reposts),
        ("quotes", metrics.quotes),
        ("likes", metrics.likes),
        ("views", metrics.views),
    ]
    return " ".join(f"{label}:{value}" for label, value in values if value is not None) or "unknown"


def escape_cell(value: str) -> str:
    return value.replace("\n", " ").replace("|", "\\|").strip()


def truncate(value: str, length: int = 220) -> str:
    if len(value) <= length:
        return value
    return f"{value[: length - 3].rstrip()}..."


def render_markdown(queries: list[str], tweets: list[TweetEvidence], generated_at: datetime) -> str:
    lines = [
        "# Xquik X Evidence",
        "",
        "## Meta",
        f"- Timestamp (UTC): {generated_at.isoformat()}",
        f"- Queries: {' | '.join(queries)}",
        "- Source type: Secondary X evidence",
        "",
        "## Use In The X Research Loop",
        "- Use these posts as leads for phrasing, objections, examples, authors, and links.",
        "- Deep-read important threads, quoted tweets, replies, and videos in the browser workflow.",
        "- Verify publishable claims against primary sources before synthesis.",
        "",
        "## Evidence",
    ]
    if not tweets:
        lines.append("\nNo matching posts returned.")
    else:
        lines.extend(["", "| Query | Author | Text | Engagement | URL |", "| --- | --- | --- | --- | --- |"])
        for tweet in tweets:
            lines.append(
                "| "
                + " | ".join(
                    [
                        escape_cell(tweet.query),
                        escape_cell(tweet.author or "unknown"),
                        escape_cell(truncate(tweet.text)),
                        escape_cell(metric_text(tweet.metrics)),
                        f"[source]({tweet.url})" if tweet.url else "",
                    ]
                )
                + " |"
            )

    urls = sorted({tweet.url for tweet in tweets if tweet.url})
    lines.extend(["", "## Sources"])
    lines.extend([f"- {url}" for url in urls] or ["- none"])
    return "\n".join(lines) + "\n"


def timestamp_slug(now: datetime) -> str:
    return now.strftime("%Y%m%d_%H%M%SZ")


def save_output(out_dir: str, filename: str, content: str) -> Path:
    target_dir = Path(out_dir)
    if not target_dir.is_absolute():
        target_dir = repo_root() / target_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / filename
    target.write_text(content, encoding="utf-8")
    return target


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect secondary X evidence through Xquik APIs.")
    parser.add_argument("--query", action="append", default=[], help="X search query. Repeat for multiple searches.")
    parser.add_argument("--topic", default="", help="Topic used as a query when --query is omitted.")
    parser.add_argument("--limit", type=int, default=20, help="Results per query, capped at 50.")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR, help="Directory for saved evidence artifacts.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--dry-run", action="store_true", help="Print planned request URLs without calling the API.")
    parser.add_argument("--no-save", action="store_true", help="Print output without writing an artifact file.")
    return parser.parse_args(argv)


def collect(queries: list[str], limit: int, config: Config) -> list[TweetEvidence]:
    headers = build_headers(config.api_key)
    tweets: list[TweetEvidence] = []
    for query in queries:
        payload = fetch_json(build_search_url(config.base_url, query, limit), headers)
        tweets.extend(
            tweet
            for item in extract_tweet_list(payload)
            if (tweet := normalize_tweet(item, query)) is not None
        )
    return tweets


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    queries = [query.strip() for query in args.query if query.strip()]
    if not queries and args.topic.strip():
        queries = [args.topic.strip()]
    if not queries:
        sys.stderr.write("Missing --query or --topic.\n")
        return 2

    limit = min(max(args.limit, 1), 50)
    config = get_config()
    urls = [build_search_url(config.base_url, query, limit) for query in queries]
    if args.dry_run:
        print(json.dumps({"queries": queries, "urls": urls}, indent=2))
        return 0

    if not config.api_key.strip():
        sys.stderr.write("Missing XQUIK_API_KEY.\n")
        return 2

    generated_at = datetime.now(tz=timezone.utc)
    tweets = collect(queries, limit, config)
    if args.format == "json":
        output = json.dumps(
            {
                "generated_at": generated_at.isoformat(),
                "queries": queries,
                "tweets": [asdict(tweet) for tweet in tweets],
            },
            indent=2,
        )
        extension = "json"
    else:
        output = render_markdown(queries, tweets, generated_at)
        extension = "md"

    if not args.no_save:
        saved = save_output(args.out_dir, f"{timestamp_slug(generated_at)}_xquik_evidence.{extension}", output)
        sys.stderr.write(f"Saved: {saved.relative_to(Path.cwd()) if saved.is_relative_to(Path.cwd()) else saved}\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
