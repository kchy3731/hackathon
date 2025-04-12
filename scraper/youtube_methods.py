import os
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# The scopes required for accessing subscriptions
SCOPES = ['https://www.googleapis.com/auth/youtube.readonly']

def get_authenticated_service():
    """
    Authenticate user and create YouTube API service
    Returns the authenticated service object
    """
    credentials = None
    # Check if token file exists
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            credentials = pickle.load(token)
            
    # If credentials don't exist or are invalid, login
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secrets.json', SCOPES)
            credentials = flow.run_local_server(port=8888)
            
        # Save credentials for future use
        with open('token.pickle', 'wb') as token:
            pickle.dump(credentials, token)
    
    # Build and return the YouTube service
    return build('youtube', 'v3', credentials=credentials)

def get_subscribed_channels(youtube_service):
    """
    Fetch all subscribed channels for the authenticated user
    Returns a list of channel information dictionaries
    """
    channels = []
    next_page_token = None
    
    while True:
        # Get subscriptions, 50 at a time (API maximum)
        request = youtube_service.subscriptions().list(
            part='snippet',
            mine=True,
            maxResults=50,
            pageToken=next_page_token
        )
        response = request.execute()
        
        # Process each subscription
        for item in response['items']:
            channel_id = item['snippet']['resourceId']['channelId']
            channel_title = item['snippet']['title']
            channels.append({
                'id': channel_id,
                'title': channel_title
            })
        
        # Check if there are more pages
        next_page_token = response.get('nextPageToken')
        if not next_page_token:
            break
    
    return channels

def get_rss_feeds(channels):
    """
    Generate RSS feed URLs for each channel
    Returns a list of dictionaries with channel title and RSS URL
    """
    rss_feeds = []
    
    for channel in channels:
        # YouTube RSS feed format for channels
        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel['id']}"
        rss_feeds.append({
            'title': channel['title'],
            'rss_url': rss_url
        })
    
    return rss_feeds

def main():
    # Authenticate and build service
    print("Authenticating...")
    youtube = get_authenticated_service()
    
    # Get subscribed channels
    print("Fetching subscribed channels...")
    channels = get_subscribed_channels(youtube)
    print(f"Found {len(channels)} subscribed channels.")
    
    # Generate RSS feeds
    print("Generating RSS feed URLs...")
    rss_feeds = get_rss_feeds(channels)
    
    # Print results
    print("\nYour YouTube subscription RSS feeds:")
    print("====================================")
    
    for i, feed in enumerate(rss_feeds, 1):
        print(f"{i}. {feed['title']}")
        print(f"   RSS: {feed['rss_url']}")
        print()
        
    # Optionally save to file
    with open("RSS.txt", "a", encoding="utf-8") as f:
        for feed in rss_feeds:
            f.write(f"{feed['rss_url']}\n")
    
    print(f"RSS feeds saved to youtube_subscription_feeds.txt")

if __name__ == "__main__":
    main()