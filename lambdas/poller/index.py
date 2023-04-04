import json
import os
import sys

import boto3
import twitter

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
CONSUMER_KEY_PARAM_NAME = '/{}/consumer_key'.format(SSM_PARAMETER_PREFIX)
CONSUMER_SECRET_PARAM_NAME = '/{}/consumer_secret'.format(SSM_PARAMETER_PREFIX)
ACCESS_TOKEN_PARAM_NAME = '/{}/access_token'.format(SSM_PARAMETER_PREFIX)
ACCESS_TOKEN_SECRET_PARAM_NAME = '/{}/access_token_secret'.format(SSM_PARAMETER_PREFIX)

def handler(event, context):
    """Forward SQS messages to Kinesis Firehose Delivery Stream."""
    for batch in _search_batches():
        LAMBDA.invoke(
            FunctionName=TWEET_PROCESSOR_FUNCTION_NAME,
            InvocationType='Event',
            Payload=json.dumps(batch)
        )

def _search_batches():
    since_id = last_id()

    tweets = []
    while True:
        result = search(SEARCH_TEXT, since_id)
        if not result['statuses']:
            # no more results
            break

        tweets = result['statuses']
        size = len(tweets)
        for i in range(0, size, BATCH_SIZE):
            yield tweets[i:min(i + BATCH_SIZE, size)]
        since_id = result['search_metadata']['max_id']
        update(since_id)

def last_id():
    """Return last checkpoint tweet id."""
    result = TABLE.get_item(
        Key={'id': RECORD_KEY}
    )
    if 'Item' in result:
        return result['Item']['since_id']
    return None


def update(since_id):
    """Update checkpoint to given tweet id."""
    try:
        TABLE.put_item(
            Item={
                'id': RECORD_KEY,
                'since_id': since_id
            },
            ConditionExpression=Or(
                Attr('id').not_exists(),
                Attr('since_id').lt(since_id)
            )
        )
    except ClientError as e:
        if e.response['Error']['Code'] != 'ConditionalCheckFailedException':
            raise


def search(search_text, since_id=None):
    """Search for tweets matching the given search text."""
    return TWITTER.GetSearch(term=search_text, count=100, return_json=True, since_id=since_id)


def _create_twitter_api():
    parameter_names = [
            CONSUMER_KEY_PARAM_NAME,
            CONSUMER_SECRET_PARAM_NAME,
            ACCESS_TOKEN_PARAM_NAME,
            ACCESS_TOKEN_SECRET_PARAM_NAME
    ]
    result = SSM.get_parameters(
        Names=parameter_names,
        WithDecryption=True
    )

    if result['InvalidParameters']:
        raise RuntimeError(
            'Could not find expected SSM parameters containing Twitter API keys: {}'.format(parameter_names))

    param_lookup = {param['Name']: param['Value'] for param in result['Parameters']}

    return twitter.Api(
        consumer_key=param_lookup[CONSUMER_KEY_PARAM_NAME],
        consumer_secret=param_lookup[CONSUMER_SECRET_PARAM_NAME],
        access_token_key=param_lookup[ACCESS_TOKEN_PARAM_NAME],
        access_token_secret=param_lookup[ACCESS_TOKEN_SECRET_PARAM_NAME],
        tweet_mode='extended'
    )


TWITTER = _create_twitter_api()

