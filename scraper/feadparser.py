import feedparser
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import requests
import csv
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import Formatter
from youtube_transcript_api.formatters import TextFormatter
import db_connector

Transcript = ''
from scraper import article

def parseRSS(manage_db_connection=True) -> list[article]:
    now = datetime.now()

    # Initialize database connection if needed
    if manage_db_connection:
        db_connector.init_connection_pool()

    # Get the last login time from the database for the user
    # For now, we'll use a default time range of 1 day
    time_range = timedelta(days=1)

    # Get RSS sources from the database
    urls = db_connector.get_rss_sources()

    if not urls:
        print("No RSS sources found in the database")
        # Fallback to RSSlinks.txt if no sources in database
        try:
            with open("RSSlinks.txt", "r") as file:
                urls = [line.strip() for line in file.readlines() if line.strip()]
        except FileNotFoundError:
            print("RSSlinks.txt not found")
            return []

    articles: list[article] = []

    for url in urls:
        url = url.strip()
        if not url:
            continue
        try:
            feed = feedparser.parse(url)
            if feed.bozo and not feed.entries:
                print(f"Error parsing feed: {url}")
                continue

            for entry in feed.entries:
                try:
                    # Handle different date formats
                    entry_date = None

                    # Try different date fields and formats
                    date_fields = ['published', 'pubDate', 'updated', 'date', 'created']

                    for field in date_fields:
                        if hasattr(entry, field) and getattr(entry, field):
                            try:
                                date_str = getattr(entry, field)
                                # Try ISO format with timezone
                                if '+' in date_str:
                                    last_plus = date_str.rfind("+")
                                    corrected_date_str = date_str[:last_plus] + "-" + date_str[last_plus + 1:]
                                    entry_date = datetime.strptime(corrected_date_str, "%Y-%m-%dT%H:%M:%S-00:00")
                                    break
                                # Try RFC 822 format
                                elif ',' in date_str:
                                    entry_date = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
                                    break
                                # Try simple ISO format
                                elif 'T' in date_str:
                                    entry_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                                    break
                            except (ValueError, AttributeError, TypeError):
                                # Continue to next field/format if this one fails
                                continue

                    # If no valid date found, use earliest possible time today
                    if entry_date is None:
                        print(f"No valid date found for entry: {entry.title if hasattr(entry, 'title') else 'Unknown title'}")
                        entry_date = datetime.combine(datetime.now().date(), datetime.min.time())

                    # Make sure we have a valid datetime object
                    if entry_date is None:
                        entry_date = datetime.now()

                    # Make sure both datetimes are either naive or aware
                    if hasattr(entry_date, 'tzinfo') and entry_date.tzinfo is not None:
                        # Convert aware datetime to naive by removing timezone info
                        entry_date = entry_date.replace(tzinfo=None)

                    # Now both datetimes should be naive
                    try:
                        time_diff = now - entry_date
                        if time_diff <= time_range:
                            new_article = article(
                                source=feed.feed.get("title", "RSS Feed"),
                                title=entry.title,
                                description=entry.get('summary', ''),
                                content=entry.get('description', ''),
                                timestamp=entry_date,
                                link=entry.link
                            )
                            articles.append(new_article)

                            # Note: We no longer save articles here
                            # This is now handled in run_scraper.py to better track duplicates
                    except Exception as e:
                        print(f"Error processing time comparison: {e}")
                except Exception as e:
                    print(f"Error processing entry in feed {url}: {e}")
        except Exception as e:
            print(f"Error processing feed {url}: {e}")

    # Close database connection pool if needed
    if manage_db_connection:
        db_connector.close_connection_pool()

    return articles

def main():

    now = datetime.now()
    lastLogin  = now
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