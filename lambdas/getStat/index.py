# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
from datetime import datetime,timedelta, timezone
import json
import boto3
import logging
import os
import pandas as pd
# from aws_xray_sdk.core import xray_recorder
# from aws_xray_sdk.core import patch_all

# patch_all()

logger = logging.getLogger()
logger.setLevel(logging.INFO)
ENCODING = 'utf-8'

AthQueryLambdaName = os.getenv('AthQueryLambdaName')
ParserLambdaName = os.getenv('ParserLambdaName')
AthQueryLambdaName = os.getenv('AthQueryLambdaName')
ProcessFacesLambdaName = os.getenv('ProcessFacesLambdaName')
RekognitionLambdaName = os.getenv('RekognitionLambdaName')

def _response_proxy(status_code, body, headers={}):
    if bool(headers): # Return True if dictionary is not empty
        return {"statusCode": status_code, "body": json.dumps(body), "headers": headers}
    else:
        return {"statusCode": status_code, "body": json.dumps(body)}

class CWChartDataFactory:
    def __init__(self):
        logger.info("------- Utils Class Initialization")
        self.cw = boto3.client('cloudwatch')
        self.metric_groups = {}
        
    def _add_group_metric(self, group_name, lambda_name, metric_name, unit, stat_type):

        if group_name not in self.metric_groups:
            self.metric_groups[group_name] = []            

        self.metric_groups[group_name].append(
            { 'metricName':metric_name, 'lambdaName': lambda_name, 'unit': unit, 'statType': stat_type }
        )

    def _build_group_data(self, group_name): 

        chart_options = {}
        metrics_results = {}
        metrics_charts = {}
        chart_1_key_list = []
        chart_2_key_list = []
        chart_3_key_list = []

        if group_name == 'days':
            period = 300
            days = 2
            chart_options["chart_1_frequency"]="30T"
            chart_options["chart_1_date_format"]="%d %H:%M"
        elif group_name == 'month':
            period = 1800
            days = 30
            chart_options["chart_1_frequency"]="W"
            chart_options["chart_1_date_format"]="%b %d"
            chart_options["chart_2_frequency"]="7D"
            chart_options["chart_2_date_format"]="%b %d"
        elif group_name == 'year':
            period = 23400 # 6 hours
            days = 365
            chart_options["chart_1_frequency"]="Y"
            chart_options["chart_1_date_format"]="%Y"
            chart_options["chart_2_frequency"]="M"
            chart_options["chart_2_date_format"]="%b %YY"
        else:
            return None

        for rec in self.metric_groups[group_name]:
            logger.info(rec['metricName'])
            chart_data = self._get_metric(rec['lambdaName'],rec['metricName'],rec['unit'],rec['statType'],period,days)
            metrics_results[rec['metricName']] = chart_data

        # processing the chart data
        for k, v in metrics_results.items():
            
            df = pd.DataFrame(v)

            if "chart_1_frequency" in chart_options:
                logger.info("Building Chart 1 for: %s",k)
                chart_1 = df.groupby(pd.Grouper(key='label', freq=chart_options["chart_1_frequency"])).data.sum()
                chart_1.index = chart_1.index.strftime(chart_options["chart_1_date_format"])
                metrics_charts["Chart1"+k] = chart_1.to_dict()

            if "chart_2_frequency" in chart_options:
                logger.info("Building Chart 2 for: %s",k)
                chart_2 = df.groupby(pd.Grouper(key='label', freq=chart_options["chart_2_frequency"])).data.sum()
                chart_2.index = chart_2.index.strftime(chart_options["chart_2_date_format"])
                metrics_charts["Chart2"+k] = chart_2.to_dict()

            if "chart_3_frequency" in chart_options:
                chart_3 = df.groupby(pd.Grouper(key='label', freq=chart_options["chart_3_frequency"])).data.sum()
                chart_3.index = chart_3.index.strftime(chart_options["chart_3_date_format"])
                metrics_charts["Chart3"+k] = chart_3.to_dict()

        # Collecting all the keys (dates) for later processing        
        logger.info("Normalizing the labels")
        for k, v in metrics_charts.items():            
            if k.startswith("Chart1"):
                chart_1_key_list.extend(list(metrics_charts[k].keys()))
            elif k.startswith("Chart2"):
                chart_2_key_list.extend(list(metrics_charts[k].keys()))
            elif k.startswith("Chart2"):
                chart_3_key_list.extend(list(metrics_charts[k].keys()))

        # Making sure that all keys are present on the arrays for consistency
        chart_1_unique_keys = list(set(chart_1_key_list)) 
        chart_2_unique_keys = list(set(chart_2_key_list)) 
        chart_3_unique_keys = list(set(chart_3_key_list))    
        logger.info("Filling up the gaps")
        for rec in self.metric_groups[group_name]:
            for key in chart_1_unique_keys:
                if not metrics_charts["Chart1"+rec['metricName']].get(key):
                    metrics_charts["Chart1"+rec['metricName']][key] = 0
            for key in chart_2_unique_keys:
                if not metrics_charts["Chart2"+rec['metricName']].get(key):
                    metrics_charts["Chart2"+rec['metricName']][key] = 0
            for key in chart_3_unique_keys:
                if not metrics_charts["Chart3"+rec['metricName']].get(key):
                    metrics_charts["Chart3"+rec['metricName']][key] = 0

        return metrics_charts  

    
    def _get_metric(self, lambdaName, metricName, unit, statType, period, days):
        chart_data = []    

        #
        # If the StartTime parameter specifies a time stamp that is greater than 3 hours ago, 
        # you must specify the period as follows or no data points in that time range is returned:
        # Start time between 3 hours and 15 days ago - Use a multiple of 60 seconds (1 minute).
        # Start time between 15 and 63 days ago - Use a multiple of 300 seconds (5 minutes).
        # Start time greater than 63 days ago - Use a multiple of 3600 seconds (1 hour).
        # The maximum number of data-points returned is 1440. 
        #
        
        endDate=datetime.utcnow() - timedelta(days=days)

        response = self.cw.get_metric_statistics(
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
            StartTime=endDate,
            Period=period,
            Statistics=[statType],
            Unit=unit
        )

        if len(response["Datapoints"]) == 0:
            logger.error("No Datapoints for %s",metricName)
            return None
        else:
            logger.info("DataPoints: %s",len(response["Datapoints"]))
            for rec in response["Datapoints"]:
                chart_data.append({ 'data':round(rec[statType], 2), 'label': rec["Timestamp"] } )

            return chart_data

