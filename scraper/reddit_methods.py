import requests
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import json
import threading
import time
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class OAuthHandler(BaseHTTPRequestHandler):
    """Handle the OAuth2 callback from Reddit"""
    
    def do_GET(self):
        """Process the callback request from Reddit"""
        query = urllib.parse.urlparse(self.path).query
        params = dict(urllib.parse.parse_qsl(query))
        
        if 'code' in params:
            self.server.authorization_code = params['code']
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Authentication successful!</h1><p>You can close this window now.</p></body></html>")
        else:
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Authentication failed!</h1><p>Error: No authorization code received.</p></body></html>")
    
    def log_message(self, format, *args):
        """Silence server logs"""
        return

class RedditRSSFetcher:
    def __init__(self, client_id, client_secret, redirect_uri, user_agent):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.user_agent = user_agent
        self.access_token = None
        self.refresh_token = None
        self.token_expiration = 0
        
    def generate_auth_url(self):
        """Generate the Reddit OAuth authorization URL"""
        base_url = "https://www.reddit.com/api/v1/authorize"
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "state": "...",
            "redirect_uri": self.redirect_uri,
            "duration": "permanent",
            "scope": "mysubreddits read"
        }
        
        auth_url = f"{base_url}?{urllib.parse.urlencode(params)}"
        return auth_url
        
    def authenticate(self):
        """Authenticate with Reddit using OAuth"""
        # Get the authorization URL
        auth_url = self.generate_auth_url()
        
        # Start the local server to handle the callback
        server = HTTPServer(('localhost', 8000), OAuthHandler)
        server.authorization_code = None
        
        # Start the server in a separate thread
        server_thread = threading.Thread(target=server.handle_request)
        server_thread.daemon = True
        server_thread.start()
        
        # Open the authorization URL in the default browser
        print("Opening browser for Reddit authentication...")
        webbrowser.open(auth_url)
        
        # Wait for the authorization code
        while server.authorization_code is None:
            time.sleep(0.1)
        
        # Exchange the authorization code for an access token
        print("Authorization code received. Obtaining access token...")
        
        # Use the authorization code to obtain an access token
        access_token_data = {
            'grant_type': 'authorization_code',
            'code': server.authorization_code,
            'redirect_uri': self.redirect_uri
        }
        
        auth = requests.auth.HTTPBasicAuth(self.client_id, self.client_secret)
        headers = {'User-Agent': self.user_agent}
        
        response = requests.post(
            'https://www.reddit.com/api/v1/access_token',
            auth=auth,
            headers=headers,
            data=access_token_data
        )
        
        if response.status_code != 200:
            print(f"Failed to obtain access token. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            sys.exit(1)
            
        token_info = response.json()
        
        if 'access_token' not in token_info:
            print("Failed to obtain access token:", token_info)
            sys.exit(1)
            
        # Store token information
        self.access_token = token_info['access_token']
        self.refresh_token = token_info.get('refresh_token')
        self.token_expiration = int(time.time()) + token_info['expires_in']
        
        print("Authentication successful!")
        
    def refresh_access_token(self):
        """Refresh the access token if expired"""
        if not self.refresh_token:
            raise Exception("No refresh token available. Please authenticate first.")
            
        if time.time() < self.token_expiration - 60:
            return  # Token still valid
            
        print("Access token expired. Refreshing...")
        
        refresh_data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token
        }
        
        auth = requests.auth.HTTPBasicAuth(self.client_id, self.client_secret)
        headers = {'User-Agent': self.user_agent}
        
        response = requests.post(
            'https://www.reddit.com/api/v1/access_token',
            auth=auth,
            headers=headers,
            data=refresh_data
        )
        
        token_info = response.json()
        
        if 'access_token' not in token_info:
            print("Failed to refresh access token:", token_info)
            sys.exit(1)
            
        self.access_token = token_info['access_token']
        self.token_expiration = int(time.time()) + token_info['expires_in']
        print("Access token refreshed successfully!")
    
    def api_request(self, endpoint, params=None):
        """Make an authenticated API request to Reddit"""
        if not self.access_token:
            raise Exception("Not authenticated. Call authenticate() first.")
            
        self.refresh_access_token()
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'User-Agent': self.user_agent
        }
        
        response = requests.get(
            f'https://oauth.reddit.com{endpoint}',
            headers=headers,
            params=params
        )
        
        if response.status_code != 200:
            print(f"API request failed: {response.status_code} - {response.text}")
            return None
            
        return response.json()
    
    def get_followed_subreddits(self):
        """Get a list of subreddits followed by the authenticated user"""
        subreddits = []
        after = None
        
        while True:
            params = {'limit': 100}
            if after:
                params['after'] = after
                
            data = self.api_request('/subreddits/mine/subscriber', params)
            
            if not data or 'data' not in data or 'children' not in data['data']:
                break
                
            batch = [child['data']['display_name'] for child in data['data']['children']]
            subreddits.extend(batch)
            
            after = data['data'].get('after')
            if not after or len(batch) == 0:
                break
        
        return subreddits
    
    def get_rss_feeds(self, subreddits):
        """Generate RSS feed URLs for a list of subreddits"""
        rss_feeds = {}
        
        for subreddit in subreddits:
            # Reddit provides several RSS feed formats for each subreddit
            rss_feeds[subreddit] = {
                'new': f'https://www.reddit.com/r/{subreddit}/new/.rss',
                'hot': f'https://www.reddit.com/r/{subreddit}/hot/.rss',
                'rising': f'https://www.reddit.com/r/{subreddit}/rising/.rss',
                'top': f'https://www.reddit.com/r/{subreddit}/top/.rss',
                'controversial': f'https://www.reddit.com/r/{subreddit}/controversial/.rss',
            }
        
        return rss_feeds
    
    def save_to_file(self, rss_feeds, filename="RSS.txt"):
        """Save the RSS feeds to a text file"""
        with open(filename, 'a') as f:
            for feed in rss_feeds:
                f.write(f"{rss_feeds[feed]['new']}\n")
        print(f"RSS feeds saved to {filename}")

