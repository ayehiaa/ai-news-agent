import datetime
import logging

from groq import Groq, APIConnectionError, RateLimitError, APIStatusError

from config import EMAIL_WORD_LIMIT, GROQ_MODEL

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = f"""You are an expert AI news curator writing for an audience of software engineers.
Your job is to read a batch of raw RSS article summaries, filter for what is most relevant to
working software engineers, and produce a concise, well-structured daily email digest.

RELEVANCE CRITERIA — include articles about:
- New AI model releases (LLMs, vision models, code models, reasoning models)
- AI coding assistants and IDE integrations (Copilot, Cursor, Codeium, Claude Code, etc.)
- New AI-powered developer tools, CLI tools, SDKs, and APIs
- Framework and library updates with AI features (LangChain, LlamaIndex, Hugging Face, etc.)
- AI agents, agentic workflows, and multi-agent systems
- Prompt engineering techniques, specs-driven development, and context engineering
- Model fine-tuning, RAG patterns, and production deployment strategies
- AI safety, regulation, or policy that directly affects developer practices
- Significant open-source AI releases (models, datasets, tooling)
- AI hardware announcements relevant to inference and training costs
- MCP (Model Context Protocol) servers, plugins, and integrations
- New AI specs, standards, or protocols relevant to engineering

EXCLUSION CRITERIA — skip articles about:
- Celebrity or entertainment AI stories with no engineering relevance
- General consumer AI product launches with no developer API or SDK
- Vague opinion pieces with no new technical content
- Redundant coverage of the same story already represented in the batch

OUTPUT FORMAT — produce a plain-text email with exactly this structure. Do not add markdown
code fences. Do not use asterisks or markdown formatting. Keep total output under {EMAIL_WORD_LIMIT} words.

---
Subject: AI Engineer Digest — [today's date, e.g. April 25, 2026]

Top Stories
-----------
[3-5 bullet points, each 2-3 sentences. Lead with the most impactful story for engineers.
Each bullet ends with the source URL in parentheses.]

What to Watch
-------------
[2-3 shorter bullets on emerging trends or stories worth monitoring.]

Quick Links
-----------
[3-5 one-line links for stories worth knowing but needing no summary.
Format: - Title (Source) — URL]

---
If fewer than 3 relevant stories exist in the batch, say so honestly and provide whatever
relevant content is available rather than padding with irrelevant articles."""


class SummarizerError(Exception):
    pass


def get_groq_client(api_key: str) -> Groq:
    return Groq(api_key=api_key)


def _build_article_payload(articles: list[dict]) -> str:
    lines = []
    for i, a in enumerate(articles, 1):
        pub = a["published_dt"].strftime("%Y-%m-%d %H:%M UTC") if a["published_dt"] else "Unknown"
        lines.append(f"[{i}] SOURCE: {a['source']}")
        lines.append(f"    Title: {a['title']}")
        lines.append(f"    URL: {a['url']}")
        lines.append(f"    Published: {pub}")
        lines.append(f"    Summary: {a['summary']}")
        lines.append("")
    return "\n".join(lines)


def summarize_and_filter(articles: list[dict], client: Groq) -> str:
    today = datetime.date.today().strftime("%B %d, %Y")
    payload = _build_article_payload(articles)

    user_message = (
        f"Today is {today}.\n\n"
        f"Below are {len(articles)} RSS articles collected in the last 48 hours. "
        f"Please filter, rank by relevance to software engineers, and produce the "
        f"email digest as instructed.\n\n"
        f"{payload}"
    )

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=1500,
            temperature=0.4,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
    except APIConnectionError as exc:
        raise SummarizerError(f"Network error connecting to Groq: {exc}") from exc
    except RateLimitError as exc:
        raise SummarizerError(f"Groq rate limit hit — try again shortly: {exc}") from exc
    except APIStatusError as exc:
        raise SummarizerError(f"Groq API error {exc.status_code}: {exc.message}") from exc

    text = response.choices[0].message.content
    if not text:
        raise SummarizerError("Groq returned an empty response")

    usage = response.usage
    logger.info(
        "Groq usage — input_tokens=%d  output_tokens=%d",
        usage.prompt_tokens,
        usage.completion_tokens,
    )

    return text
