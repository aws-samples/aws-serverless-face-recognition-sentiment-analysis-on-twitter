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
from aws_embedded_metrics import metric_scope
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

patch_all()

S3Bucket = os.getenv('Bucket')
CollectionId = os.getenv('CollectionId')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
s3_bucket = S3Bucket

rek = boto3.client('rekognition')

status = ["success", "error", "moderated"]
year_week = datetime.now().strftime("%Y-W%U")
year_month = datetime.now().strftime("%Y-%m")

@xray_recorder.capture('## rek.create_collection Init')
def Initialize():    
    try:
        rek.create_collection(
        CollectionId=CollectionId,
    )
    except Exception as e:
        logger.warning(e)
    
@metric_scope
def handler(event, context, metrics):
    try:        
        
        r = requests.get(event["image_url"], allow_redirects=True)

        attributes=[]
        attributes.append("DEFAULT")
        attributes.append("ALL")

        xray_recorder.begin_subsegment('## Moderation')
        mod_response = rek.detect_moderation_labels(
            Image={
                'Bytes': r.content
            },
            MinConfidence=50
        )
        xray_recorder.end_subsegment()

        if len(mod_response["ModerationLabels"]) != 0:
            metrics.set_namespace('TwitterRekognition')
            metrics.put_dimensions({"step": "Rekognition"})
            metrics.put_metric("ImagesModerated", 1, "Count")
            metrics.set_property("RequestId", context.aws_request_id)
            metrics.set_property("LambdaName", context.function_name)
            metrics.set_property("Labels", mod_response["ModerationLabels"])
            return {'result': 'Moderated' }

        xray_recorder.begin_subsegment('## IndexFaces')
        rek_response = rek.index_faces(
            Image={"Bytes": r.content},
            CollectionId=CollectionId,
            DetectionAttributes=attributes
        )
        xray_recorder.end_subsegment()

        if 'FaceRecords' in rek_response:
            hdata = {}
            hdata['image_url'] = str(event["image_url"])
            hdata['full_text'] = event['full_text']
            hdata['facerecords'] = rek_response["FaceRecords"]
            hdata['collectionname'] = CollectionId
            hdata['guidstr'] = event["guidstr"]

            faces_count = len(rek_response["FaceRecords"])
            return {'result': 'Succeed', 'count': str(faces_count), 'data': json.dumps(hdata)}
            
        else:
            logger.error('Unable to rekognize any face')
            return {'result': 'Fail', 'msg': 'Unable to rekognize face'}

    except Exception as e:
        logger.error(str(e))
        # Reckoginition Collection
        Initialize()
        return {'result': 'Fail', 'msg': str(e)}