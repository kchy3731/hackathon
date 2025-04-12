import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup

def get_article_content(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        content_div = soup.find('div', {'data-testid': 'article-body'})
        return '\n'.join(p.get_text() for p in content_div.find_all('p')) if content_div else "Content not found"
    except:
        return "Error fetching content"

# Read RSS XML from file
with open('news.txt', 'r', encoding='utf-8') as file:
    rss_xml = file.read()

root = ET.fromstring(rss_xml)
namespaces = {
    'dc': 'http://purl.org/dc/elements/1.1/',
    'media': 'http://search.yahoo.com/mrss/'
}

for item in root.findall('./channel/item'):
    print("Title:", item.find('title').text)
    print("Author:", item.find('dc:creator', namespaces).text if item.find('dc:creator', namespaces) is not None else "No author")
    print("Date:", item.find('pubDate').text)
    print("Content:", get_article_content(item.find('link').text)[:500] + "...\n")
    print("=" * 80)  # Separator between articles