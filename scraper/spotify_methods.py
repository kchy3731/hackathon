import base64
import json
import requests
import urllib.parse
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
from datetime import datetime
import sys
import os
from dotenv import load_dotenv
from scraper import article

load_dotenv()

# Get Spotify credentials from environment variables
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
#print(CLIENT_ID, CLIENT_SECRET)
REDIRECT_URI = "http://127.0.0.1:8888/callback"  # Ensure this matches exactly in Spotify Dashboard

# Spotify API endpoints
AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
FOLLOWED_ARTISTS_URL = "https://api.spotify.com/v1/me/following"
ARTIST_ALBUMS_URL = "https://api.spotify.com/v1/artists/{artist_id}/albums"

# Store the authorization code from the callback
auth_code = None

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        try:
            if '/callback' in self.path:
                # Extract the authorization code from the callback URL
                query_components = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                if 'code' in query_components:
                    auth_code = query_components['code'][0]
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(b'<html><body><h1>Authorization successful!</h1><p>You can close this window now.</p></body></html>')
                elif 'error' in query_components:
                    error = query_components['error'][0]
                    self.send_response(400)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(f'<html><body><h1>Authorization failed!</h1><p>Error: {error}</p></body></html>'.encode())
                    print(f"Authorization error: {error}")
                else:
                    self.send_response(400)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(b'<html><body><h1>Authorization failed!</h1><p>No authorization code received.</p></body></html>')
            else:
                self.send_response(404)
                self.end_headers()
        except Exception as e:
            print(f"Error in callback handler: {e}")
    
    def log_message(self, format, *args):
        # Silence the server logs
        return

def start_callback_server():
    try:
        server = HTTPServer(('127.0.0.1', 8888), CallbackHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        return server
    except Exception as e:
        print(f"Error starting server: {e}")
        raise

def get_authorization():
    # Start the local server to handle the callback
    server = start_callback_server()
    
    # Set required scopes for the authorization
    # We need user-follow-read to access followed artists
    scope = "user-follow-read"
    
    # Prepare the authorization URL
    auth_params = {
        'client_id': CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': REDIRECT_URI,
        'scope': scope,
        'show_dialog': 'true'  # Force showing the auth dialog
    }
    
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(auth_params)}"
    
    # Open the browser for the user to authorize
    print(f"Opening browser for authorization...")
    print(f"If the browser doesn't open automatically, visit this URL: {auth_url}")
    
    # Try different methods to open the browser
    try:
        webbrowser.open(auth_url)
    except:
        print("Failed to open browser automatically. Please copy and paste the URL above into your browser.")
    
    # Wait for the callback to receive the authorization code
    timeout = 180  # 3 minutes timeout
    start_time = time.time()
    while auth_code is None and time.time() - start_time < timeout:
        time.sleep(1)
    
    # Shutdown the server
    try:
        server.shutdown()
    except:
        pass
    
    if auth_code is None:
        raise Exception("Authorization timeout or failed.")
    
    return auth_code

def get_access_token(auth_code):
    # Encode client ID and client secret
    auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    
    # Prepare the token request
    token_data = {
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': REDIRECT_URI,
    }
    
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    # Make the token request
    try:
        response = requests.post(TOKEN_URL, data=token_data, headers=headers)
        
        if response.status_code != 200:
            print(f"Error getting token: {response.status_code}")
            print(response.json())
            raise Exception(f"Failed to get access token: {response.json().get('error_description', 'Unknown error')}")
        
        # Extract token info from the response
        token_info = response.json()
        return token_info
    except requests.exceptions.RequestException as e:
        print(f"Network error during token request: {e}")
        raise Exception("Network error during token request")

