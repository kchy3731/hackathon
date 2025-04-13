import websockets
import datetime
import json
import asyncio

async def test_client():
    """Test client to verify websocket server functionality"""
    uri = "ws://localhost:8765"
    print(f"Connecting to {uri}...")
    
    async with websockets.connect(uri) as websocket:
        # Create test request
        request = {
            "action": "get_snapshot",
            "timestamp": datetime.datetime.now().isoformat(),
            "youtube": True,
            "reddit": True,
            "spotify": True,
            "twitter": False
        }
        
        print(f"Sending request: {request}")
        await websocket.send(json.dumps(request))
        
        # Wait for response
        response = await websocket.recv()
        print(response)
        response_data = json.loads(response)
        
        print("\nReceived response:")
        print(f"Status: {response_data.get('status')}")
        
        # Print summary of articles received
        articles = response_data.get('data', [])
        print(f"Received {len(articles)} articles")
        
        # Print first few articles as sample
        #for i, article in enumerate(articles[:3]):
        for i, article in enumerate(articles):
            print(f"\nArticle {i+1}:")
            print(f"Source: {article.get('source')}")
            print(f"Timestamp: {article.get('timestamp')}")
            print(f"Title: {article.get('title')}")
            print(f"Link: {article.get('link')}")
        
        # if len(articles) > 3:
        #     print(f"\n... and {len(articles) - 3} more articles")
        
        return response_data

def run_test():
    """Run the test client"""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(test_client())