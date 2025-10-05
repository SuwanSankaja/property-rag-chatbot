import boto3
import json
import time

from env_loader import CONFIG

API_NAME = "PropertyRAGChatbotAPI"
REGION = CONFIG['AWS_REGION']
LAMBDA_FUNCTION_NAME = CONFIG['QUERY_LAMBDA_NAME']
account_id = CONFIG['AWS_ACCOUNT_ID']

# Initialize clients
apigateway = boto3.client('apigateway')
lambda_client = boto3.client('lambda')

print("=== Creating API Gateway ===\n")

# Create REST API
print("Step 1: Creating REST API...")
api_response = apigateway.create_rest_api(
    name=API_NAME,
    description='REST API for Property RAG Chatbot',
    endpointConfiguration={'types': ['REGIONAL']}
)

api_id = api_response['id']
print(f"✓ API created: {api_id}")

# Get root resource
resources = apigateway.get_resources(restApiId=api_id)
root_id = resources['items'][0]['id']

# Create /chat resource
print("\nStep 2: Creating /chat resource...")
chat_resource = apigateway.create_resource(
    restApiId=api_id,
    parentId=root_id,
    pathPart='chat'
)
chat_resource_id = chat_resource['id']
print(f"✓ /chat resource created: {chat_resource_id}")

# Create POST method
print("\nStep 3: Creating POST method...")
apigateway.put_method(
    restApiId=api_id,
    resourceId=chat_resource_id,
    httpMethod='POST',
    authorizationType='NONE'
)
print("✓ POST method created")

# Create OPTIONS method for CORS
print("\nStep 4: Creating OPTIONS method (CORS)...")
apigateway.put_method(
    restApiId=api_id,
    resourceId=chat_resource_id,
    httpMethod='OPTIONS',
    authorizationType='NONE'
)

apigateway.put_method_response(
    restApiId=api_id,
    resourceId=chat_resource_id,
    httpMethod='OPTIONS',
    statusCode='200',
    responseParameters={
        'method.response.header.Access-Control-Allow-Headers': True,
        'method.response.header.Access-Control-Allow-Methods': True,
        'method.response.header.Access-Control-Allow-Origin': True
    }
)

apigateway.put_integration(
    restApiId=api_id,
    resourceId=chat_resource_id,
    httpMethod='OPTIONS',
    type='MOCK',
    requestTemplates={'application/json': '{"statusCode": 200}'}
)

apigateway.put_integration_response(
    restApiId=api_id,
    resourceId=chat_resource_id,
    httpMethod='OPTIONS',
    statusCode='200',
    responseParameters={
        'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
        'method.response.header.Access-Control-Allow-Methods': "'POST,OPTIONS'",
        'method.response.header.Access-Control-Allow-Origin': "'*'"
    }
)
print("✓ CORS configured")

# Set up Lambda integration for POST
print("\nStep 5: Setting up Lambda integration...")
lambda_arn = f"arn:aws:lambda:{REGION}:{account_id}:function:{LAMBDA_FUNCTION_NAME}"
lambda_uri = f"arn:aws:apigateway:{REGION}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations"

apigateway.put_integration(
    restApiId=api_id,
    resourceId=chat_resource_id,
    httpMethod='POST',
    type='AWS_PROXY',
    integrationHttpMethod='POST',
    uri=lambda_uri
)
print("✓ Lambda integration configured")

# Grant API Gateway permission to invoke Lambda
print("\nStep 6: Granting API Gateway permissions...")
source_arn = f"arn:aws:execute-api:{REGION}:{account_id}:{api_id}/*/*"

try:
    lambda_client.add_permission(
        FunctionName=LAMBDA_FUNCTION_NAME,
        StatementId=f'apigateway-invoke-{int(time.time())}',
        Action='lambda:InvokeFunction',
        Principal='apigateway.amazonaws.com',
        SourceArn=source_arn
    )
    print("✓ Permissions granted")
except lambda_client.exceptions.ResourceConflictException:
    print("✓ Permissions already exist")

# Deploy API
print("\nStep 7: Deploying API to production...")
deployment = apigateway.create_deployment(
    restApiId=api_id,
    stageName='prod'
)
print("✓ API deployed")

# Get endpoint URL
api_endpoint = f"https://{api_id}.execute-api.{REGION}.amazonaws.com/prod/chat"

print("\n" + "="*60)
print("API Gateway Setup Complete!")
print("="*60)
print(f"\nAPI ID: {api_id}")
print(f"Endpoint: {api_endpoint}")

# Update config.json
config['api_endpoint'] = api_endpoint
with open('config.json', 'w') as f:
    json.dump(config, f, indent=2)

print("\n✓ config.json updated with API endpoint")