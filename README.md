## AWS Serverless face recognition sentiment analysis on twitter 

<img src="images/twitter-app.png" alt="app" width="1000"/>

In this Serverless app we show a rank of the happiest, saddest among other emotions [Amazon Rekognition](https://aws.amazon.com/rekognition/) can detect from tweets that have the word "selfie" in it. The app relies on lambda functions that extract, process, store and report the information from the picture. It is important to note that Twitter is a public platform that does not moderate photos uploaded by its users. This demo uses the AWS Reckognition moderation feature, but occasionally inappropriate photos can appear. **Use at your own discretion**

The Amazon S3 bucket of this solution creates contains two [Object lifecycle management](https://docs.aws.amazon.com/AmazonS3/latest/dev/object-lifecycle-mgmt.html) for the folders where the reports and records files are stored, which expire the files 2 days after of its creation. Similarly, the dynamoDb table that records all the images processed, expires the records after 2 days of its creation.  

Below is the diagram for a depiction of the complete architecture.

<img src="images/twitter-rekognition.png" alt="architecture" width="800"/>

The solution also leverage the [Embedded Metric Format](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Embedded_Metric_Format_Specification.html) to create metrics for number of tweets that are being processed, number of images moderated and number of faces identified and processed. There isn't a direct correlations of numbers of tweets and faces processed as not all tweets' images have people, some images are moderated. In some cases one photo can contain more than 10 faces, which makes it impredictable. Becasuse EMF stores the information into AWS CloudWatch metrics, we were able to query it and display the estatitics and the graph data from there. 

Another cool service used is [AWS X-Ray](https://aws.amazon.com/xray/) that allows you to understand how your application and its underlying services are performing to identify and troubleshoot the root cause of performance issues and errors.

## Initial environment setup

### Prerequisites

This app is deployed through AWS CloudFormation with an additional Vue.js application configuration. The following resources are required to be installed:

- [AWS SAM](https://aws.amazon.com/serverless/sam/) - The AWS Serverless Application Model (SAM) is an open-source framework for building serverless applications. It provides shorthand syntax to express functions, APIs, databases, and event source mappings.
- npm to be able to build the Vue.js app
- [AWS cli](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html) to be able to interact with the AWS resources
- AWS Account and permissition to create the resources.
- Python 3.8 or Docker installed in your local machine. 

### Step 1: Create the Twitter API keys

1. The solution requires the following Twitter API Keys: Consumer Key (API Key, Consumer Secret (AP I Secret), Access Token, and Access Token Secret. The following steps walk you through registering the app with your Twitter account to create these values.
   - Create a Twitter account if you do not already have one
   - Register a new application with your Twitter account:
     - Go to https://developer.twitter.com/en/portal/projects-and-apps
     - Click "Create New App"
     - Under Name, enter something descriptive (but unique), e.g., aws-serverless-twitter-es
     - Enter a description
     - Under Website, you can enter https://github.com/awslabs/aws-serverless-twitter-event-source
     - Leave Callback URL blank
     - Read and agree to the Twitter Developer Agreement
     - Click "Create your Twitter application"
   - (Optional, but recommended) Restrict the application permissions to read only
     - From the detail page of your Twitter application, click the "Permissions" tab
     - Under the "Access" section, make sure "Read only" is selected and click the "Update Settings" button
   - Generate an access token:
     - From the detail page of your Twitter application, click the "Keys and Access Tokens" tab
     - On this tab, you will already see the Consumer Key (API Key) and Consumer Secret (API Secret) values required by the app.
     - Scroll down to the Access Token section and click "Create my access token"
     - You will now have the Access Token and Access Token Secret values required by the app.

2.  Store the keys as encrypted SecureString values in SSM Parameter Store. You can setup the required parameters via the AWS Console or using the following AWS CLI commands:
   
 ```bash
aws ssm put-parameter --name /twitter-event-source/consumer_key --value <your consumer key value> --type SecureString --overwrite
aws ssm put-parameter --name /twitter-event-source/consumer_secret --value <your consumer secret value> --type SecureString --overwrite
aws ssm put-parameter --name /twitter-event-source/access_token --value <your access token value> --type SecureString --overwrite
aws ssm put-parameter --name /twitter-event-source/access_token_secret --value <your access token secret value> --type SecureString --overwrite
  ```

### Step 2: Build all the solution's libraries dependencies

1. The AWS Lambda functions requires libraries for their executions and SAM fetches and install them per each funtion. The *sam build* command creates a .aws-sam directory with the AWS SAM template, AWS Lambda function code, and any language-specific files and dependencies in a format ready to be deployed in the next step. 
   
If you have Python 3.8 installed in your machine you can run:
   
```bash
sam build
```

Another option is to execute *sam build* using containers. It requires you to have docker installed :
```bash
sam build --use-container --build-image amazon/aws-sam-cli-build-image-python3.8
```

When the build finishes, you will receive a message like: 
```bash
Build Succeeded

Built Artifacts  : .aws-sam/build
Built Template   : .aws-sam/build/template.yaml

Commands you can use next
=========================
[*] Validate SAM template: sam validate
[*] Invoke Function: sam local invoke
[*] Test Function in the Cloud: sam sync --stack-name {{stack-name}} --watch
[*] Deploy: sam deploy --guided
```


### Step 3: Deploy the backend usins *sam deploy* 

1. Now it is time to deploy the solution to your AWS Account. The command will ask you a few questions. Below an example of the questions and answers you can provide.
```bash
sam deploy --guided --capabilities CAPABILITY_NAMED_IAM

Configuring SAM deploy
======================

	Looking for config file [samconfig.toml] :  Not found

	Setting default arguments for 'sam deploy'
	=========================================
	Stack Name [sam-app]: twitter-demo
	AWS Region [us-west-2]:
	Parameter GlueDatabaseName [twitter-db]:
	Parameter SearchText [selfie]:
	Parameter SSMParameterPrefix [twitter-event-source]:
	Parameter PollingFrequencyInMinutes [10]:
	Parameter BatchSize [15]:
	#Shows you resources changes to be deployed and require a 'Y' to initiate deploy
	Confirm changes before deploy [y/N]: y
	#SAM needs permission to be able to create roles to connect to the resources in your template
	Allow SAM CLI IAM role creation [Y/n]: y
	#Preserves the state of previously provisioned resources when an operation fails
	Disable rollback [y/N]: n
	GetStat may not have authorization defined, Is this okay? [y/N]: y
	GetImage may not have authorization defined, Is this okay? [y/N]: y
	DelImage may not have authorization defined, Is this okay? [y/N]: y
	Save arguments to configuration file [Y/n]: y
	SAM configuration file [samconfig.toml]:
	SAM configuration environment [default]:
```

Once AWS SAM deploy does it magic, all you need is to answer **Y** to proceed the deployment.

```bash
Previewing CloudFormation changeset before deployment
======================================================
Deploy this changeset? [y/N]: y
```

### Step 4: Deploy Vue.js app into S3

1. In this last step we will executes the script to publish the Vue.js application into your bucket that exposes it via Amazon Cloudfront. **The script requires the npm and aws cli installed**
```bash
./appDeploy.sh 
```

Once if finishes the script provides you the URL where the applicaton is running. Give it a few minutes so it can collect some data.

```bash
Site available at: https://<YourCloudFrontId>.cloudfront.net
```

:warning: **Important Note: Some Ad blocking apps can prevent the images to be shown.** 
