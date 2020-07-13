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
  echo "Please inform the stack name"
  exit 1
fi

aws cloudformation describe-stacks --stack-name ${1} &> /dev/null
if [ $? -eq 0 ]; then
   echo -e "Stack ${YELLOW}${1}${SET} found"
else
   echo -e "${RED}Error:${SET} Stack ${YELLOW}${1}${SET} not found"
   exit 1
fi

BUCKET=$(aws cloudformation describe-stack-resource --stack-name $1 --logical-resource-id Bucket --query "StackResourceDetail.PhysicalResourceId" --output text)
API=$(aws cloudformation describe-stack-resource --stack-name $1 --logical-resource-id HttpApi --query StackResourceDetail.PhysicalResourceId --output text)
AWS_REGION=$(aws configure get region)
echo -e "${YELLOW}-- API: ${WHITE}${API}${SET}"
echo -e "${YELLOW}-- REGION: ${WHITE}${AWS_REGION}${SET}"
echo -e "-- Creating .env file"
cd vue-app
echo "VUE_APP_AWS_API_URL=https://${API}.execute-api.${AWS_REGION}.amazonaws.com" > .env
echo -e "-- npm commands"
npm install
npm run build
aws s3 cp dist s3://${BUCKET} --recursive --acl public-read
aws s3 website s3://${BUCKET}/ --index-document index.html --error-document error.html
cd ..
echo -e "Site available at: ${YELLOW}http://${BUCKET}.s3-website-${AWS_REGION}.amazonaws.com/#/${SET}"