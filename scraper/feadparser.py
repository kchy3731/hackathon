import feedparser
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import requests
import csv
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import Formatter
from youtube_transcript_api.formatters import TextFormatter





Transcript = ''
from scraper import article
def parseRSS() -> list[article]:
    now = datetime.now()
    with open("Logins.txt", "a") as file:
        file.write(now.isoformat() + "\n")

# Read all login times
    with open("Logins.txt", "r") as file:
        lines = [line.strip() for line in file.readlines() if line.strip()]

# Determine time range
    if len(lines) >= 2:
        last_login = datetime.fromisoformat(lines[-2])
        current_login = datetime.fromisoformat(lines[-1])
        time_range = current_login - last_login
    else:
    # Default if only one login exists
        time_range = timedelta(days=1)

    with open("RSSlinks.txt", "r") as file:
        urls = file.readlines()

    articles: list[article] = []

    for url in urls:
        url = url.strip()
        if not url:
            continue
        feed = feedparser.parse(url)
        for entry in feed.entries:
            last_plus = (entry.published).rfind("+")
            if last_plus != -1:
                corrected_date_str = entry.published[:last_plus] + "-" + entry.published[last_plus + 1:]
                entry_date = datetime.strptime(corrected_date_str, "%Y-%m-%dT%H:%M:%S-00:00")
                if now - entry_date <= time_range:
                    articles.append(article(
                        source = feed.feed.get("title", "RSS Feed"),
                        title = entry.title,
                        description = entry.summary,
                        content = entry.description,
                        timestamp = entry_date,
                        link = entry.link
                    ))

    return articles

def main():

    now = datetime.now()
    lastLogin  = now
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
                entry_date = datetime.strptime((corrected_date_str), "%Y-%m-%dT%H:%M:%S-00:00")
                if now - entry_date <= time_range:
                    print("Entry Title:", entry.title)
                    print("Entry Link:", entry.link)
                    print("Entry Published Date:", entry.published)
                    print("Entry Summary:", entry.summary)
                    print("Entry Description:", entry.description)
                    if (".youtube.com") in entry:
                        #code for youtube transcript
                        ytt_api = YouTubeTranscriptApi()
                        Transcript = (ytt_api.fetch(entry.link[entry.link.find("v=") + 2:])).fetch()
                        formatter = TextFormatter()
                        txtFormattedTranscript = formatter.format_transcript(Transcript)

                    else:
                        response = requests.get(entry.link)

                        if response.status_code == 200:
                            soup = BeautifulSoup(response.content, "html.parser") 
                            print("Entry Content:", soup.get_text())

                    print("\n")

        with open('rss_data.csv', mode='w', newline='', encoding='utf-8') as csv_file:
            fieldnames = ['title', 'link', 'published', 'summary', 'content']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            if (".youtube.com") in entry:
                for entry in feed.entries:
                    writer.writerow({'title': entry.title, 'link': entry.link, 'published': entry_date, 'content': txtFormattedTranscript})
            else:
                for entry in feed.entries:
                    writer.writerow({'title': entry.title, 'link': entry.link, 'published': entry_date, 'content': soup.get_text()})


if __name__ == "__main__":
    main()


'''
    def main():
    try:
        with open("lastLogin.txt", "r") as f:
            last_login_str = f.read().strip()
            lastLogin = datetime.fromisoformat(last_login_str)
    except FileNotFoundError:
        lastLogin = datetime.min

    now = datetime.now()

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
                if lastLogin <= entry_date <= now:
                    print("Entry Title:", entry.title)
                    print("Entry Link:", entry.link)
                    print("Entry Published Date:", entry.published)
                    print("Entry Summary:", entry.summary)
                    print("Entry Description:", entry.description)

                    if ".youtube.com" in entry.link:
                        video_id = entry.link[entry.link.find("v=") + 2:]
                        try:
                            transcript = YouTubeTranscriptApi.get_transcript(video_id)
                            formatter = TextFormatter()
                            txtFormattedTranscript = formatter.format_transcript(transcript)
                            content = txtFormattedTranscript
                        except Exception as e:
                            content = f"Error fetching transcript: {e}"
                    else:
                        response = requests.get(entry.link)
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.content, "html.parser")
                            content = soup.get_text()
                        else:
                            content = "Failed to fetch page content."

                    with open('rss_data.csv', mode='a', newline='', encoding='utf-8') as csv_file:
                        fieldnames = ['title', 'link', 'published', 'summary', 'content']
                        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                        if csv_file.tell() == 0:
                            writer.writeheader()
                        writer.writerow({
                            'title': entry.title,
                            'link': entry.link,
                            'published': entry_date,
                            'summary': entry.summary,
                            'content': content
                        })

                    print("\n")

    with open("lastLogin.txt", "w") as f:
        f.write(now.isoformat())

        '''