#!/usr/bin/env bash

DARKGRAY='\033[1;30m'
RED='\033[0;31m'
LIGHTRED='\033[1;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
LIGHTPURPLE='\033[1;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
SET='\033[0m'

# Check parameters
if [[ ! -n "$1" ]]; then
  echo "using TwitterStack as Stackname (default)"
  STACKNAME="TwitterStack"
else
  STACKNAME=$1
fi

aws cloudformation describe-stacks --stack-name ${STACKNAME} &> /dev/null
if [ $? -eq 0 ]; then
   echo -e "Stack ${YELLOW}${STACKNAME}${SET} found"
else
   echo -e "${RED}Error:${SET} Stack ${YELLOW}${1}${SET} not found"
   exit 1
fi

BUCKET=$(aws cloudformation describe-stacks --stack-name $STACKNAME --query "Stacks[0].Outputs[?OutputKey=='S3Bucket'].OutputValue" --output text)
echo -e "Bucket: ${YELLOW}${BUCKET}${SET}"
API=$(aws cloudformation describe-stacks --stack-name $STACKNAME --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text)
echo -e "ApiUrl: ${YELLOW}${API}${SET}"
CLOUDFRONT=$(aws cloudformation describe-stacks --stack-name $STACKNAME --query "Stacks[0].Outputs[?OutputKey=='Cloudfront'].OutputValue" --output text)
echo -e "CloudFront domain name: ${YELLOW}${CLOUDFRONT}${SET}"
AWS_REGION=$(aws configure get region)
echo -e "${YELLOW}-- API: ${WHITE}${API}${SET}"
echo -e "${YELLOW}-- REGION: ${WHITE}${AWS_REGION}${SET}"
echo -e "-- Creating .env file"
cd vue-app
echo "VUE_APP_AWS_API_URL=${API}" > .env
echo -e "-- npm commands"
npm install
npm run build
aws s3 cp dist s3://${BUCKET} --recursive
aws s3 website s3://${BUCKET}/ --index-document index.html --error-document error.html
cd ..
echo 
echo -e "Site available at: ${YELLOW}https://${CLOUDFRONT}/index.html${SET}"