def get_followed_artists(access_token):
    """Get the list of artists followed by the user"""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # We're looking specifically for 'artist' type
    params = {
        'type': 'artist',
        'limit': 50  # Maximum allowed by Spotify API
    }
    
    artists = []
    
    # First request
    try:
        response = requests.get(FOLLOWED_ARTISTS_URL, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"Error getting followed artists: {response.status_code}")
            print(response.json())
            raise Exception(f"Failed to get followed artists: {response.json().get('error', {}).get('message', 'Unknown error')}")
        
        result = response.json()
        artists.extend(result['artists']['items'])
        
        # Handle pagination if there are more artists
        next_url = result['artists'].get('next')
        
        while next_url:
            response = requests.get(next_url, headers=headers)
            if response.status_code != 200:
                break
                
            result = response.json()
            artists.extend(result['artists']['items'])
            next_url = result['artists'].get('next')
        
        return artists
    except requests.exceptions.RequestException as e:
        print(f"Network error getting followed artists: {e}")
        raise Exception("Network error during API request")

def get_artist_latest_release(artist_id, access_token):
    """Get the latest release (album/single/EP) for a specific artist"""
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    # Get all albums, singles, and EPs for the artist
    params = {
        'include_groups': 'album,single,appears_on',
        'limit': 50,  # Maximum allowed by API
        'market': 'from_token'  # Use the user's market
    }
    
    try:
        response = requests.get(
            ARTIST_ALBUMS_URL.format(artist_id=artist_id), 
            headers=headers, 
            params=params
        )
        
        if response.status_code != 200:
            print(f"Error getting albums for artist {artist_id}: {response.status_code}")
            return None
        
        albums = response.json()['items']
        
        # Handle pagination if needed
        next_url = response.json().get('next')
        while next_url:
            response = requests.get(next_url, headers=headers)
            if response.status_code != 200:
                break
                
            result = response.json()
            albums.extend(result['items'])
            next_url = result.get('next')
        
        if not albums:
            return None
        
        # Filter out compilations and appearances where the artist isn't the main artist
        filtered_albums = []
        for album in albums:
            # Check if our artist is the first artist listed
            if artist_id == album['artists'][0]['id']:
                filtered_albums.append(album)
        
        # If we have no albums where our artist is the primary, use all albums
        if not filtered_albums:
            filtered_albums = albums
        
        # Sort by release date (newest first)
        sorted_albums = sorted(
            filtered_albums,
            key=lambda x: datetime.strptime(x['release_date'], '%Y-%m-%d' if len(x['release_date']) == 10 else '%Y'),
            reverse=True
        )
        
        # Return the most recent album
        if sorted_albums:
            return sorted_albums[0]
        return None
        
    except Exception as e:
        print(f"Error getting latest release for artist {artist_id}: {e}")
        return None

def latest_release_articles(artists_with_releases) -> list[article]:
    """Return the latest releases as articles"""
    if not artists_with_releases:
        return None
    
    articles = []
    
    for i, (artist, release) in enumerate(artists_with_releases):
        if not release:
            continue
            
        articles.append(article(
            source = "Spotify",
            title = f"{artist['name']} - {release['name']} ({release['album_type'].capitalize()})",
            description = f"Release Date: {release['release_date']}, Tracks: {release.get('total_tracks', 'N/A')}",
            content = f"Spotify: {release['external_urls']['spotify']}",
            timestamp = datetime.strptime(release['release_date'], '%Y-%m-%d' if len(release['release_date']) == 10 else '%Y'),
            link = release['external_urls']['spotify']
        ))
        
    return articles

def verify_credentials():
    if CLIENT_ID == "your_client_id" or CLIENT_SECRET == "your_client_secret":
        print("ERROR: You need to update the CLIENT_ID and CLIENT_SECRET in the script.")
        print("Get these from your Spotify Developer Dashboard: https://developer.spotify.com/dashboard/")
        return False
    return True

def snapshot():
    """
    Return a JSON output of all the latest releases sorted from most recent to least recent
    """
    try:
        # Verify credentials are set
        if not verify_credentials():
            return json.dumps({"error": "Invalid credentials"})
        
        # Get authorization code
        code = get_authorization()
        
        # Exchange the code for an access token
        token_info = get_access_token(code)
        access_token = token_info['access_token']
        
        # Get followed artists
        followed_artists = get_followed_artists(access_token)
        
        # Get the latest release for each artist
        artists_with_releases = []
        
        for artist in followed_artists:
            latest_release = get_artist_latest_release(artist['id'], access_token)
            if latest_release:
                # Add relevant data to our results
                release_data = {
                    "artist_name": artist['name'],
                    "artist_id": artist['id'],
                    "release_name": latest_release['name'],
                    "release_type": latest_release['album_type'],
                    "release_date": latest_release['release_date'],
                    "total_tracks": latest_release.get('total_tracks', 'N/A'),
                    "spotify_url": latest_release['external_urls']['spotify'],
                    "image_url": latest_release['images'][0]['url'] if latest_release['images'] else None
                }
                artists_with_releases.append(release_data)
        
        # Sort by release date (newest first)
        sorted_releases = sorted(
            artists_with_releases,
            key=lambda x: datetime.strptime(x['release_date'], '%Y-%m-%d' if len(x['release_date']) == 10 else '%Y'),
            reverse=True
        )
        
        return json.dumps(sorted_releases, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})
    
