import boto3
import json

lambda_client = boto3.client('lambda')

payload = {
    "body": json.dumps({
        "user_id": "test123",
        "query": "Show me 1 bedroom apartments in Dubai",
        "conversation_history": [],
        "filters": {}
    })
}

response = lambda_client.invoke(
    FunctionName='property-listings-query',
    InvocationType='RequestResponse',
    Payload=json.dumps(payload)
)

result = json.loads(response['Payload'].read())
print(json.dumps(result, indent=2))

# Save to file
with open('response.json', 'w') as f:
    json.dump(result, f, indent=2)

print("\nResponse saved to response.json")