from __future__ import print_function
from crhelper import CfnResource
import logging
import boto3
from datetime import datetime

# https://github.com/aws-cloudformation/custom-resource-helper

logger = logging.getLogger(__name__)
# Initialise the helper, all inputs are optional, this example shows the defaults
helper = CfnResource(json_logging=False, log_level='DEBUG', boto_level='CRITICAL', sleep_on_delete=120, ssl_verify=None)

try:
    glue = boto3.client("glue")
    pass
except Exception as e:
    helper.init_failure(e)


@helper.create
def create(event, context):
    logger.info("Got Create")

    bucketName = event['ResourceProperties']['BucketName']
    databaseName = event['ResourceProperties']['DatabaseName']

    try:
        response = glue.get_database(
        Name=databaseName
    )
        logger.info("Database already exists. Skipping database creation")
    except Exception as e:        
        logger.info(e)
        logger.info("creating database")
        response = glue.create_database(
            DatabaseInput={
                'Name':  databaseName
            }
        ) 

    response = glue.create_table(
    DatabaseName=databaseName,
    TableInput={
        'Name':  'json_records',
        'StorageDescriptor': {
            'Columns': [ 
                {
                    "Name": "first_name",
                    "Type": "string"
                },
                {
                    "Name": "last_name",
                    "Type": "string"
                },
                {
                    "Name": "image_url",
                    "Type": "string"
                },
                {
                    "Name": "tweet_id",
                    "Type": "string"
                },
                {
                    "Name": "gender",
                    "Type": "struct<value:string,confidence:double>"
                },
                {
                    "Name": "face_id",
                    "Type": "string"
                },
                {
                    "Name": "emotions",
                    "Type": "array<struct<type:string,confidence:double>>"
                },
                {
                    "Name": "bbox_left",
                    "Type": "double"
                },
                {
                    "Name": "bbox_top",
                    "Type": "double"
                },
                {
                    "Name": "bbox_width",
                    "Type": "double"
                },
                {
                    "Name": "bbox_height",
                    "Type": "double"
                },
                {
                    "Name": "imgwidth",
                    "Type": "int"
                },
                {
                    "Name": "imgheight",
                    "Type": "int"
                },
                {
                    "Name": "full_text",
                    "Type": "string"
                },
                {
                    "Name": "sentiment",
                    "Type": "string"
                },
                {
                    "Name": "updated_at",
                    "Type": "string"
                },
                {
                    "Name": "agerange",
                    "Type": "struct<low:int,high:int>"
                }
            ],
        'Location': 's3://' + bucketName + '/data/json-records/',
        'InputFormat': 'org.apache.hadoop.mapred.TextInputFormat',
        'OutputFormat': 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat',
        'Compressed': False,
        'NumberOfBuckets': 0,
        'SerdeInfo': {
            'SerializationLibrary': 'org.openx.data.jsonserde.JsonSerDe'
        },
        },
        'TableType': 'EXTERNAL_TABLE'
        }
    )  

    response = glue.create_table(
    DatabaseName=databaseName,
    TableInput={
        'Name':  'parquet_records',
        'StorageDescriptor': {
            'Columns': [ 
                {
                    "Name": "first_name",
                    "Type": "string"
                },
                {
                    "Name": "last_name",
                    "Type": "string"
                },
                {
                    "Name": "image_url",
                    "Type": "string"
                },
                {
                    "Name": "tweet_id",
                    "Type": "string"
                },
                {
                    "Name": "gender",
                    "Type": "struct<value:string,confidence:double>"
                },
                {
                    "Name": "face_id",
                    "Type": "string"
                },
                {
                    "Name": "emotions",
                    "Type": "array<struct<type:string,confidence:double>>"
                },
                {
                    "Name": "bbox_left",
                    "Type": "double"
                },
                {
                    "Name": "bbox_top",
                    "Type": "double"
                },
                {
                    "Name": "bbox_width",
                    "Type": "double"
                },
                {
                    "Name": "bbox_height",
                    "Type": "double"
                },
                {
                    "Name": "imgwidth",
                    "Type": "int"
                },
                {
                    "Name": "imgheight",
                    "Type": "int"
                },
                {
                    "Name": "full_text",
                    "Type": "string"
                },
                {
                    "Name": "sentiment",
                    "Type": "string"
                },
                {
                    "Name": "updated_at",
                    "Type": "string"
                },
                {
                    "Name": "agerange",
                    "Type": "struct<low:int,high:int>"
                }
            ],
        'Location': 's3://' + bucketName + '/data/parquet-' + datetime.now().strftime("%Y"),
        'InputFormat': 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat',
        'OutputFormat': 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat',
        'Compressed': False,
        'NumberOfBuckets': 0,
        'SerdeInfo': {
            'SerializationLibrary': 'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe'
        },
        },
        'TableType': 'EXTERNAL_TABLE'
        }
    )
    
    helper.Data['Db'] = databaseName

    # To return an error to cloudformation you raise an exception:
    if not helper.Data.get("Db"):
        raise ValueError("this error will show in the cloudformation events log and console.")
    
    return databaseName


@helper.update
def update(event, context):
    logger.info("Got Update")
    # If the update resulted in a new resource being created, return an id for the new resource. 
    # CloudFormation will send a delete event with the old id when stack update completes


@helper.delete
def delete(event, context):
    logger.info("Got Delete")

    databaseName = event["PhysicalResourceId"]

    try:
        response = glue.delete_database(
        Name=databaseName
    )
        logger.info("Database deleted")
    except Exception as e:        
        logger.info(e)
        logger.info("Database did not exist")
        
    # Delete never returns anything. Should not fail if the underlying resources are already deleted.
    # Desired state.



def handler(event, context):
    helper(event, context)
                