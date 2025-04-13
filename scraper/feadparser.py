import feedparser

url = "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"
feed = feedparser.parse(url)

for entry in feed.entries:
    print("Entry Title:", entry.title)
    print("Entry Summary:", entry.summary)
    print("Entry Link:", entry.link)
    print("Entry Published:", entry.published)
    print("Entry Author:", entry.author)
    print("=" * 80)  # Separator between entries