import logging
import os
import sys

from dotenv import load_dotenv

from ai_summarizer import SummarizerError, get_groq_client, summarize_and_filter
from config import MAX_TOTAL_ARTICLES, RECENCY_HOURS, RSS_FEEDS
from email_sender import EmailSendError, send_email
from news_collector import collect_all_articles


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )


def load_and_validate_env() -> dict:
    load_dotenv()
    required = {
        "GROQ_API_KEY": "Groq API key (free at console.groq.com — no billing needed)",
        "GMAIL_SENDER": "Gmail sender address",
        "GMAIL_APP_PASSWORD": "Gmail App Password (not your main password)",
        "RECIPIENT_EMAIL": "Recipient email address",
    }
    missing = [f"  {key} — {desc}" for key, desc in required.items() if not os.environ.get(key)]
    if missing:
        raise EnvironmentError(
            "Missing required .env values:\n" + "\n".join(missing) +
            "\n\nCopy .env.example to .env and fill in all values."
        )
    return {key: os.environ[key] for key in required}


def extract_subject(email_body: str) -> tuple[str, str]:
    import datetime
    default_subject = f"AI Engineer Digest — {datetime.date.today().strftime('%B %d, %Y')}"
    lines = email_body.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("Subject:"):
            subject = line.split(":", 1)[1].strip()
            remaining = "\n".join(lines[:i] + lines[i + 1:]).strip()
            return subject, remaining
    return default_subject, email_body


def run() -> int:
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        env = load_and_validate_env()
    except EnvironmentError as exc:
        print(f"Configuration error:\n{exc}", file=sys.stderr)
        return 2

    logger.info("Collecting articles from %d feeds (last %dh)...", len(RSS_FEEDS), RECENCY_HOURS)
    articles = collect_all_articles(RSS_FEEDS, RECENCY_HOURS)
    logger.info("Total articles collected: %d", len(articles))

    if not articles:
        logger.error("No articles collected from any feed. Check network connectivity.")
        return 2

    if len(articles) > MAX_TOTAL_ARTICLES:
        articles = articles[:MAX_TOTAL_ARTICLES]
        logger.info("Capped at %d articles for Gemini", MAX_TOTAL_ARTICLES)

    logger.info("Sending %d articles to Gemini for filtering and summarization...", len(articles))
    try:
        client = get_groq_client(env["GROQ_API_KEY"])
        email_body = summarize_and_filter(articles, client)
    except SummarizerError as exc:
        logger.error("Summarization failed: %s", exc)
        return 2

    subject, body = extract_subject(email_body)
    logger.info("Email subject: %s", subject)

    logger.info("Sending email from %s to %s...", env["GMAIL_SENDER"], env["RECIPIENT_EMAIL"])
    try:
        send_email(
            sender=env["GMAIL_SENDER"],
            recipient=env["RECIPIENT_EMAIL"],
            subject=subject,
            body=body,
            smtp_password=env["GMAIL_APP_PASSWORD"],
        )
    except EmailSendError as exc:
        logger.error("Email sending failed: %s", exc)
        return 1

    logger.info("Done. Email sent successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
