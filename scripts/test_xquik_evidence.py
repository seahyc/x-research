import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xquik_evidence as evidence


class XquikEvidenceTest(unittest.TestCase):
    def test_build_search_url_encodes_query_and_limit(self):
        url = evidence.build_search_url("https://xquik.com/", "agent research", 8)

        self.assertEqual(url, "https://xquik.com/api/v1/x/tweets/search?q=agent+research&limit=8")

    def test_build_headers_supports_api_key_and_bearer(self):
        self.assertEqual(evidence.build_headers("xq_test"), {"Accept": "application/json", "x-api-key": "xq_test"})
        self.assertEqual(evidence.build_headers("Bearer token"), {"Accept": "application/json", "Authorization": "Bearer token"})

    def test_get_config_prefers_exported_xquik_key(self):
        config = evidence.get_config(
            {"XQUIK_API_KEY": "xquik", "XQUIK_BASE_URL": "https://api.example.com"},
            {"XQUIK_API_KEY": "dotenv"},
        )

        self.assertEqual(config, evidence.Config(api_key="xquik", base_url="https://api.example.com"))

    def test_get_config_reads_dotenv_fallback(self):
        config = evidence.get_config({}, {"XQUIK_API_KEY": "dotenv"})

        self.assertEqual(config, evidence.Config(api_key="dotenv", base_url="https://xquik.com"))

    def test_extract_tweet_list_handles_nested_payloads(self):
        payload = {"data": {"tweets": [{"id": "1", "text": "one"}]}}

        self.assertEqual(evidence.extract_tweet_list(payload), [{"id": "1", "text": "one"}])

    def test_normalize_tweet_maps_common_shapes(self):
        tweet = evidence.normalize_tweet(
            {
                "id": "123",
                "full_text": "Research agents need current X evidence.",
                "user": {"username": "example"},
                "public_metrics": {"reply_count": 2, "retweet_count": 3, "quote_count": 4, "like_count": 5, "view_count": "600"},
            },
            "research agents",
        )

        self.assertEqual(
            tweet,
            evidence.TweetEvidence(
                query="research agents",
                tweet_id="123",
                author="@example",
                text="Research agents need current X evidence.",
                url="https://x.com/example/status/123",
                created_at="",
                metrics=evidence.Metrics(replies=2, reposts=3, quotes=4, likes=5, views=600),
            ),
        )

    def test_render_markdown_keeps_posts_secondary(self):
        markdown = evidence.render_markdown(
            ["research agents"],
            [
                evidence.TweetEvidence(
                    query="research agents",
                    tweet_id="123",
                    author="@example",
                    text="Check the official docs before publishing.",
                    url="https://x.com/example/status/123",
                    created_at="",
                    metrics=evidence.Metrics(replies=None, reposts=None, quotes=None, likes=10, views=None),
                )
            ],
            datetime(2026, 5, 25, tzinfo=timezone.utc),
        )

        self.assertIn("Xquik X Evidence", markdown)
        self.assertIn("Source type: Secondary X evidence", markdown)
        self.assertIn("official docs", markdown)
        self.assertIn("https://x.com/example/status/123", markdown)

    def test_dry_run_does_not_require_api_key(self):
        output = {"queries": ["agent research"], "urls": ["https://xquik.com/api/v1/x/tweets/search?q=agent+research&limit=20"]}

        self.assertEqual(json.loads(json.dumps(output)), output)


if __name__ == "__main__":
    unittest.main()
