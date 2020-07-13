# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
from datetime import datetime, timedelta
import decimal
import json
import urllib
import boto3
import logging
import csv
import os
import base64
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

patch_all()

s3_bucket = os.getenv('Bucket')
AthQueryLambdaName = os.getenv('AthQueryLambdaName')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

lambda_client = boto3.client('lambda')

def handler(event, context):
    try:   
        if 'emotion' not in event["queryStringParameters"]:
            logger.error( 'Missing parameters')
            return {'result': False, 'msg': 'Missing parameters' }
            
        print(event["queryStringParameters"]["emotion"])
        emotion = event["queryStringParameters"]["emotion"]

        query_str = """
        with twitter_emotions as (
            select face_id, image_url, first_name, last_name, (agerange.low + agerange.high)/2 as age, 
            gender.value as gender_value, emotion.type as etype, 
            round(emotion.confidence,3) as confidence, full_text,
            bbox_left, bbox_top, bbox_width, bbox_height,
            imgWidth, imgHeight, sentiment, updated_at
            from twitter_data.parquet_records TABLESAMPLE BERNOULLI (50)
            cross JOIN UNNEST(emotions) as t(emotion)
            where emotion.type = '%s'
            order by confidence desc
            LIMIT 1
        )
        select * from twitter_emotions           
        """ % (emotion)

        payload = {}
        payload["type"] = emotion
        payload["query"] = query_str

        response = lambda_client.invoke(
            FunctionName=AthQueryLambdaName,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        data = json.loads(response['Payload'].read())
        
        logger.info(data[0])
        
        return data[0]

    except Exception as e:
        logger.error('Something went wrong: ' + str(e))
        return {'result': False, 'msg': str(e)}