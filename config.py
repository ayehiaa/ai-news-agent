RSS_FEEDS = [
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "timeout": 10},
    {"name": "The Verge AI", "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "timeout": 10},
    {"name": "Wired", "url": "https://www.wired.com/feed/rss", "timeout": 10},
    {"name": "MIT Technology Review AI", "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed", "timeout": 10},
    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index", "timeout": 10},
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/", "timeout": 10},
    {"name": "InfoQ", "url": "https://feed.infoq.com/", "timeout": 10},
    {"name": "IEEE Spectrum", "url": "https://spectrum.ieee.org/feeds/feed.rss", "timeout": 10},
    {"name": "The Register", "url": "https://www.theregister.com/headlines.atom", "timeout": 10},
    {"name": "Hacker News", "url": "https://news.ycombinator.com/rss", "timeout": 10},
]

RECENCY_HOURS = 48
MAX_ARTICLES_PER_FEED = 5
MAX_TOTAL_ARTICLES = 30

GEMINI_MODEL = "gemini-2.0-flash"
EMAIL_WORD_LIMIT = 600

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

USER_AGENT = "AINewsAgent/1.0 (Python feedparser)"
