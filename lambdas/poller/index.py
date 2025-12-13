import json
import os
import time
from datetime import datetime, timezone

import boto3
import tweepy
from aws_xray_sdk.core import xray_recorder
from aws_embedded_metrics import metric_scope

from boto3.dynamodb.conditions import Attr, Or
from botocore.exceptions import ClientError

LAMBDA = boto3.client('lambda')
SSM = boto3.client('ssm')
DDB = boto3.resource('dynamodb')
TABLE = DDB.Table(os.getenv('SEARCH_CHECKPOINT_TABLE_NAME'))
RECORD_KEY = 'checkpoint'

SEARCH_TEXT = os.getenv('SEARCH_TEXT')
TWEET_PROCESSOR_FUNCTION_NAME = os.getenv('TWEET_PROCESSOR_FUNCTION_NAME')
BATCH_SIZE = int(os.getenv('BATCH_SIZE'))

SSM_PARAMETER_PREFIX = os.getenv("SSM_PARAMETER_PREFIX")
BEARER_TOKEN_PARAM_NAME = '/{}/bearer_token'.format(SSM_PARAMETER_PREFIX)

# Rate limiting constants
MAX_RETRIES = 3
RETRY_DELAY = 60  # seconds
MAX_RESULTS_PER_REQUEST = 100

@xray_recorder.capture('poller_handler')
@metric_scope
def handler(event, context, metrics):
    """Poll X API v2 for tweets and process in batches with improved rate limiting."""
    start_time = datetime.now(timezone.utc)
    total_tweets = 0
    total_batches = 0
    
    try:
        for batch in _search_batches():
            LAMBDA.invoke(
                FunctionName=TWEET_PROCESSOR_FUNCTION_NAME,
                InvocationType='Event',
                Payload=json.dumps(batch)
            )
            total_tweets += len(batch)
            total_batches += 1
        
        # Record metrics
        metrics.put_metric("TweetsPolled", total_tweets, "Count")
        metrics.put_metric("BatchesProcessed", total_batches, "Count")
        metrics.put_metric("PollingDuration", (datetime.now(timezone.utc) - start_time).total_seconds(), "Seconds")
        
        print(f"Successfully processed {total_tweets} tweets in {total_batches} batches")
        
    except Exception as e:
        metrics.put_metric("PollingErrors", 1, "Count")
        print(f"Error in polling handler: {e}")
        raise

def _search_batches():
    since_id = last_id()
    
    # Single API call to get all tweets
    result = search(SEARCH_TEXT, since_id)
    if not result:
        return
    
    all_tweets = result
    if not all_tweets:
        return
    
    # Process in batches
    size = len(all_tweets)
    newest_id = max(int(tweet['id']) for tweet in all_tweets)
    
    for i in range(0, size, BATCH_SIZE):
        batch = all_tweets[i:min(i + BATCH_SIZE, size)]
        yield batch
    
    # Update checkpoint only after all batches are processed
    update_checkpoint_atomic(str(newest_id), since_id)

def last_id():
    """Return last checkpoint tweet id."""
    result = TABLE.get_item(
        Key={'id': RECORD_KEY}
    )
    if 'Item' in result:
        return result['Item']['since_id']
    return None


def update_checkpoint_atomic(new_since_id, expected_since_id):
    """Atomically update checkpoint with optimistic locking."""
    try:
        if expected_since_id:
            # Update only if checkpoint hasn't changed
            TABLE.put_item(
                Item={
                    'id': RECORD_KEY,
                    'since_id': new_since_id,
                    'updated_at': int(time.time())
                },
                ConditionExpression=Attr('since_id').eq(expected_since_id)
            )
        else:
            # First time setup
            TABLE.put_item(
                Item={
                    'id': RECORD_KEY,
                    'since_id': new_since_id,
                    'updated_at': int(time.time())
                },
                ConditionExpression=Attr('id').not_exists()
            )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            print(f"Checkpoint changed during execution, skipping update")
        else:
            raise


@xray_recorder.capture('search_tweets')
def search(search_text, since_id=None):
    """Search for tweets with improved rate limiting and error handling."""
    for attempt in range(MAX_RETRIES):
        try:
            # Build query parameters with enhanced selfie-specific search
            query_params = {
                'query': f'({search_text} OR "taking a selfie" OR "my selfie" OR "#selfie") has:images -is:retweet',
                'max_results': MAX_RESULTS_PER_REQUEST,
                'tweet_fields': ['id', 'text', 'attachments', 'created_at'],
                'expansions': ['attachments.media_keys'],
                'media_fields': ['type', 'url', 'preview_image_url', 'width', 'height']
            }
            
            if since_id:
                query_params['since_id'] = since_id
            
            # Search recent tweets
            response = X_CLIENT.search_recent_tweets(**query_params)
            
            if not response.data:
                return []
            
            # Build media lookup from includes
            media_lookup = {}
            if response.includes and 'media' in response.includes:
                for media in response.includes['media']:
                    media_lookup[media.media_key] = media
            
            # Transform X API v2 format to match parser expectations
            transformed_tweets = []
            for tweet in response.data:
                # Check if tweet has media attachments
                if not hasattr(tweet, 'attachments') or not tweet.attachments:
                    continue
                
                media_keys = tweet.attachments.get('media_keys', [])
                if not media_keys:
                    continue
                
                # Build extended_entities structure for parser compatibility
                media_entities = []
                for media_key in media_keys:
                    if media_key not in media_lookup:
                        continue
                    
                    media = media_lookup[media_key]
                    # Only process photos with minimum dimensions
                    if (media.type == 'photo' and 
                        hasattr(media, 'width') and hasattr(media, 'height') and
                        media.width >= 200 and media.height >= 200):
                        media_entities.append({
                            'id_str': str(tweet.id),
                            'media_url_https': media.url,
                            'type': 'photo'
                        })
                
                if media_entities:
                    transformed_tweets.append({
                        'id': str(tweet.id),
                        'id_str': str(tweet.id),
                        'full_text': tweet.text,
                        'extended_entities': {
                            'media': media_entities
                        }
                    })
            
            return transformed_tweets
            
        except tweepy.TooManyRequests:
            if attempt < MAX_RETRIES - 1:
                print(f"Rate limit hit, waiting {RETRY_DELAY} seconds (attempt {attempt + 1})")
                time.sleep(RETRY_DELAY)
                continue
            else:
                print("Rate limit exceeded, max retries reached")
                return []
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                print(f"Error searching tweets (attempt {attempt + 1}): {e}")
                time.sleep(RETRY_DELAY // 2)
                continue
            else:
                print(f"Final error searching tweets: {e}")
                return []
    
    return []


def _create_x_client():
    """Create X API v2 client with Bearer Token authentication."""
    result = SSM.get_parameters(
        Names=[BEARER_TOKEN_PARAM_NAME],
        WithDecryption=True
    )

    if result['InvalidParameters']:
        raise RuntimeError(
            'Could not find expected SSM parameter containing X API Bearer Token: {}'.format(BEARER_TOKEN_PARAM_NAME))

    param_lookup = {param['Name']: param['Value'] for param in result['Parameters']}
    bearer_token = param_lookup[BEARER_TOKEN_PARAM_NAME]

    return tweepy.Client(bearer_token=bearer_token, wait_on_rate_limit=True)


X_CLIENT = _create_x_client()