def handler(event, context):
    try:        

        chart_data_factory = CWChartDataFactory()

        chart_data_factory._add_group_metric("days",ParserLambdaName,'TweetsProcessed', 'Count', 'Sum')
        chart_data_factory._add_group_metric("days",ParserLambdaName,'ImagesIdentified','Count', 'Sum')
        chart_data_factory._add_group_metric("days",RekognitionLambdaName,'ImagesModerated', 'Count', 'Sum')
        chart_data_factory._add_group_metric("days",ProcessFacesLambdaName,'FacesProcessed', 'Count', 'Sum')

        chart_data_factory._add_group_metric("month",ParserLambdaName,'TweetsProcessed', 'Count', 'Sum')
        chart_data_factory._add_group_metric("month",ParserLambdaName,'ImagesIdentified','Count', 'Sum')
        chart_data_factory._add_group_metric("month",RekognitionLambdaName,'ImagesModerated', 'Count', 'Sum')
        chart_data_factory._add_group_metric("month",ProcessFacesLambdaName,'FacesProcessed', 'Count', 'Sum')

        chart_data_factory._add_group_metric("year",ParserLambdaName,'TweetsProcessed', 'Count', 'Sum')

        days = chart_data_factory._build_group_data("days")
        month = chart_data_factory._build_group_data("month")
        year = chart_data_factory._build_group_data("year")

        data = { 'days' : days, 'month': month, 'year': year }
        
        headers = {
           'Content-Type': 'application/json', 
           'Access-Control-Allow-Origin': '*' 
        }
        
        return _response_proxy(200, data, headers)

    except Exception as e:
        logger.error('Something went wrong: ' + str(e))
        resp = {'result': False, 'msg': str(e)}
        return _response_proxy(500,resp)