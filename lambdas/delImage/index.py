# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
from datetime import datetime
from datetime import timedelta
import json
import urllib
import boto3
import logging
import time
import os
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

patch_all()

BUCKET_NAME = os.getenv('BUCKET_NAME')
FIREHOSE_NAME = os.getenv('FIREHOSE_NAME')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

print('Loading function')

client = boto3.client('s3')
s3 = boto3.resource('s3')

payload = {}

today = datetime.now()

def handler(event, context):
    try:
        #logger.info(event)        
        if 'body' not in event:
            logger.error( 'Missing parameters')
            return {'result': False, 'msg': 'Missing parameters' }
            
        body = json.loads(event['body'])
        tweet = body["tweet"]
        dt = datetime.fromisoformat(tweet["updated_at"])
        
        s3_key = "parquet-" + str(today.year) + "/"

        name_updated_at = s3_key + FIREHOSE_NAME + "-1-" + dt.strftime("%Y-%m-%d-%H")
        pos_datetime = len(name_updated_at)+6 #adding characters for minute

        response = client.list_objects_v2(
            Bucket=BUCKET_NAME,          
            MaxKeys=60,
            Prefix=name_updated_at
        )        

        s3_files = response["Contents"]
        print("updated_at")
        print(dt)
        for file in s3_files:            
            timestamp_min = file["Key"][pos_datetime-19:pos_datetime]
            sdate = timestamp_min[0:10]
            stime = timestamp_min[11:].replace("-",":")            
            dt_utc_file = datetime.fromisoformat(sdate + "T" + stime)
            print(file["Key"])
            print(dt_utc_file)
            if dt_utc_file > dt:
                s3.Object(BUCKET_NAME, file["Key"]).delete()                
                print('DELETED: ' + file["Key"]) 
                break
                               
        return {'result': True}

    except Exception as e:
        logger.error('Something went wrong: ' + str(e))
        return {'result': False, 'msg': str(e)}