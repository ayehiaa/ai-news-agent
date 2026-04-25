import datetime
import logging
from html.parser import HTMLParser

import feedparser

from config import MAX_ARTICLES_PER_FEED, RECENCY_HOURS, USER_AGENT

logger = logging.getLogger(__name__)


class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts = []

    def handle_data(self, data):
        self._parts.append(data)

    def get_text(self):
        return " ".join(self._parts).strip()


def _strip_html(raw: str) -> str:
    stripper = _HTMLStripper()
    stripper.feed(raw or "")
    return stripper.get_text()


def _parse_entry(entry, source_name: str) -> dict:
    published_dt = None
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            try:
                published_dt = datetime.datetime(*parsed[:6], tzinfo=datetime.timezone.utc)
            except Exception:
                pass
            break

    summary = _strip_html(getattr(entry, "summary", "") or "")
    if len(summary) > 400:
        summary = summary[:400] + "..."

    return {
        "title": getattr(entry, "title", "No title"),
        "url": getattr(entry, "link", ""),
        "published_dt": published_dt,
        "summary": summary,
        "source": source_name,
    }


def _is_recent(article: dict, hours: int) -> bool:
    if article["published_dt"] is None:
        return True
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)
    return article["published_dt"] >= cutoff


def fetch_feed(feed_config: dict) -> list[dict]:
    feedparser.USER_AGENT = USER_AGENT
    try:
        feed = feedparser.parse(feed_config["url"], request_headers={"User-Agent": USER_AGENT})
    except Exception as exc:
        logger.warning("Failed to fetch %s: %s", feed_config["name"], exc)
        return []

    if feed.bozo and not feed.entries:
        logger.warning("Malformed feed with no entries: %s", feed_config["name"])
        return []

    articles = []
    for entry in feed.entries:
        try:
            articles.append(_parse_entry(entry, feed_config["name"]))
        except Exception as exc:
            logger.debug("Skipping malformed entry in %s: %s", feed_config["name"], exc)

    return articles


def collect_all_articles(feeds: list[dict], recency_hours: int = RECENCY_HOURS) -> list[dict]:
    all_articles = []
    for feed_config in feeds:
        articles = fetch_feed(feed_config)
        recent = [a for a in articles if _is_recent(a, recency_hours)]
        capped = recent[:MAX_ARTICLES_PER_FEED]
        logger.info("%-25s fetched=%d  recent=%d  kept=%d", feed_config["name"], len(articles), len(recent), len(capped))
        all_articles.extend(capped)
    return all_articles
