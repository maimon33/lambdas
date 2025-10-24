#!/bin/bash
set -e

REGION=${REGION:-us-east-1}
PYTHON_VERSION=${PYTHON_VERSION:-python3.11}
FUNCTION_NAME=$1
FREQ=$2

user_info=$(aws sts get-caller-identity --output text || echo "Failed to auth AWS")
ACCOUNT_ID="`echo $user_info | awk ' {print $1} '`"
USER_NAME="`echo $user_info | awk ' {print $3} '`"

if ! aws iam list-roles --region $REGION | grep "${FUNCTION_NAME}LambdaRole" > /dev/null; then \
    aws iam create-role --region $REGION --role-name "${FUNCTION_NAME}LambdaRole" \
    --assume-role-policy-document file://lambda-role-trust-policy.json; \
fi

aws iam put-role-policy --region $REGION --role-name "${FUNCTION_NAME}LambdaRole" \
    --policy-name "${FUNCTION_NAME}Policy" --policy-document file://lambda-role-policy.json

if ! aws lambda get-function --region $REGION --function-name $FUNCTION_NAME &> /dev/null; then
    echo "Function does not exist, creating..."
    ROLE_ARN="arn:aws:iam::$ACCOUNT_ID:role/${FUNCTION_NAME}LambdaRole"
    aws lambda create-function \
        --region $REGION \
	    --function-name $FUNCTION_NAME \
	    --zip-file fileb://deployment-package.zip \
	    --handler main.lambda_handler \
	    --runtime $PYTHON_VERSION \
	    --memory-size 512 \
	    --timeout 15 \
	    --role "$ROLE_ARN"
else
    echo "Function already exists, updating..."
    nohup aws lambda update-function-code \
        --region $REGION \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://deployment-package.zip &
    # aws lambda delete-function --region $REGION --function-name $FUNCTION_NAME || true
	# aws lambda create-function \
    #     --region $REGION \
	#     --function-name $FUNCTION_NAME \
	#     --zip-file fileb://deployment-package.zip \
	#     --handler main.lambda_handler \
	#     --runtime python3.9 \
	#     --memory-size 512 \
	#     --timeout 15 \
	#     --role "$ROLE_ARN"
fi

case $FREQ in
    "Daily")
        rules="cron(0 10 * * ? *)"
        ;;
    "5Minutes")
        rules="rate(5 minutes)"
        ;;
    "1Minute")
        rules="rate(1 minute)"
        ;;
    *)
        echo "Invalid frequency"
        exit 1
        ;;
esac

aws events put-rule \
    --region "$REGION" \
    --name "${FUNCTION_NAME}-${FREQ}" \
    --schedule-expression "$rules"

targets="{\"Id\" : \"1\", \"Arn\": \"arn:aws:lambda:$REGION:$ACCOUNT_ID:function:$FUNCTION_NAME\"}"

aws events put-targets \
    --region "$REGION" \
    --rule "${FUNCTION_NAME}-${FREQ}" \
    --targets "$targets"


if ! aws lambda get-policy --region $REGION --function-name $FUNCTION_NAME 2> /dev/null | grep CountInstanceSchePerm > /dev/null; then
    echo "Setting policy so schedule event will trigger function"
    aws lambda add-permission \
        --region $REGION \
        --function-name $FUNCTION_NAME \
        --statement-id CountInstanceSchePerm \
        --action 'lambda:InvokeFunction' \
        --principal events.amazonaws.com \
        --source-arn "arn:aws:events:$REGION:$ACCOUNT_ID:rule/${FUNCTION_NAME}-${FREQ}"
else
    echo "Events already have permission to trigger function."
    aws lambda remove-permission \
        --region $REGION \
        --function-name $FUNCTION_NAME \
        --statement-id CountInstanceSchePerm

    aws lambda add-permission \
        --region $REGION \
        --function-name $FUNCTION_NAME \
        --statement-id CountInstanceSchePerm \
        --action 'lambda:InvokeFunction' \
        --principal events.amazonaws.com \
        --source-arn "arn:aws:events:$REGION:$ACCOUNT_ID:rule/${FUNCTION_NAME}-${FREQ}"
fi


