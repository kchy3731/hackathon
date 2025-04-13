import feedparser

url = "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"
feed = feedparser.parse(url)

for entry in feed.entries:
   print("Entry Title:", entry.title)
   print("Entry Link:", entry.link)
   print("Entry Published Date:", entry.published)
   print("Entry Summary:", entry.summary)
   print("\n")

