import boto3
import json

iam = boto3.client('iam')
role_name = 'PropertyRAGLambdaExecutionRole'

# New policy with wildcard for all Claude models
new_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": [
                "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v2:0",
                "arn:aws:bedrock:*::foundation-model/anthropic.claude*"
            ]
        }
    ]
}

# Update the policy
iam.put_role_policy(
    RoleName=role_name,
    PolicyName='BedrockAccess',
    PolicyDocument=json.dumps(new_policy)
)

print("✓ Lambda role policy updated to allow all Claude models")
print("\nWaiting 10 seconds for IAM changes to propagate...")

import time
time.sleep(10)

print("\nTesting Lambda...")
import os
os.system('python test_query_lambda.py')