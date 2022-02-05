import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as s3 from "aws-cdk-lib/aws-s3";
import * as iam from "aws-cdk-lib/aws-iam";

import * as apiGw from "aws-cdk-lib/aws-apigateway"
import { Table, AttributeType, BillingMode } from 'aws-cdk-lib/aws-dynamodb';
import { CfnApplication } from 'aws-cdk-lib/aws-sam';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as tasks from 'aws-cdk-lib/aws-stepfunctions-tasks';
import * as lambda from 'aws-cdk-lib/aws-lambda';

export interface TwServerlessProps extends cdk.NestedStackProps  {
  /** the function for which we want to count url hits **/
  readonly s3Bucket: s3.Bucket
}

export class TwServerless extends cdk.NestedStack {

  readonly athenaQueryFunction: lambda.Function;
  readonly getImageFunction: lambda.Function;
  readonly parseFunction: lambda.Function;
  readonly rekognitionFunction: lambda.Function;
  readonly processFacesFunction: lambda.Function;
  readonly statFunction: lambda.Function;
  readonly api: apiGw.RestApi;

  constructor(scope: Construct, id: string, props: TwServerlessProps ) {
    super(scope, id, props);
  
    const ssmReadPolicy = new iam.PolicyStatement({
        actions: [
          'ssm:GetParameters',
          'ssm:GetParameter',
          'ssm:GetParametersByPath'
        ],
        resources: [this.formatArn({
          service: 'ssm',
          resource: 'parameter/twitter*'
        })]
    });

    const athenaPolicy = new iam.PolicyStatement({
        actions: ["athena:StartQueryExecution",
                  "athena:Get*",
                  "athena:List*",
                  "athena:BatchGetNamedQuery",
                  "athena:RunQuery",
                  "athena:BatchGetQueryExecution",
                  "glue:Get*",
                  "glue:List*"],
        resources: ['*'],
    });

    const gluePolicy = new iam.PolicyStatement({
      actions: ["glue:BatchGetPartition",
                "glue:GetPartition",
                "glue:GetPartitions",
                "glue:GetTable",
                "glue:GetTables",
                "glue:GetTableVersion",
                "glue:GetTableVersions"],
      resources: [this.formatArn({
        service: 'glue',
        resource: 'table/twitter*'
      })],
    });

    const cloudwatchPolicy = new iam.PolicyStatement({
        actions: ["cloudwatch:Get*"],
        resources: ['*'],
    });

    const rekReadPolicy = new iam.PolicyStatement({
        actions: ["rekognition:CompareFaces",
        "rekognition:DetectFaces",
        "rekognition:DetectLabels",
        "rekognition:ListCollections",
        "rekognition:ListFaces",
        "rekognition:SearchFaces",
        "rekognition:SearchFacesByImage",
        "rekognition:DetectText",
        "rekognition:GetCelebrityInfo",
        "rekognition:RecognizeCelebrities",
        "rekognition:DetectModerationLabels",
        "rekognition:GetLabelDetection",
        "rekognition:GetFaceDetection",
        "rekognition:GetContentModeration",
        "rekognition:GetPersonTracking",
        "rekognition:GetCelebrityRecognition",
        "rekognition:GetFaceSearch",
        "rekognition:GetTextDetection",
        "rekognition:DescribeStreamProcessor",
        "rekognition:ListStreamProcessors",
        "rekognition:DescribeProjects",
        "rekognition:DescribeProjectVersions",
        "rekognition:DetectCustomLabels"],
        resources: ['*'],
    });
    
    const comprehendPolicy = new iam.PolicyStatement({
      actions: ["comprehend:BatchDetectKeyPhrases",
        "comprehend:DetectDominantLanguage",
        "comprehend:DetectEntities",
        "comprehend:BatchDetectEntities",
        "comprehend:DetectKeyPhrases",
        "comprehend:DetectSentiment",
        "comprehend:BatchDetectDominantLanguage",
        "comprehend:BatchDetectSentiment"],
        resources: ['*']
    });        

    const kinesisPolicy = new iam.PolicyStatement({
      actions: ["firehose:PutRecord",
                "firehose:PutRecordBatch"],
      resources: [this.formatArn({
        service: 'firehose',
        resource: 'deliverystream/TwitterStack*'
      })]
    });

     // DynamoDB
     const ddbImageTable = new Table(this, 'ddbImageTable', {
      partitionKey: {
        name: "img_url",
        type: AttributeType.STRING
      },
      timeToLiveAttribute: "expire_at",
      billingMode: BillingMode.PAY_PER_REQUEST,
      //stream: StreamViewType.NEW_IMAGE,      
      removalPolicy: cdk.RemovalPolicy.DESTROY, // NOT recommended for production code
    });

    // API Gatewat Root
    this.api = new apiGw.RestApi(this, 'twitterApi', {
       restApiName: 'twitter Demo Api',
       defaultCorsPreflightOptions: {
        allowOrigins: apiGw.Cors.ALL_ORIGINS,
      },
     });

    // Lambda Layer
    const layer = new lambda.LayerVersion(this, 'CoreLayer', {
      code: lambda.Code.fromAsset('../layers/layer.zip'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_7],
      license: 'Apache-2.0',
      description: 'Tweet Demo Layer',
    });    

    // Lambda athenaQuery
    this.athenaQueryFunction = new lambda.Function(this, 'athenaQuery', {
      code: lambda.Code.fromAsset('../lambdas/athenaquery'),
      handler: "index.handler",
      runtime: lambda.Runtime.PYTHON_3_7,
      tracing: lambda.Tracing.ACTIVE,      
      memorySize: 256,      
      timeout: cdk.Duration.seconds(120),
      layers: [layer],
      environment: {
        Bucket: props.s3Bucket.bucketName
      }
    })
    this.athenaQueryFunction.currentVersion.addAlias('live');
    props.s3Bucket.grantReadWrite(this.athenaQueryFunction);
    this.athenaQueryFunction.addToRolePolicy(ssmReadPolicy);
    this.athenaQueryFunction.addToRolePolicy(athenaPolicy);
    this.athenaQueryFunction.addToRolePolicy(gluePolicy);

    // Lambda Rekognition
    this.rekognitionFunction = new lambda.Function(this, 'recognition', {
      handler: "index.handler",
      runtime: lambda.Runtime.PYTHON_3_7,
      tracing: lambda.Tracing.ACTIVE,
      code: lambda.Code.fromAsset('../lambdas/rekognition'),
      memorySize: 256,
      timeout: cdk.Duration.seconds(120),
      layers: [layer],
      environment: {
        Bucket: props.s3Bucket.bucketName
      }
    })
    this.rekognitionFunction.currentVersion.addAlias('live');
    props.s3Bucket.grantReadWrite(this.rekognitionFunction)
    this.rekognitionFunction.addToRolePolicy(ssmReadPolicy);
    this.rekognitionFunction.addToRolePolicy(rekReadPolicy);

    // Lambda ProcessFaces
    this.processFacesFunction = new lambda.Function(this, 'processfaces', {
      code: lambda.Code.fromAsset('../lambdas/processfaces'),
      handler: "index.handler",
      runtime: lambda.Runtime.PYTHON_3_7,
      tracing: lambda.Tracing.ACTIVE,      
      memorySize: 256,
      timeout: cdk.Duration.seconds(120),
      layers: [layer],
      environment: {
        Bucket: props.s3Bucket.bucketName
      }
    })
    this.processFacesFunction.currentVersion.addAlias('live');
    props.s3Bucket.grantReadWrite(this.processFacesFunction)
    this.processFacesFunction.addToRolePolicy(ssmReadPolicy);
    this.processFacesFunction.addToRolePolicy(comprehendPolicy);
    this.processFacesFunction.addToRolePolicy(kinesisPolicy);

    // Lambda getImage
    this.getImageFunction = new lambda.Function(this, 'getImage', {
      code: lambda.Code.fromAsset('../lambdas/getimage'),
      handler: "index.handler",
      runtime: lambda.Runtime.PYTHON_3_7,
      tracing: lambda.Tracing.ACTIVE,
      memorySize: 256,
      timeout: cdk.Duration.seconds(120),
      layers: [layer],
      environment: {
        Bucket: props.s3Bucket.bucketName,
        AthQueryLambdaName: this.athenaQueryFunction.functionName
      }
    })
    this.getImageFunction.currentVersion.addAlias('live');
    this.getImageFunction.addToRolePolicy(ssmReadPolicy);
    this.getImageFunction.addToRolePolicy(gluePolicy);
    props.s3Bucket.grantReadWrite(this.getImageFunction)
    this.athenaQueryFunction.grantInvoke(this.getImageFunction)

    const getImageApi = this.api.root.addResource('image');
    const getImageFunctionIntegration = new apiGw.LambdaIntegration(this.getImageFunction);
    getImageApi.addMethod('GET', getImageFunctionIntegration);

    //State Machine
    const successState = new sfn.Succeed(this, 'Succeed');
    const failState = new sfn.Fail(this, 'Fail');

    const RekognitionJob = new tasks.LambdaInvoke(this, 'Rekognition', {
      lambdaFunction: this.rekognitionFunction,
      // Lambda's result is in the attribute `Payload`
      outputPath: '$.Payload',
    });

    const ProcessFacesJob = new tasks.LambdaInvoke(this, 'ProcessFaces', {
      lambdaFunction: this.processFacesFunction,
      // Lambda's result is in the attribute `Payload`
      outputPath: '$.Payload',
    });

    const definition = RekognitionJob
    .next(new sfn.Choice(this, 'RekErrorHandler')
      .when(sfn.Condition.stringEquals('$.result', 'Moderated'), successState)
      .when(sfn.Condition.stringEquals('$.result', 'Fail'), failState)
      .when(sfn.Condition.stringEquals('$.result', 'Succeed'), ProcessFacesJob.next(
        new sfn.Choice(this, 'FacesErrorHandler')
          .when(sfn.Condition.stringEquals('$.result', 'Succeed'), successState)
          .when(sfn.Condition.stringEquals('$.result', 'Fail'), failState)
          .otherwise(failState)
          ))
      .otherwise(failState));

    const stateMachine = new sfn.StateMachine(this, 'StateMachine', {
        definition,
        timeout: cdk.Duration.minutes(5)
    });

    // Lambda Parser
    this.parseFunction = new lambda.Function(this, 'parser', {
      handler: "index.handler",
      runtime: lambda.Runtime.PYTHON_3_7,
      tracing: lambda.Tracing.ACTIVE,
      code: lambda.Code.fromAsset('../lambdas/parser'),
      memorySize: 256,
      timeout: cdk.Duration.seconds(120),
      layers: [layer],
      environment: {
        StateMachineArn: stateMachine.stateMachineArn,
        DdbImageTable: ddbImageTable.tableName
      }
    })    
    this.parseFunction.currentVersion.addAlias('live');
    this.parseFunction.addToRolePolicy(ssmReadPolicy);
    props.s3Bucket.grantReadWrite(this.parseFunction);
    ddbImageTable.grantReadWriteData(this.parseFunction);
    stateMachine.grantStartExecution(this.parseFunction);

    // Lambda Stat
    this.statFunction = new lambda.Function(this, 'stat', {
      handler: "index.handler",
      runtime: lambda.Runtime.PYTHON_3_7,
      tracing: lambda.Tracing.ACTIVE,
      code: lambda.Code.fromAsset('../lambdas/getstat'),
      memorySize: 256,
      timeout: cdk.Duration.seconds(120),
      layers: [layer],
      environment: {
        ParserLambdaName: this.parseFunction.functionName,
        AthQueryLambdaName: this.athenaQueryFunction.functionName,
        ProcessFacesLambdaName: this.processFacesFunction.functionName,
        RekognitionLambdaName: this.rekognitionFunction.functionName
      }
    })
    this.statFunction.currentVersion.addAlias('live');
    this.statFunction.addToRolePolicy(ssmReadPolicy);
    this.statFunction.addToRolePolicy(cloudwatchPolicy);

    const statApi = this.api.root.addResource('stat');
    const statFunctionIntegration = new apiGw.LambdaIntegration(this.statFunction);
    statApi.addMethod('GET', statFunctionIntegration)    

    new cdk.CfnOutput(this, 'API_URL', {  value: this.api.url });

    // Serverless Application Repository    
    const tweetSource = new CfnApplication(this, 'tweetSource', {
      location: {
        applicationId: 'arn:aws:serverlessrepo:us-east-1:077246666028:applications/aws-serverless-twitter-event-source',
        semanticVersion: '2.0.0'
      },
      parameters: {
        SearchText: 'selfie',
        TweetProcessorFunctionName: this.parseFunction.functionName,
        PollingFrequencyInMinutes: '10',
        StreamModeEnabled: 'true'
      }
    });  
  }
}