import feedparser

with open("RSSlinks.txt", "r") as file:
    urls = file.readlines()

for url in urls:
    url = url.strip()
    if not url:
         continue
    feed = feedparser.parse(url)
    for entry in feed.entries:
    print("Feed Title:", feed.feed.get("title", "N/A"))
    print("Feed Description:", feed.feed.get("description", "N/A"))
    print("Feed Link:", feed.feed.get("link", "N/A"))
    print("-" * 40)