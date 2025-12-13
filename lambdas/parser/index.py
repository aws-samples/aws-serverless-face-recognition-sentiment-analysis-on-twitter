# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import os
import re
import json
import sys
import time
import boto3
import base64
import logging
from aws_embedded_metrics import metric_scope
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

patch_all()

DDB_IMAGE_TABLE = os.getenv('DDB_IMAGE_TABLE')
STATE_MACHINE_ARN = os.getenv('STATE_MACHINE_ARN')

rek = boto3.client('rekognition')
dynamodb = boto3.resource("dynamodb")
dyn_table = dynamodb.Table(DDB_IMAGE_TABLE)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

@xray_recorder.capture('## GetDynamo')
def GetImage(url):
    try:
        response = dyn_table.query(
        KeyConditionExpression=Key('img_url').eq(str(url))
        )
        return response

    except ClientError as e:
        logger.error(e.response['Error']['Message'])
        return {'Items': [], 'Count': 0}

@xray_recorder.capture('## AddDynamo')            
def AddImage(url,tweet_id):
    try:
        epoch = datetime.utcfromtimestamp(0)
        epochexp = (datetime.now()+timedelta(days=15) - epoch).total_seconds() * 1000.0
        response = dyn_table.put_item(
        Item={
            'img_url': str(url),
            'tweet_id': tweet_id,
            'expire_at': int(epochexp)
            }
        )
        return response

    except ClientError as e:
        logger.error(e.response['Error']['Message'])
    return {'Items': [], 'Count': 0}

@xray_recorder.capture('## Calling StepFunction')
def CallStepFunction(tweet):
    client = boto3.client('stepfunctions') 
    # Add timestamp to ensure unique execution names
    execution_name = f"{tweet['tweet_id']}-{int(time.time() * 1000)}"
    response = client.start_execution(
        stateMachineArn=STATE_MACHINE_ARN,
        name=execution_name,
        input=json.dumps(tweet)
    )
    AddImage(tweet["image_url"],tweet["tweet_id"])
    #logger.info(json.dumps(hdata))    

@metric_scope
def handler(event, context, metrics):
    """Process tweet batches from poller with improved error handling."""
    skipped_count = 0
    processed_count = 0
    no_image = 0
    error_count = 0
    
    try:
        for rec in event:
            try:
                if "extended_entities" in rec:            
                    if "media" in rec["extended_entities"]:
                        for m in rec["extended_entities"]["media"]:
                            if "media_url_https" in m:
                                if m["type"] == "photo":
                                    dyn_resp = GetImage(m["media_url_https"])
                                    if dyn_resp["Count"] == 0:
                                        processed_count += 1
                                        CallStepFunction({'tweet_id': m["id_str"], 'full_text': rec["full_text"], 'image_url': m["media_url_https"]})
                                    else:
                                        skipped_count += 1                            
                                else:
                                    no_image += 1
                            else:
                                no_image += 1
                    else:
                        no_image += 1
                else:
                    no_image += 1
            except Exception as e:
                error_count += 1
                logger.error(f"Error processing tweet {rec.get('id', 'unknown')}: {e}")

        # Align metrics with poller namespace
        metrics.set_namespace('XSentimentAnalysis')
        metrics.put_metric("TweetsProcessed", len(event), "Count")
        metrics.put_metric("ImagesIdentified", processed_count, "Count")
        metrics.put_metric("ImagesSkipped", skipped_count, "Count")
        metrics.put_metric("ProcessingErrors", error_count, "Count")
        metrics.set_property("RequestId", context.aws_request_id)
        metrics.set_property(
            "payload", { "tweets": str(len(event)) ,"processed": processed_count, "skipped": skipped_count, "no_image": no_image, "errors": error_count }
        )

        return True
        
    except Exception as e:
        logger.error(f"Critical error in parser handler: {e}")
        metrics.put_metric("CriticalErrors", 1, "Count")
        raise