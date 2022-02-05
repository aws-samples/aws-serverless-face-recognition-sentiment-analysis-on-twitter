import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { PolicyStatement, Role, ServicePrincipal } from "aws-cdk-lib/aws-iam";
import * as kinesisFirehose from 'aws-cdk-lib/aws-kinesisfirehose'
import * as glue from 'aws-cdk-lib/aws-glue'
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import { Reference } from 'aws-cdk-lib';

export interface TwDatabaseProps extends cdk.NestedStackProps {
  /** the function for which we want to count url hits **/
  readonly s3Bucket: s3.Bucket;
  readonly athenaQueryFunction: lambda.Function;
  readonly getImageFunction: lambda.Function;
}

export class TwDatabase extends cdk.NestedStack {
  constructor(scope: Construct, id: string, props: TwDatabaseProps) {
    super(scope, id, props);

    const firehoseRole = new Role(this, 'DeliveryStreamRole', {
      assumedBy: new ServicePrincipal('firehose.amazonaws.com'),
    });

    firehoseRole.addToPolicy(new PolicyStatement({
      resources: ['*'],
      actions: ['glue:Start*', 'glue:Stop*', 'glue:Create*', 'glue:Get*', 'glue:List*', 'glue:Search*']
    }));

    firehoseRole.addToPolicy(new PolicyStatement({
      resources: [props.s3Bucket.bucketArn, props.s3Bucket.bucketArn + '/*'],
      actions: ['s3:AbortMultipartUpload', 's3:GetBucketLocation', 's3:GetObject', 's3:ListBucket', 's3:ListBucketMultipartUploads', 's3:PutObject']
    }));

    const twDatabase = new glue.CfnDatabase(this, 'twitter_data', {
      catalogId: this.account,
      databaseInput: {
        name: 'twitter_data'
      }
    });

    const twJsonTable = new glue.CfnTable(this, 'json_records', {
      catalogId: this.account,
      databaseName: twDatabase.ref,
      tableInput: {
      name: 'json_records',      
      storageDescriptor: {
        columns: [
          {
            name: "first_name",
            type: "string",
            comment: "from deserializer"
          },
          {
            name: "last_name",
            type: "string",
            comment: "from deserializer"
          },
          {
            name: "image_url",
            type: "string",
            comment: "from deserializer"
          },
          {
            name: "tweet_id",
            type: "string",
            comment: "from deserializer"
          },
          {
            name: "gender",
            type: "struct<value:string,confidence:double>",
            comment: "from deserializer"
          },
          {
            name: "face_id",
            type: "string",
            comment: "from deserializer"
          },
          {
            name: "emotions",
            type: "array<struct<type:string,confidence:double>>",
            comment: "from deserializer"
          },
          {
            name: "bbox_left",
            type: "double",
            comment: "from deserializer"
          },
          {
            name: "bbox_top",
            type: "double",
            comment: "from deserializer"
          },
          {
            name: "bbox_width",
            type: "double",
            comment: "from deserializer"
          },
          {
            name: "bbox_height",
            type: "double",
            comment: "from deserializer"
          },
          {
            name: "imgwidth",
            type: "smallint",
            comment: "from deserializer"
          },
          {
            name: "imgheight",
            type: "smallint",
            comment: "from deserializer"
          },
          {
            name: "full_text",
            type: "string",
            comment: "from deserializer"
          },
          {
            name: "sentiment",
            type: "string",
            comment: "from deserializer"
          },
          {
            name: "updated_at",
            type: "string",
            comment: "from deserializer"
          },
          {
            name: "agerange",
            type: "struct<low:smallint,high:smallint>",
            comment: "from deserializer"
          }
        ],
        compressed: false,
        location: "s3://" + props.s3Bucket.bucketName + "/data/json-records/",
        inputFormat: "org.apache.hadoop.mapred.TextInputFormat",
        outputFormat: "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",        
        numberOfBuckets: 0,
        serdeInfo: {
          serializationLibrary: "org.openx.data.jsonserde.JsonSerDe"
		    },
      }
    }})

    const twParquetTable = new glue.CfnTable(this, 'parquet_records', {
      catalogId: this.account,
      databaseName: twDatabase.ref,
      tableInput: {
      name: 'parquet_records',      
      storageDescriptor: {
        columns: [
          {
            name: "first_name",
            type: "string",
            comment: "from deserializer"
          },
          {
            name: "last_name",
            type: "string",
            comment: "from deserializer"
          },
          {
            name: "image_url",
            type: "string",
            comment: "from deserializer"
          },
          {
            name: "tweet_id",
            type: "string",
            comment: "from deserializer"
          },
          {
            name: "gender",
            type: "struct<value:string,confidence:double>",
            comment: "from deserializer"
          },
          {
            name: "face_id",
            type: "string",
            comment: "from deserializer"
          },
          {
            name: "emotions",
            type: "array<struct<type:string,confidence:double>>",
            comment: "from deserializer"
          },
          {
            name: "bbox_left",
            type: "double",
            comment: "from deserializer"
          },
          {
            name: "bbox_top",
            type: "double",
            comment: "from deserializer"
          },
          {
            name: "bbox_width",
            type: "double",
            comment: "from deserializer"
          },
          {
            name: "bbox_height",
            type: "double",
            comment: "from deserializer"
          },
          {
            name: "imgwidth",
            type: "smallint",
            comment: "from deserializer"
          },
          {
            name: "imgheight",
            type: "smallint",
            comment: "from deserializer"
          },
          {
            name: "full_text",
            type: "string",
            comment: "from deserializer"
          },
          {
            name: "sentiment",
            type: "string",
            comment: "from deserializer"
          },
          {
            name: "updated_at",
            type: "string",
            comment: "from deserializer"
          },
          {
            name: "agerange",
            type: "struct<low:smallint,high:smallint>",
            comment: "from deserializer"
          }
        ],
        compressed: false,
        location: "s3://" + props.s3Bucket.bucketName + '/data/parquet-' + new Date().getFullYear().toString() + '/',
        inputFormat: "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
        outputFormat: "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",        
        numberOfBuckets: 0,
        serdeInfo: {
          serializationLibrary: "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
		    },
      }
    }})

    const kinesis = new kinesisFirehose.CfnDeliveryStream(this, 'twFirehose', {
      extendedS3DestinationConfiguration: {
        bucketArn: props.s3Bucket.bucketArn,
        prefix: 'data/parquet-!{timestamp:yyyy}/',
        errorOutputPrefix: 'FirehoseFailures/!{firehose:error-output-type}/!{firehose:random-string}/',
        roleArn: firehoseRole.roleArn,
        dataFormatConversionConfiguration: {
          enabled: true,
          inputFormatConfiguration: {
            deserializer: {
              openXJsonSerDe: {}
            }
          },
          outputFormatConfiguration: {
            serializer: {
              parquetSerDe: {}
            }
          },
          schemaConfiguration: {
            roleArn: firehoseRole.roleArn,
            databaseName: twDatabase.ref,
            tableName: twJsonTable.ref
          }
        }
      },
    })

    kinesis.node.addDependency(firehoseRole);

    // Create a new SSM Parameter for firehose
    new ssm.StringParameter(this, 'Parameter', {
      description: 'Kinesis firehost for Twitter Demo',
      parameterName: '/twitter-demo/deliverystream',
      stringValue: kinesis.attrArn
    });

  }
}