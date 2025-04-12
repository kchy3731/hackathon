import tweepy
import json
import datetime
import argparse
import os
from dotenv import load_dotenv

def authenticate_twitter():
    """
    Authenticate with Twitter API using OAuth credentials
    """
    # Load credentials from environment variables
    load_dotenv()
    
    consumer_key = os.getenv('TWITTER_CONSUMER_KEY')
    consumer_secret = os.getenv('TWITTER_CONSUMER_SECRET')
    access_token = os.getenv('TWITTER_ACCESS_TOKEN')
    access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
    
    # Authenticate with Twitter
    auth = tweepy.OAuth1UserHandler(
        consumer_key, 
        consumer_secret,
        access_token, 
        access_token_secret
    )
    
    # Create API object
    api = tweepy.API(auth, wait_on_rate_limit=True)
    
    return api

def get_followed_accounts(api):
    """
    Get a list of accounts that the authenticated user follows
    
    Args:
        api: Authenticated tweepy API object
        
    Returns:
        List of user IDs
    """
    followed_ids = []
    for user in tweepy.Cursor(api.get_friends).items():
        followed_ids.append(user.id)
    
    return followed_ids

def get_tweets_since_timestamp(api, user_ids, timestamp):
    """
    Get tweets from specified users posted after a given timestamp
    
    Args:
        api: Authenticated tweepy API object
        user_ids: List of user IDs to fetch tweets from
        timestamp: Datetime object representing the cutoff time
        
    Returns:
        List of tweet objects
    """
    all_tweets = []
    
    for user_id in user_ids:
        try:
            # Get tweets from this user
            tweets = tweepy.Cursor(
                api.user_timeline,
                user_id=user_id,
                count=200,  # Max tweets per request
                tweet_mode='extended'  # Get full tweet text
            ).items()
            
            # Filter tweets posted after timestamp
            for tweet in tweets:
                if tweet.created_at > timestamp:
                    # Convert tweet to dictionary
                    tweet_dict = {
                        'id': tweet.id_str,
                        'created_at': tweet.created_at.isoformat(),
                        'text': tweet.full_text,
                        'user': {
                            'id': tweet.user.id_str,
                            'screen_name': tweet.user.screen_name,
                            'name': tweet.user.name
                        },
                        'retweet_count': tweet.retweet_count,
                        'favorite_count': tweet.favorite_count,
                        'is_retweet': hasattr(tweet, 'retweeted_status')
                    }
                    
                    # Add media information if available
                    if hasattr(tweet, 'extended_entities') and 'media' in tweet.extended_entities:
                        tweet_dict['media'] = tweet.extended_entities['media']
                    
                    all_tweets.append(tweet_dict)
                else:
                    # Tweets are typically in chronological order, so we can break once we hit older tweets
                    break
        except Exception as e:
            print(f"Error fetching tweets for user {user_id}: {e}")
    
    return all_tweets

def main():
    # Parse command line arguments
    # parser = argparse.ArgumentParser(description='Fetch tweets from followed accounts since a specific timestamp')
    # parser.add_argument('--timestamp', type=str, required=True, 
    #                     help='Timestamp in ISO format (YYYY-MM-DDTHH:MM:SS)')
    # parser.add_argument('--output', type=str, default='tweets.json',
    #                     help='Output file name')
    # args = parser.parse_args()
    
    # Parse timestamp
    timestamp = datetime.datetime.now() - datetime.timedelta(days=1)
    
    # Authenticate with Twitter
    api = authenticate_twitter()
    
    # Get followed accounts
    print("Fetching followed accounts...")
    followed_ids = get_followed_accounts(api)
    print(f"Found {len(followed_ids)} followed accounts")
    
    # Get tweets since timestamp
    print(f"Fetching tweets posted after {timestamp.isoformat()}...")
    tweets = get_tweets_since_timestamp(api, followed_ids, timestamp)
    print(f"Found {len(tweets)} tweets")
    
    # Save tweets to file
    # with open(args.output, 'w', encoding='utf-8') as f:
    #     json.dump(tweets, f, ensure_ascii=False, indent=2)
    
    # print(f"Tweets saved to {args.output}")

if __name__ == "__main__":
    main()
