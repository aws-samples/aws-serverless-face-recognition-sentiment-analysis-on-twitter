# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
from datetime import datetime, timedelta
import json
import urllib
import boto3
import logging
import uuid
import urllib 
import io
import os
import requests
from time import sleep
from aws_embedded_metrics import metric_scope
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

patch_all()

S3Bucket = os.getenv('Bucket')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
s3_bucket = S3Bucket

rek = boto3.client('rekognition')

status = ["success", "error", "moderated"]
year_week = datetime.now().strftime("%Y-W%U")
year_month = datetime.now().strftime("%Y-%m")
    
@metric_scope
def handler(event, context, metrics):   
        
    r = requests.get(event["image_url"], allow_redirects=True)

    attributes=[]
    attributes.append("DEFAULT")
    attributes.append("ALL")

    retries = 0
    while (retries < 5):
        try:
            xray_recorder.begin_subsegment('## Moderation')
            mod_response = rek.detect_moderation_labels(
                Image={
                    'Bytes': r.content
                },
                MinConfidence=50
            )
            xray_recorder.end_subsegment()
            break

        except Exception as e:
            logger.error(str(e))                 
            retries = retries + 1
            logger.info("sleeps: " + str(pow(2, retries) * 0.15))
            sleep(pow(2, retries) * 0.15)            
            if retries == 5:
                logger.error("Error: Moderation backoff limit")
                return {'result': 'Fail', 'msg': str(e) + " Moderation backoff limit"} 
            else:
                continue

    if len(mod_response["ModerationLabels"]) != 0:
        metrics.set_namespace('TwitterRekognition')
        metrics.put_metric("ImagesModerated", 1, "Count")
        metrics.set_property("RequestId", context.aws_request_id)        
        metrics.set_property("Labels", mod_response["ModerationLabels"])
        return {'result': 'Moderated' }

    retries = 0
    while (retries < 5):
        try:
            xray_recorder.begin_subsegment('## DetectFaces')            
            rek_response = rek.detect_faces(
                Image={"Bytes": r.content},
                Attributes=attributes
            )
            xray_recorder.end_subsegment()
            break

        except Exception as e:
            logger.error(str(e))                 
            retries = retries + 1
            logger.info("sleeps: " + str(pow(2, retries) * 0.15))
            sleep(pow(2, retries) * 0.15)
            if retries == 5:
                logger.error("Error: FaceDetect backoff limit")
                return {'result': 'Fail', 'msg': str(e) + " FaceDetect backoff limit"} 
            else:
                continue

    logger.info("FaceDetails: " + str(len(rek_response["FaceDetails"])))

    if len(rek_response["FaceDetails"]) > 0:
        hdata = {}
        hdata['image_url'] = str(event["image_url"])
        hdata['full_text'] = event['full_text']
        hdata['facerecords'] = rek_response["FaceDetails"]
        hdata['tweet_id'] = event["tweet_id"]

        faces_count = len(rek_response["FaceDetails"])
        return {'result': 'Succeed', 'count': str(faces_count), 'data': json.dumps(hdata)}
        
    else:
        logger.error('Unable to rekognize any face')
        return {'result': 'Fail', 'msg': 'Unable to rekognize face'}