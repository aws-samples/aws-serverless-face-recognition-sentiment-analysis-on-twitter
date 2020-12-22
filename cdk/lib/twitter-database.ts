import * as cdk from '@aws-cdk/core'
import { PolicyStatement, Role, ServicePrincipal } from "@aws-cdk/aws-iam";
import * as kinesisFirehose from '@aws-cdk/aws-kinesisfirehose'
import { Database as glueDatabase, Table as glueTable, Schema, DataFormat } from '@aws-cdk/aws-glue'
import * as s3 from '@aws-cdk/aws-s3';
import * as lambda from '@aws-cdk/aws-lambda';
import * as ssm from '@aws-cdk/aws-ssm';

export interface TwDatabaseProps extends cdk.NestedStackProps {
  /** the function for which we want to count url hits **/
  readonly s3Bucket: s3.Bucket;
  readonly athenaQueryFunction: lambda.Function;
  readonly getImageFunction: lambda.Function;
}

export class TwDatabase extends cdk.NestedStack {
  constructor(scope: cdk.Construct, id: string, props: TwDatabaseProps) {
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

    const twDatabase = new glueDatabase(this, 'twitter_data', {
      databaseName: 'twitter_data'
    });

    const twJsonTable = new glueTable(this, 'json_records', {
      database: twDatabase,
      tableName: 'json_records',
      dataFormat: DataFormat.JSON,
      columns: [
        { name: "first_name", type: Schema.STRING, comment: 'from deserializer' },
        { name: "last_name", type: Schema.STRING, comment: 'from deserializer' },
        { name: "image_url", type: Schema.STRING, comment: 'from deserializer' },
        { name: "tweet_id", type: Schema.STRING, comment: 'from deserializer' },
        { name: "gender", type: Schema.struct([{ name: "value", type: Schema.STRING }, { name: "confidence", type: Schema.DOUBLE }]), comment: 'from deserializer' },
        { name: "face_id", type: Schema.STRING, comment: 'from deserializer' },
        { name: "emotions", type: Schema.array(Schema.struct([{ name: "type", type: Schema.STRING }, { name: "confidence", type: Schema.DOUBLE }])), comment: 'from deserializer' },
        { name: "bbox_left", type: Schema.DOUBLE, comment: 'from deserializer' },
        { name: "bbox_top", type: Schema.DOUBLE, comment: 'from deserializer' },
        { name: "bbox_width", type: Schema.DOUBLE, comment: 'from deserializer' },
        { name: "bbox_height", type: Schema.DOUBLE, comment: 'from deserializer' },
        { name: "imgWidth", type: Schema.SMALL_INT, comment: 'from deserializer' },
        { name: "imgHeight", type: Schema.SMALL_INT, comment: 'from deserializer' },
        { name: "full_text", type: Schema.STRING, comment: 'from deserializer' },
        { name: "sentiment", type: Schema.STRING, comment: 'from deserializer' },
        { name: "updated_at", type: Schema.STRING, comment: 'from deserializer' },
        { name: "agerange", type: Schema.struct([{ name: "low", type: Schema.SMALL_INT }, { name: "high", type: Schema.SMALL_INT }]), comment: 'from deserializer' }
      ],
      bucket: props.s3Bucket,
      s3Prefix: 'data/json-records/',
    })

    const twParquetTable = new glueTable(this, 'parquet_records', {
      database: twDatabase,
      tableName: 'parquet_records',
      dataFormat: DataFormat.PARQUET,
      columns: [
        { name: "first_name", type: Schema.STRING, comment: 'from deserializer' },
        { name: "last_name", type: Schema.STRING, comment: 'from deserializer' },
        { name: "image_url", type: Schema.STRING, comment: 'from deserializer' },
        { name: "tweet_id", type: Schema.STRING, comment: 'from deserializer' },
        { name: "gender", type: Schema.struct([{ name: "value", type: Schema.STRING }, { name: "confidence", type: Schema.DOUBLE }]), comment: 'from deserializer' },
        { name: "face_id", type: Schema.STRING, comment: 'from deserializer' },
        { name: "emotions", type: Schema.array(Schema.struct([{ name: "type", type: Schema.STRING }, { name: "confidence", type: Schema.DOUBLE }])), comment: 'from deserializer' },
        { name: "bbox_left", type: Schema.DOUBLE, comment: 'from deserializer' },
        { name: "bbox_top", type: Schema.DOUBLE, comment: 'from deserializer' },
        { name: "bbox_width", type: Schema.DOUBLE, comment: 'from deserializer' },
        { name: "bbox_height", type: Schema.DOUBLE, comment: 'from deserializer' },
        { name: "imgWidth", type: Schema.SMALL_INT, comment: 'from deserializer' },
        { name: "imgHeight", type: Schema.SMALL_INT, comment: 'from deserializer' },
        { name: "full_text", type: Schema.STRING, comment: 'from deserializer' },
        { name: "sentiment", type: Schema.STRING, comment: 'from deserializer' },
        { name: "updated_at", type: Schema.STRING, comment: 'from deserializer' },
        { name: "agerange", type: Schema.struct([{ name: "low", type: Schema.SMALL_INT }, { name: "high", type: Schema.SMALL_INT }]), comment: 'from deserializer' }
      ],
      bucket: props.s3Bucket,
      s3Prefix: 'data/parquet-' + new Date().getFullYear().toString() + '/',
    })
    twParquetTable.grantRead(props.athenaQueryFunction)
    twParquetTable.grantRead(props.getImageFunction)

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
            databaseName: twDatabase.databaseName,
            tableName: twJsonTable.tableName
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