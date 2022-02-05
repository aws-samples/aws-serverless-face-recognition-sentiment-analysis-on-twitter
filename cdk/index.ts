import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as s3 from "aws-cdk-lib/aws-s3";
import * as iam from "aws-cdk-lib/aws-iam";
import {
  CloudFrontWebDistribution,
  CloudFrontWebDistributionProps,
  OriginAccessIdentity,
} from 'aws-cdk-lib/aws-cloudfront';

import { TwServerless } from './twitter-serverless';
import { TwDatabase } from './twitter-database';
class TwitterStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Bucket
    const bucket = new s3.Bucket(this, "TweetStore", {
      versioned: false,
      publicReadAccess: false,
      //encryption: s3.BucketEncryption.S3_MANAGED,
      removalPolicy: cdk.RemovalPolicy.DESTROY, // NOT recommended for production code
      lifecycleRules: [
        {
          expiration: cdk.Duration.days(2),
          prefix: 'data'
        },
        {
          expiration: cdk.Duration.days(2),
          prefix: 'twitter-ath-results'
        }
      ]
    });

    const cloudFrontOAI = new OriginAccessIdentity(this, 'OAI', {
      comment: `OAI for Twitter Demo App.`,
    });

    const cloudFrontDistProps: CloudFrontWebDistributionProps = {
      originConfigs: [
        {
          s3OriginSource: {
            s3BucketSource: bucket,
            originAccessIdentity: cloudFrontOAI,
          },
          behaviors: [{ isDefaultBehavior: true }],
        },
      ],
    };
    
    const cloudfrontDist = new CloudFrontWebDistribution(
      this,
      `Twitter Demo Distribution`,
      cloudFrontDistProps
    );

    const cloudfrontS3Access = new iam.PolicyStatement();
    cloudfrontS3Access.addActions('s3:GetBucket*');
    cloudfrontS3Access.addActions('s3:GetObject*');
    cloudfrontS3Access.addActions('s3:List*');
    cloudfrontS3Access.addResources(bucket.bucketArn);
    cloudfrontS3Access.addResources(`${bucket.bucketArn}/*`);
    cloudfrontS3Access.addCanonicalUserPrincipal(
      cloudFrontOAI.cloudFrontOriginAccessIdentityS3CanonicalUserId
    );

    const twServerless = new TwServerless(this, 'Srvless', {
      s3Bucket: bucket
    });

    const twDatabase = new TwDatabase(this, 'Db', {
      s3Bucket: bucket,
      getImageFunction: twServerless.getImageFunction,
      athenaQueryFunction: twServerless.athenaQueryFunction
    });

    new cdk.CfnOutput(this, 'ApiUrl', {  
      value: twServerless.api.url 
    });
    new cdk.CfnOutput(this, 'S3Bucket', {  
      value: bucket.bucketName 
    });
    new cdk.CfnOutput(this, "Cloudfront", {
      value: cloudfrontDist.distributionDomainName,
    });

  }
}

const app = new cdk.App();
new TwitterStack(app,'TwitterStack');
app.synth();