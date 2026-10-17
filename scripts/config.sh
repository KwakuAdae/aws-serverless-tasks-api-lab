#!/usr/bin/env bash
# Shared lab settings. Override any value by exporting it before running a script.
export AWS_REGION="${AWS_REGION:-us-east-1}"
export STACK_NAME="${STACK_NAME:-tasks-api-lab}"

# Read a CloudFormation output from the deployed stack
stack_output() {
  aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text
}
