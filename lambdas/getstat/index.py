# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
from datetime import datetime,timedelta, timezone
import json
import boto3
import logging
import os
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

patch_all()

logger = logging.getLogger()
logger.setLevel(logging.INFO)
ENCODING = 'utf-8'

s3_bucket = os.getenv('Bucket')
AthQueryLambdaName = os.getenv('AthQueryLambdaName')
ParserLambdaName = os.getenv('ParserLambdaName')
AthQueryLambdaName = os.getenv('AthQueryLambdaName')
ProcessFacesLambdaName = os.getenv('ProcessFacesLambdaName')
RekognitionLambdaName = os.getenv('RekognitionLambdaName')

client = boto3.client('cloudwatch')

def _response_proxy(status_code, body, headers={}):
    if bool(headers): # Return True if dictionary is not empty
        return {"statusCode": status_code, "body": json.dumps(body), "headers": headers}
    else:
        return {"statusCode": status_code, "body": json.dumps(body)}

def GetMetric(lambdaName, metricName, unit, statType):
    cdata = []
    month_ago=datetime.utcnow() - timedelta(days=30)
    week_ago=datetime.utcnow() - timedelta(days=7)
    day_ago=datetime.utcnow() - timedelta(days=1)
    
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
        EndTime=datetime.utcnow(),
        StartTime=month_ago,
        Period=7200,
        Statistics=[statType],
        Unit=unit
    )

    if len(response["Datapoints"]) == 0:
        return None
    else:
        dtp_sum_one = 0
        dtp_sum_seven = 0
        dtp_sum_total = 0
        for rec in response["Datapoints"]:
            dtp_sum_total += rec[statType]
            cdata.append({'y': round(rec[statType], 2), 'x': rec["Timestamp"].strftime("%Y/%m/%dT%H:%M:%S")})
            if rec["Timestamp"].replace(tzinfo=None) > day_ago:
                dtp_sum_one += rec[statType]
            if rec["Timestamp"].replace(tzinfo=None) > week_ago:
                dtp_sum_seven += rec[statType]
                                        
        data_points = sorted(cdata, key=lambda k : k['x'])
        dtp_sum_one_formatted = "{:,}".format(dtp_sum_one).rstrip('0').rstrip('.')
        dtp_sum_seven_formatted = "{:,}".format(dtp_sum_seven).rstrip('0').rstrip('.')
        dtp_sum_total_formatted = "{:,}".format(dtp_sum_total).rstrip('0').rstrip('.')

        return { 'data': data_points, 'aggregation': { 'one': dtp_sum_one_formatted, 'seven': dtp_sum_seven_formatted, 'total': dtp_sum_total_formatted } }


def handler(event, context):
    try:
        
        TweetsProcessed = GetMetric(ParserLambdaName,'TweetsProcessed', 'Count', 'Sum')
        ImagesIdentified = GetMetric(ParserLambdaName,'ImagesIdentified','Count', 'Sum')    
        ImagesModerated = GetMetric(RekognitionLambdaName,'ImagesModerated', 'Count', 'Sum')
        FacesProcessed = GetMetric(ProcessFacesLambdaName,'FacesProcessed', 'Count', 'Sum')
        
        raw_data = { 'TweetsProcessed' : TweetsProcessed, 'ImagesIdentified': ImagesIdentified, 'FacesProcessed': FacesProcessed, 'ImagesModerated': ImagesModerated }
        
        headers = {
           'Content-Type': 'application/json', 
           'Access-Control-Allow-Origin': '*' 
        }
        
        return _response_proxy(200, raw_data, headers)

    except Exception as e:
        logger.error('Something went wrong: ' + str(e))
        resp = {'result': False, 'msg': str(e)}
        return _response_proxy(500,resp)