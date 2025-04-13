import feedparser

url = "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"
feed = feedparser.parse(url)

print("Feed Title:", feed.feed.title)
print("Feed Description:", feed.feed.description)
print("Feed Link:", feed.feed.link)