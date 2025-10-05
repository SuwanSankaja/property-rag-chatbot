import boto3
import json
import time

# Initialize clients
opensearch_serverless = boto3.client('opensearchserverless')

from env_loader import CONFIG

COLLECTION_NAME = 'property-listings-rag'
REGION = CONFIG['AWS_REGION']
LAMBDA_ROLE_ARN = CONFIG['LAMBDA_ROLE_ARN']

def create_encryption_policy():
    encryption_policy = {
        "Rules": [{
            "ResourceType": "collection",
            "Resource": [f"collection/{COLLECTION_NAME}"]
        }],
        "AWSOwnedKey": True
    }
    
    try:
        response = opensearch_serverless.create_security_policy(
            name=f'{COLLECTION_NAME}-encryption',
            type='encryption',
            policy=json.dumps(encryption_policy)
        )
        print(f"✓ Encryption policy created")
        return response
    except Exception as e:
        print(f"Encryption policy error: {e}")
        return None

def create_network_policy():
    network_policy = [{
        "Rules": [{
            "ResourceType": "collection",
            "Resource": [f"collection/{COLLECTION_NAME}"]
        }, {
            "ResourceType": "dashboard",
            "Resource": [f"collection/{COLLECTION_NAME}"]
        }],
        "AllowFromPublic": True
    }]
    
    try:
        response = opensearch_serverless.create_security_policy(
            name=f'{COLLECTION_NAME}-network',
            type='network',
            policy=json.dumps(network_policy)
        )
        print(f"✓ Network policy created")
        return response
    except Exception as e:
        print(f"Network policy error: {e}")
        return None

def create_data_access_policy():
    sts = boto3.client('sts')
    account_id = sts.get_caller_identity()['Account']
    
    data_access_policy = [{
        "Rules": [{
            "ResourceType": "collection",
            "Resource": [f"collection/{COLLECTION_NAME}"],
            "Permission": [
                "aoss:CreateCollectionItems",
                "aoss:DeleteCollectionItems",
                "aoss:UpdateCollectionItems",
                "aoss:DescribeCollectionItems"
            ]
        }, {
            "ResourceType": "index",
            "Resource": [f"index/{COLLECTION_NAME}/*"],
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
            LAMBDA_ROLE_ARN,
            f"arn:aws:iam::{account_id}:root"
        ]
    }]
    
    try:
        response = opensearch_serverless.create_access_policy(
            name=f'{COLLECTION_NAME}-access',
            type='data',
            policy=json.dumps(data_access_policy)
        )
        print(f"✓ Data access policy created")
        return response
    except Exception as e:
        print(f"Data access policy error: {e}")
        return None

def create_collection():
    try:
        response = opensearch_serverless.create_collection(
            name=COLLECTION_NAME,
            type='VECTORSEARCH',
            description='Property listings vector search'
        )
        
        collection_id = response['createCollectionDetail']['id']
        print(f"✓ Collection created: {COLLECTION_NAME}")
        print("  Waiting for collection to become active...")
        
        while True:
            status_response = opensearch_serverless.batch_get_collection(
                names=[COLLECTION_NAME]
            )
            status = status_response['collectionDetails'][0]['status']
            
            if status == 'ACTIVE':
                endpoint = status_response['collectionDetails'][0]['collectionEndpoint']
                print(f"✓ Collection is ACTIVE!")
                print(f"  Endpoint: {endpoint}")
                return endpoint
            elif status == 'FAILED':
                print("✗ Collection creation failed")
                return None
            
            print(f"  Status: {status}")
            time.sleep(10)
            
    except Exception as e:
        print(f"Collection creation error: {e}")
        return None

def main():
    print("=== Creating OpenSearch Serverless Collection ===\n")
    
    print("Step 1: Creating encryption policy...")
    create_encryption_policy()
    time.sleep(2)
    
    print("\nStep 2: Creating network policy...")
    create_network_policy()
    time.sleep(2)
    
    print("\nStep 3: Creating data access policy...")
    create_data_access_policy()
    time.sleep(2)
    
    print("\nStep 4: Creating collection...")
    endpoint = create_collection()
    
    if endpoint:
        print("\n=== Setup Complete! ===")
        print(f"\nCollection Endpoint: {endpoint}")
        
        # Update config.json
        with open('config.json', 'r') as f:
            config = json.load(f)
        config['opensearch_endpoint'] = endpoint.replace('https://', '')
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=2)
        print("\n✓ config.json updated with endpoint")
    else:
        print("\n✗ Setup failed")

if __name__ == "__main__":
    main()