def add_all_artists():
    """
    Return a JSON output of all the latest releases sorted from most recent to least recent
    """
    if not verify_credentials():
        return
        
    # Step 1: Get the authorization code
    code = get_authorization()
    print("Authorization code received!")
    
    # Step 2: Exchange the code for an access token
    token_info = get_access_token(code)
    access_token = token_info['access_token']

    # Step 3: Get followed artists
    followed_artists = get_followed_artists(access_token)
    
    # Step 4: Get the latest release for each artist    
    artists_with_releases = []
    
    for i, artist in enumerate(followed_artists):
        latest_release = get_artist_latest_release(artist['id'], access_token)
        if latest_release:
            artists_with_releases.append((artist, latest_release))
    
    # Display the results
    return latest_release_articles(artists_with_releases)
    

def display_latest_releases(artists_with_releases):
    """Display the latest releases in a formatted way"""
    if not artists_with_releases:
        print("No releases found for your followed artists.")
        return
    
    print("\nLatest Releases from Your Followed Artists:")
    print("=" * 50)
    
    for i, (artist, release) in enumerate(artists_with_releases, 1):
        if not release:
            continue
            
        print(f"{i}. {artist['name']}")
        print(f"   Latest Release: {release['name']} ({release['album_type'].capitalize()})")
        print(f"   Release Date: {release['release_date']}")
        print(f"   Tracks: {release.get('total_tracks', 'N/A')}")
        print(f"   Spotify: {release['external_urls']['spotify']}")
        print("-" * 50)

def main():
    try:
        print("Spotify Followed Artists Latest Releases")
        print("======================================")
        
        # Verify credentials are set
        if not verify_credentials():
            return
        
        # Step 1: Get the authorization code
        print("Step 1/4: Getting authorization code...")
        code = get_authorization()
        print("Authorization code received!")
        
        # Step 2: Exchange the code for an access token
        print("\nStep 2/4: Getting access token...")
        token_info = get_access_token(code)
        access_token = token_info['access_token']
        print("Access token received!")
        
        # Step 3: Get followed artists
        print("\nStep 3/4: Fetching your followed artists...")
        followed_artists = get_followed_artists(access_token)
        print(f"Found {len(followed_artists)} followed artists.")
        
        # Step 4: Get the latest release for each artist
        print("\nStep 4/4: Finding the latest release for each artist...")
        print("This may take a moment...")
        
        artists_with_releases = []
        
        for i, artist in enumerate(followed_artists):
            sys.stdout.write(f"\rProcessing artist {i+1}/{len(followed_artists)}: {artist['name']}")
            sys.stdout.flush()
            
            latest_release = get_artist_latest_release(artist['id'], access_token)
            if latest_release:
                artists_with_releases.append((artist, latest_release))
        
        print("\nDone fetching latest releases!")
        
        # Display the results
        display_latest_releases(artists_with_releases)
        
        print(f"\nTotal: Found latest releases for {len(artists_with_releases)} out of {len(followed_artists)} followed artists.")
        
    except Exception as e:
        print(f"\nError: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure your CLIENT_ID and CLIENT_SECRET are correct")
        print("2. Verify your redirect URI in the Spotify Developer Dashboard matches exactly:")
        print(f"   {REDIRECT_URI}")
        print("3. Check that your app is registered correctly in the Spotify Developer Dashboard")
        print("4. Make sure you're following artists on Spotify")

if __name__ == "__main__":
    main()
