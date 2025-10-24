#!/bin/bash

set -x

REGION=${REGION:-eu-central-1}
FUNCTION_NAME=$1

echo $FUNCTION_NAME

# aws iam get-user