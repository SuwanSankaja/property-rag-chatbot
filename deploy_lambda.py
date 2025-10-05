import boto3
import os
from dotenv import load_dotenv

load_dotenv()

lambda_client = boto3.client('lambda')

# Update Query Lambda environment variables
lambda_client.update_function_configuration(
    FunctionName=os.getenv('QUERY_LAMBDA_NAME'),
    Environment={
        'Variables': {
            'OPENSEARCH_ENDPOINT': os.getenv('OPENSEARCH_ENDPOINT'),
            'INDEX_NAME': os.getenv('OPENSEARCH_INDEX'),
            'REGION': os.getenv('AWS_REGION'),
            'INTENTS_BUCKET': os.getenv('INTENTS_BUCKET'),
            'EMBEDDING_MODEL': os.getenv('EMBEDDING_MODEL'),
            'CHAT_MODEL': os.getenv('CHAT_MODEL')
        }
    }
)

print("Lambda environment variables updated!")