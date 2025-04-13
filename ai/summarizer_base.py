import json
import os
import asyncio
import websockets
from datetime import datetime
from newspaper import Article
from openai import OpenAI



from TrendAnalysis import analyze_and_display  

os.environ["TOKENIZERS_PARALLELISM"] = "false"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

async def fetch_scraper_data():
    """Fetch articles from WebSocket scraper"""
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        request = {
            'action': 'get_snapshot',
            'timestamp': datetime.now().isoformat(),
            'youtube': True,
            'reddit': True,
            'spotify': True,
            'twitter': True
        }
        await websocket.send(json.dumps(request))
        response = await websocket.recv()
        data = json.loads(response)
        if data['status'] == 'success':
            return data['data']  # Direct scraper output
        raise Exception(data.get('message', 'Failed to fetch snapshot'))

def transform_scraper_format(scraper_data):
    """Convert scraper articles to TrendAnalysis format"""
    transformed = []
    for article in scraper_data:
        try:
            # Convert ISO timestamp to date string
            dt = datetime.fromisoformat(article['timestamp'])
            transformed.append({
                'title': article['title'],
                'date': dt.strftime('%Y-%m-%d'),
                'source': article['source'],
                'url': article['link'],  # Map link -> url
                # Preserve original data for other uses
                '_original': {
                    'description': article['description'],
                    'content': article['content'],
                    'timestamp': article['timestamp']
                }
            })
        except KeyError as e:
            print(f"Skipping invalid article: Missing field {e}")
    return transformed

def get_valid_article(url):
    """Try to fetch and parse article content with error handling"""
    try:
        article = Article(url, browser_user_agent=headers['User-Agent'], request_timeout=10)
        article.download()
        article.parse()
        
        if len(article.text.strip()) > 100: 
            return article.text
        return None
    except Exception as e:
        print(f"⚠️ Failed to process article: {url}\nError: {str(e)[:200]}...")
        return None

client = OpenAI(api_key="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")

def summarize_with_openai(text):
    messages = [
        {"role": "system", "content": "Create a headline and one-sentence summary."},
        {"role": "user", "content": f"Articles:\n{text[:12000]}\n\nSummary:"}
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.3,
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"OpenAI API Error: {str(e)}"

def summarize_clusters(result):
    summaries = []
    summary_string = ""

    for cluster in result['high_trend_clusters']:
        contents = []
        valid_urls = []
        
        for url in cluster['articles']:
            content = get_valid_article(url)
            if content:
                contents.append(content)
                valid_urls.append(url)

        if contents:
            combined_text = "\n\n".join(contents)
            summary = summarize_with_openai(combined_text)

            summaries.append({
                "cluster_id": cluster['cluster_id'],
                "summary": summary,
                "urls": valid_urls
            })

            summary_string += f"\n\n Cluster {cluster['cluster_id']} Summary:\n{summary}\n"

    return summaries, summary_string

if __name__ == "__main__":
    # Fetch and transform data
    try:
        scraper_data = asyncio.run(fetch_scraper_data())
        articles = transform_scraper_format(scraper_data)
    except Exception as e:
        print(f" Connection error: {str(e)}")
        exit(1)

    if not articles:
        print("No articles received from scraper")
        exit(1)

    # Analysis and summarization remains unchanged
    print("\nRunning trend detection...\n")
    result = analyze_and_display(articles)
    
    if result and result.get('high_trend_clusters'):
        summaries, summary_string = summarize_clusters(result)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(f"cluster_summaries_{timestamp}.json", "w") as f:
            json.dump(summaries, f, indent=2)

        print("\nFinal Summaries:")
        print(summary_string)