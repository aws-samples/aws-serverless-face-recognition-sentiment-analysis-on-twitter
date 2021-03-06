import * as cdk from '@aws-cdk/core'
import * as apiGw from "@aws-cdk/aws-apigateway"
import * as iam from "@aws-cdk/aws-iam";
import { Table, AttributeType, BillingMode } from '@aws-cdk/aws-dynamodb';
import * as s3 from '@aws-cdk/aws-s3';
import { CfnApplication } from '@aws-cdk/aws-sam';
import * as sfn from '@aws-cdk/aws-stepfunctions';
import * as tasks from '@aws-cdk/aws-stepfunctions-tasks';
import * as lambda from '@aws-cdk/aws-lambda';
//import * as ssm from '@aws-cdk/aws-ssm';

export interface TwServerlessProps extends cdk.NestedStackProps {
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

  constructor(scope: cdk.Construct, id: string, props: TwServerlessProps ) {
    super(scope, id, props);
  
    //arn:aws:ssm:us-west-2:00000000:parameter/twitter-demo/deliverystream
    const ssmReadPolicy = new iam.PolicyStatement()
    ssmReadPolicy.addActions("ssm:GetParameters")
    ssmReadPolicy.addActions("ssm:GetParameter")
    ssmReadPolicy.addActions("ssm:GetParametersByPath")
    ssmReadPolicy.addResources(this.formatArn({
       service: 'ssm',
       resource: 'parameter/twitter*',
       sep: ':'
     }
    ));

    const rekReadPolicy = new iam.PolicyStatement()
    rekReadPolicy.addActions("rekognition:CompareFaces")
    rekReadPolicy.addActions("rekognition:DetectFaces")
    rekReadPolicy.addActions("rekognition:DetectLabels")
    rekReadPolicy.addActions("rekognition:ListCollections")
    rekReadPolicy.addActions("rekognition:ListFaces")
    rekReadPolicy.addActions("rekognition:SearchFaces")
    rekReadPolicy.addActions("rekognition:SearchFacesByImage")
    rekReadPolicy.addActions("rekognition:DetectText")
    rekReadPolicy.addActions("rekognition:GetCelebrityInfo")
    rekReadPolicy.addActions("rekognition:RecognizeCelebrities")
    rekReadPolicy.addActions("rekognition:DetectModerationLabels")
    rekReadPolicy.addActions("rekognition:GetLabelDetection")
    rekReadPolicy.addActions("rekognition:GetFaceDetection")
    rekReadPolicy.addActions("rekognition:GetContentModeration")
    rekReadPolicy.addActions("rekognition:GetPersonTracking")
    rekReadPolicy.addActions("rekognition:GetCelebrityRecognition")
    rekReadPolicy.addActions("rekognition:GetFaceSearch")
    rekReadPolicy.addActions("rekognition:GetTextDetection")
    rekReadPolicy.addActions("rekognition:DescribeStreamProcessor")
    rekReadPolicy.addActions("rekognition:ListStreamProcessors")
    rekReadPolicy.addActions("rekognition:DescribeProjects")
    rekReadPolicy.addActions("rekognition:DescribeProjectVersions")
    rekReadPolicy.addActions("rekognition:DetectCustomLabels")
    rekReadPolicy.addAllResources()

    const comprehendPolicy = new iam.PolicyStatement()
    comprehendPolicy.addActions("comprehend:BatchDetectKeyPhrases")
    comprehendPolicy.addActions("comprehend:DetectDominantLanguage")
    comprehendPolicy.addActions("comprehend:DetectEntities")
    comprehendPolicy.addActions("comprehend:BatchDetectEntities")
    comprehendPolicy.addActions("comprehend:DetectKeyPhrases")
    comprehendPolicy.addActions("comprehend:DetectSentiment")
    comprehendPolicy.addActions("comprehend:BatchDetectDominantLanguage")
    comprehendPolicy.addActions("comprehend:BatchDetectSentiment")
    comprehendPolicy.addAllResources()

    const kinesisPolicy = new iam.PolicyStatement()
    kinesisPolicy.addActions("firehose:PutRecord")
    kinesisPolicy.addActions("firehose:PutRecordBatch")
    kinesisPolicy.addResources(this.formatArn({
      service: 'firehose',
      resource: 'deliverystream/TwitterStack*',
      sep: ':'
    }
   ));


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
       restApiName: 'twitter Demo Api'
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
    props.s3Bucket.grantReadWrite(this.athenaQueryFunction)
    this.athenaQueryFunction.addToRolePolicy(ssmReadPolicy);

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