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
YEAR=$(date +'%Y')
#PREFIX=$(aws s3api list-objects-v2 --bucket ${BUCKET} --prefix data --query 'Contents[?ends_with(Key, `/`)].[Key]' --output text | grep parquet | sed 's/\//\\\//g')
echo -e "${YELLOW}-- BUCKET: ${WHITE}${BUCKET}${SET}"
echo -e "-- Creating Athena Database"
aws athena start-query-execution --query-string file://athenaDb.sql --query-execution-context Database="default" --result-configuration OutputLocation=s3://$BUCKET/ath-output
echo -e "-- Creating Athena Json Table"
sed "s/<app-bucket>/${BUCKET}/" athenaTable.sql > athenaTable.json.sql
aws athena start-query-execution --query-string file://athenaTable.json.sql --query-execution-context Database="twitter_data" --result-configuration OutputLocation=s3://$BUCKET/ath-output
rm athenaTable.json.sql
echo -e "-- Creating Athena Parquet Table"
sed "s/<app-bucket><parquet-directory>/${BUCKET}\/data\/parquet-${YEAR}/" athenaParquet.sql > athenaParquet.tmp.sql
aws athena start-query-execution --query-string file://athenaParquet.tmp.sql --query-execution-context Database="twitter_data" --result-configuration OutputLocation=s3://$BUCKET/ath-output
rm athenaParquet.tmp.sql
echo -e "-- Creating FireHose"
aws cloudformation create-stack --stack-name twitter-firehose --template-body file://firehose.yaml --capabilities CAPABILITY_IAM --parameters ParameterKey=Bucket,ParameterValue=$BUCKET