def create_sample_env_file():
    """Create a sample .env file if it doesn't exist"""
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write("""# Reddit API credentials
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
REDDIT_USERNAME=your_reddit_username_here
""")
        print("A sample .env file has been created. Please edit it with your Reddit API credentials.")
        return False
    return True

def main():
    # Check if .env file exists, create a sample one if it doesn't
    if not create_sample_env_file():
        sys.exit(1)
    
    # Get credentials from environment variables
    client_id = os.getenv('REDDIT_CLIENT_ID')
    client_secret = os.getenv('REDDIT_CLIENT_SECRET')
    username = os.getenv('REDDIT_USERNAME')
    
    # Check if credentials are properly set
    if not client_id or client_id == 'your_client_id_here':
        client_id = input("Enter your Reddit application client ID: ")
    
    if not client_secret or client_secret == 'your_client_secret_here':
        client_secret = input("Enter your Reddit application client secret: ")
    
    if not username or username == 'your_reddit_username_here':
        username = input("Enter your Reddit username: ")
    
    redirect_uri = "http://localhost:8000"
    user_agent = f"python:reddit-rss-fetcher:v1.0 (by /u/{username})"
    
    try:
        # Initialize the fetcher
        fetcher = RedditRSSFetcher(client_id, client_secret, redirect_uri, user_agent)
        
        # Authenticate
        fetcher.authenticate()
        
        # Get followed subreddits
        print("Fetching followed subreddits...")
        subreddits = fetcher.get_followed_subreddits()
        print(f"Found {len(subreddits)} followed subreddits:")
        for i, subreddit in enumerate(subreddits, 1):
            print(f"{i}. r/{subreddit}")
        
        # Generate RSS feeds
        print("\nGenerating RSS feed URLs...")
        rss_feeds = fetcher.get_rss_feeds(subreddits)
        
        # Save to file
        fetcher.save_to_file(rss_feeds)
        
        # Print example usage
        if subreddits:
            example = subreddits[0]
            print(f"\nExample RSS feed for r/{example}:")
            print(f"New posts: {rss_feeds[example]['new']}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()