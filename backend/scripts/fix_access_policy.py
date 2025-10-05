import boto3
import json

opensearch_serverless = boto3.client('opensearchserverless')
sts = boto3.client('sts')

# Get current identity
identity = sts.get_caller_identity()
account_id = identity['Account']
current_arn = identity['Arn']

print(f"Current IAM identity: {current_arn}")

# Load config
with open('config.json', 'r') as f:
    config = json.load(f)
    lambda_role_arn = config['lambda_role_arn']

# Get current policy to find version
try:
    current_policy = opensearch_serverless.get_access_policy(
        name='property-listings-rag-access',
        type='data'
    )
    policy_version = current_policy['accessPolicyDetail']['policyVersion']
    print(f"Current policy version: {policy_version}")
except Exception as e:
    print(f"Error getting current policy: {e}")
    exit(1)

# Update data access policy
data_access_policy = [{
    "Rules": [{
        "ResourceType": "collection",
        "Resource": ["collection/property-listings-rag"],
        "Permission": [
            "aoss:CreateCollectionItems",
            "aoss:DeleteCollectionItems",
            "aoss:UpdateCollectionItems",
            "aoss:DescribeCollectionItems"
        ]
    }, {
        "ResourceType": "index",
        "Resource": ["index/property-listings-rag/*"],
        "Permission": [
            "aoss:CreateIndex",
            "aoss:DeleteIndex",
            "aoss:UpdateIndex",
            "aoss:DescribeIndex",
            "aoss:ReadDocument",
            "aoss:WriteDocument"
        ]
    }],
    "Principal": [
        lambda_role_arn,
        f"arn:aws:iam::{account_id}:root",
        current_arn  # Add your current user
    ]
}]

try:
    response = opensearch_serverless.update_access_policy(
        name='property-listings-rag-access',
        policyVersion=policy_version,
        type='data',
        policy=json.dumps(data_access_policy)
    )
    print("✓ Data access policy updated successfully")
    print(f"  Added principal: {current_arn}")
    print("\nWait 30 seconds for policy to propagate, then run:")
    print("  python create_index.py")
except Exception as e:
    print(f"Error updating policy: {e}")