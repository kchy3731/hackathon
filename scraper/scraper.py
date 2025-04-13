import datetime
import json
import asyncio
import websockets
import feedparser

class article:
    def __init__(self, source, title, description, content, timestamp, link):
        self.source = source
        self.title = title
        self.description = description
        self.content = content
        self.timestamp = timestamp
        self.link = link

    def __str__(self):
        return f"{self.source},{self.title},{self.description} - {self.content} - {self.timestamp} - {self.link}"
    
    def __lt__(self, other):
        return self.timestamp < other.timestamp
    
    def __gt__(self, other):
        return self.timestamp > other.timestamp
    
    def __le__(self, other):
        return self.timestamp <= other.timestamp
    
    def __ge__(self, other):
        return self.timestamp >= other.timestamp
    
    def __eq__(self, other):
        return self.timestamp == other.timestamp
    
    def __hash__(self):
        return hash(self.timestamp)
    
    def to_dict(self):
        return {
            "source": self.source,
            "title": self.title,
            "description": self.description,
            "content": self.content,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime.datetime) else self.timestamp,
            "link": self.link
        }

def takeSnapshot(timestamp: datetime.datetime, youtube=False, reddit=False, spotify=False, twitter=False) -> list[article]:
    from spotify_methods import add_all_artists
    from twitter_methods import get_tweets_since_timestamp
    from youtube_methods import add_all_subscriptions
    from reddit_methods import add_all_subreddits
    from feadparser import parseRSS
    
    if youtube:
        add_all_subscriptions()
    if reddit:
        add_all_subreddits()

    snap: list[article] = []

    if spotify:
        snap.extend(add_all_artists())
    if twitter:
        snap.extend(get_tweets_since_timestamp(timestamp))

    # parse RSS
    print("Parsing RSS...")
    snap.extend(parseRSS())

    # sort and de-duplicate
    snap = sorted(set(snap), reverse=True)

    # remove all before timestamp
    snap = [a for a in snap if a.timestamp >= timestamp]

    return snap

# Websocket server implementation
async def handle_client(websocket):
    try:
        async for message in websocket:
            data = json.loads(message)
            if data.get('action') == 'get_snapshot':
                # Extract parameters from request
                timestamp = datetime.datetime.fromisoformat(data.get('timestamp', datetime.datetime.now().isoformat()))
                youtube = data.get('youtube', False)
                reddit = data.get('reddit', False)
                spotify = data.get('spotify', False)
                twitter = data.get('twitter', False)
                
                # Take snapshot with requested parameters
                snapshot = takeSnapshot(timestamp, youtube, reddit, spotify, twitter)
                
                # Convert snapshot to JSON-serializable format
                snapshot_data = [article.to_dict() for article in snapshot]
                
                # Send snapshot back to client
                await websocket.send(json.dumps({
                    'status': 'success',
                    'data': snapshot_data
                }))
            elif data.get('action') == 'add_rss_feed':
                # Extract parameters from request
                feed_url = data.get('feed_url', None)

                if not feed_url:
                    await websocket.send(json.dumps({
                        'status': 'error',
                        'message': 'Feed URL is required'
                    }))
                    continue

                # verify validity of feed
                feed = feedparser.parse(feed_url)

                if feed.bozo or not feed.entries:
                    await websocket.send(json.dumps({
                        'status': 'error',
                        'message': 'Invalid RSS feed'
                    }))
                    continue

                # Write to RSSlinks.txt
                with open("RSSlinks.txt", "a", encoding="utf-8") as f:
                    f.write(f"{feed_url}\n")

                await websocket.send(json.dumps({
                    'status': 'success',
                    'message': 'RSS feed added successfully'
                }))
            else:
                await websocket.send(json.dumps({
                    'status': 'error',
                    'message': 'Unknown action'
                }))
    except Exception as e:
        await websocket.send(json.dumps({
            'status': 'error',
            'message': str(e)
        }))

async def start_server(host='localhost', port=8765):
    server = await websockets.serve(handle_client, host, port)
    print(f"Websocket server started on ws://{host}:{port}")
    return server

def run_websocket_server(host='localhost', port=8765):
    loop = asyncio.get_event_loop()
    server = loop.run_until_complete(start_server(host, port))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("Server shutting down...")
    finally:
        server.close()
        loop.run_until_complete(server.wait_closed())
        loop.close()

if __name__ == "__main__":
    import sys
    from test_client import run_test

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Run in test client mode
        print("Running in test client mode...")
        run_test()
    else:
        # Run in server mode
        print("Running in server mode...")
        run_websocket_server()
