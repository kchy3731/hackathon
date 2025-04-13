import feedparser
from datetime import datetime, timedelta

import csv



now = datetime.now()
time_range = timedelta(days=1)

with open("RSSlinks.txt", "r") as file:
    urls = file.readlines()

for url in urls:
    url = url.strip()
    if not url:
        continue
    feed = feedparser.parse(url)
    print("Feed Title:", feed.feed.get("title", "N/A"))
    print("Feed Description:", feed.feed.get("description", "N/A"))
    print("Feed Link:", feed.feed.get("link", "N/A"))
    print("-" * 40)

    for entry in feed.entries:
        last_plus = (entry.published).rfind("+")
        if last_plus != -1:
            corrected_date_str = entry.published[:last_plus] + "-" + entry.published[last_plus + 1:]
            entry_date = datetime.strptime(corrected_date_str, "%Y-%m-%dT%H:%M:%S-00:00")
            if now - entry_date <= time_range:
                print("Entry Title:", entry.title)
                print("Entry Link:", entry.link)
                print("Entry Published Date:", entry.published)
                print("Entry Summary:", entry.summary)
                print("Entry Description:", entry.description)
                print("\n")

    with open('rss_data.csv', mode='w', newline='', encoding='utf-8') as csv_file:
        fieldnames = ['title', 'link', 'published', 'summary']
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        # Iterate through entries and write to the CSV file
        for entry in feed.entries:
            writer.writerow({'title': entry.title, 'link': entry.link, 'published': entry_date})