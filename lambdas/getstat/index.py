# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
from datetime import datetime,timedelta
import decimal
import json
import urllib
import boto3
import logging
import csv
import os
from base64 import b64encode
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

patch_all()

s3_bucket = os.getenv('Bucket')
AthQueryLambdaName = os.getenv('AthQueryLambdaName')
ParserLambdaName = os.getenv('ParserLambdaName')
AthQueryLambdaName = os.getenv('AthQueryLambdaName')
ProcessFacesLambdaName = os.getenv('ProcessFacesLambdaName')
RekognitionLambdaName = os.getenv('RekognitionLambdaName')

logger = logging.getLogger()
logger.setLevel(logging.INFO)
ENCODING = 'utf-8'

client = boto3.client('cloudwatch')

metricWidget =  {
    "metrics": [
        [ "TwitterRekognition", "TweetsProcessed", "ServiceName", ParserLambdaName, "LogGroup", ParserLambdaName, "ServiceType", "AWS::Lambda::Function" ],
        [ ".", "ImagesIdentified", ".", ".", ".", ".", ".", "." ],
        [ ".", "FacesProcessed", ".", ProcessFacesLambdaName, ".", ProcessFacesLambdaName, ".", "." ],
        [ ".", "ImagesModerated", ".", RekognitionLambdaName, ".", RekognitionLambdaName, ".", "." ]
    ],
    "view": "timeSeries",
    "stacked": False,
    "stat": "Sum",
    "period": 86400,
    "width": 800,
    "height": 350,
    "start": "-P7D",
    "end": "P0D"
}


def GetMetric(lambdaName, metricName, daysDelta):

    endTime = datetime(datetime.now().year, datetime.now().month, datetime.now().day, datetime.now().hour, datetime.now().minute, 00)

    if daysDelta >= 5:
        period = 86400
    else:
        period = 21600

    startTime = endTime + timedelta(days=-daysDelta)
    
    response = client.get_metric_statistics(
        Namespace='TwitterRekognition',
        MetricName=metricName,
        Dimensions=[

            {
                'Name': 'ServiceName',
                'Value': lambdaName
            },
            {
                'Name': 'LogGroup',
                'Value': lambdaName
            },
            {
                'Name': 'ServiceType',
                'Value': 'AWS::Lambda::Function'
            }
        ],
        StartTime=startTime,
        EndTime=endTime,
        Period=period,
        Statistics=[
            'Sum'
        ],
        Unit='Count'
    )
    
    dtp_sum = 0
    for dtp in response["Datapoints"]:
        dtp_sum += dtp["Sum"]

    return "{:,}".format(dtp_sum).rstrip('0').rstrip('.')


def handler(event, context):
    try:
        
        TweetsProcessed = {}
        ImagesIdentified = {}
        ImagesModerated = {}
        FacesProcessed = {}

        TweetsProcessed["1"] = GetMetric(ParserLambdaName,'TweetsProcessed',1)
        TweetsProcessed["7"] = GetMetric(ParserLambdaName,'TweetsProcessed',7)
        TweetsProcessed["30"] = GetMetric(ParserLambdaName,'TweetsProcessed',30)
        
        ImagesIdentified["1"] = GetMetric(ParserLambdaName,'ImagesIdentified',1)
        ImagesIdentified["7"] = GetMetric(ParserLambdaName,'ImagesIdentified',7)
        ImagesIdentified["30"] = GetMetric(ParserLambdaName,'ImagesIdentified',30)
        
        ImagesModerated["1"] = GetMetric(RekognitionLambdaName,'ImagesModerated',1)
        ImagesModerated["7"] = GetMetric(RekognitionLambdaName,'ImagesModerated',7)
        ImagesModerated["30"] = GetMetric(RekognitionLambdaName,'ImagesModerated',30)
        
        FacesProcessed["1"] = GetMetric(ProcessFacesLambdaName,'FacesProcessed',1)
        FacesProcessed["7"] = GetMetric(ProcessFacesLambdaName,'FacesProcessed',7)
        FacesProcessed["30"] = GetMetric(ProcessFacesLambdaName,'FacesProcessed',30)

        response = client.get_metric_widget_image(
            MetricWidget = json.dumps(metricWidget),
            OutputFormat='png'
        )
        
        base64_bytes = b64encode(response["MetricWidgetImage"])
        base64_string = base64_bytes.decode(ENCODING)
        
        raw_data = { 'TweetsProcessed' : TweetsProcessed, 'ImagesIdentified': ImagesIdentified, 'FacesProcessed': FacesProcessed, 'ImagesModerated': ImagesModerated, 
        'MetricWidgetImage': base64_string }

        return json.dumps(raw_data)

    except Exception as e:
        logger.error('Something went wrong: ' + str(e))
        return {'result': False, 'msg': str(e)}