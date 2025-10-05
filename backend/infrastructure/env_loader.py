import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)

def get_env(key, default=None):
    """Get environment variable with optional default"""
    return os.getenv(key, default)

def get_required_env(key):
    """Get required environment variable, raise error if missing"""
    value = os.getenv(key)
    if value is None:
        raise ValueError(f"Missing required environment variable: {key}")
    return value

# Export all config
CONFIG = {
    'AWS_REGION': get_required_env('AWS_REGION'),
    'AWS_ACCOUNT_ID': get_required_env('AWS_ACCOUNT_ID'),
    'SOURCE_BUCKET': get_required_env('SOURCE_BUCKET'),
    'INTENTS_BUCKET': get_required_env('INTENTS_BUCKET'),
    'FRONTEND_BUCKET': get_required_env('FRONTEND_BUCKET'),
    'OPENSEARCH_ENDPOINT': get_required_env('OPENSEARCH_ENDPOINT'),
    'OPENSEARCH_INDEX': get_required_env('OPENSEARCH_INDEX'),
    'LAMBDA_ROLE_ARN': get_required_env('LAMBDA_ROLE_ARN'),
    'INGESTION_LAMBDA_NAME': get_required_env('INGESTION_LAMBDA_NAME'),
    'QUERY_LAMBDA_NAME': get_required_env('QUERY_LAMBDA_NAME'),
    'API_ENDPOINT': get_required_env('API_ENDPOINT'),
    'EMBEDDING_MODEL': get_required_env('EMBEDDING_MODEL'),
    'CHAT_MODEL': get_required_env('CHAT_MODEL'),
}