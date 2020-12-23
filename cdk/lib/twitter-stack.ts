import * as cdk from '@aws-cdk/core';
import * as s3 from '@aws-cdk/aws-s3';

import { TwServerless } from './twitter-serverless';
import { TwDatabase } from './twitter-database';
export class TwitterStack extends cdk.Stack {
  constructor(scope: cdk.Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Bucket
    const bucket = new s3.Bucket(this, "TweetStore", {
      versioned: false,
      websiteIndexDocument: "index.html",
      websiteErrorDocument: "error.html",
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

    const twServerless = new TwServerless(this, 'Srvless', {
      s3Bucket: bucket
    });

    const twDatabase = new TwDatabase(this, 'Db', {
      s3Bucket: bucket,
      getImageFunction: twServerless.getImageFunction,
      athenaQueryFunction: twServerless.athenaQueryFunction
    });


  }
}