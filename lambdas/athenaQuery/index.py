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
DATABASE_NAME = os.getenv('DATABASE_NAME')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_output =  's3://' + BUCKET_NAME + '/twitter-ath-results/'
ath = boto3.client('athena')
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@xray_recorder.capture('## AthQuery')
def AthenaQuery(query_string, emotion):
    xray_recorder.put_annotation('Query', query_string)
    query_id = ath.start_query_execution(
        QueryString=query_string,
        QueryExecutionContext={
            'Database': DATABASE_NAME
        },
        ResultConfiguration={
            'OutputLocation': s3_output + emotion
        }
    )['QueryExecutionId']
    query_status = None
    while query_status == 'QUEUED' or query_status == 'RUNNING' or query_status is None:
        query_status = ath.get_query_execution(QueryExecutionId=query_id)['QueryExecution']['Status']['State']
        if query_status == 'FAILED' or query_status == 'CANCELLED':
            raise Exception('Athena query with the string "{}" failed or was cancelled'.format(query_string))
        time.sleep(2)
        results_paginator = ath.get_paginator('get_query_results')
        results_iter = results_paginator.paginate(
            QueryExecutionId=query_id,
            PaginationConfig={
                'PageSize': 1000
            }
        )
    results = []
    column_names = None
    for results_page in results_iter:
        for row in results_page['ResultSet']['Rows']:
           column_values = [col.get('VarCharValue', None) for col in row['Data']]
           if not column_names:
               column_names = column_values
           else:
               results.append(dict(zip(column_names, column_values)))
    
    return results
        
def handler(event, context):
    
        res = AthenaQuery(event["query"], event["type"])
        logger.debug(res)
        return res