import json
import boto3
import csv
import io
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from datetime import datetime

s3_client = boto3.client('s3')
bedrock_runtime = boto3.client('bedrock-runtime')

import os
OPENSEARCH_ENDPOINT = os.environ.get('OPENSEARCH_ENDPOINT')
INDEX_NAME = os.environ.get('INDEX_NAME', 'property-listings')
REGION = os.environ.get('REGION', 'us-east-1')
EMBEDDING_MODEL = 'amazon.titan-embed-text-v2:0'

def get_opensearch_client():
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        REGION,
        'aoss',
        session_token=credentials.token
    )
    
    return OpenSearch(
        hosts=[{'host': OPENSEARCH_ENDPOINT, 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=300
    )

def get_embedding(text):
    try:
        text = text[:6000]
        
        payload = {
            "inputText": text,
            "dimensions": 1024,
            "normalize": True
        }
        
        response = bedrock_runtime.invoke_model(
            modelId=EMBEDDING_MODEL,
            body=json.dumps(payload)
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['embedding']
        
    except Exception as e:
        print(f"Embedding error: {e}")
        return None

def create_combined_text(row):
    parts = []
    
    if row.get('property_name'):
        parts.append(f"Property: {row['property_name']}")
    
    if row.get('property_type'):
        parts.append(f"Type: {row['property_type']}")
    
    location_parts = []
    for field in ['community_name', 'area_name_en', 'city_name']:
        if row.get(field):
            location_parts.append(row[field])
    if location_parts:
        parts.append(f"Location: {', '.join(location_parts)}")
    
    if row.get('Number of Bedrooms'):
        parts.append(f"{row['Number of Bedrooms']} bedrooms")
    
    if row.get('asking_price'):
        parts.append(f"Price: {row.get('asking_price_currency', '')} {row['asking_price']}")
    
    if row.get('description'):
        parts.append(f"Description: {row['description'][:500]}")
    
    return ' | '.join(parts)

def parse_csv_row(row):
    def safe_convert(value, converter, default=None):
        try:
            if value and value.strip():
                return converter(value)
        except (ValueError, AttributeError):
            pass
        return default
    
    return {
        'listing_id': row.get('listing_id', ''),
        'property_name': row.get('property_name', ''),
        'city_name': row.get('city_name', ''),
        'property_type': row.get('property_type', ''),
        'asking_price': safe_convert(row.get('asking_price'), int),
        'asking_price_currency': row.get('asking_price_currency', ''),
        'number_of_bedrooms': safe_convert(row.get('Number of Bedrooms'), int),
        'bathrooms_total': safe_convert(row.get('bathrooms_total'), int),
        'total_area_sqm': safe_convert(row.get('total_area_sqm'), float),
        'community_name': row.get('community_name', ''),
        'area_name_en': row.get('area_name_en', ''),
        'description': row.get('description', ''),
        'for_sale': row.get('for_sale', '').lower() == 'true',
        'for_rent': row.get('for_rent', '').lower() == 'true',
        'listing_url': row.get('listing_url', ''),
        'list_agent_full_name': row.get('list_agent_full_name', ''),
    }

def lambda_handler(event, context):
    try:
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']
        
        print(f"Processing: s3://{bucket}/{key}")
        
        response = s3_client.get_object(Bucket=bucket, Key=key)
        csv_content = response['Body'].read().decode('utf-8')
        
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)
        
        print(f"Found {len(rows)} rows")
        
        os_client = get_opensearch_client()
        
        processed = 0
        failed = 0
        
        for row in rows:
            try:
                doc = parse_csv_row(row)
                
                if not doc.get('listing_id'):
                    continue
                
                combined_text = create_combined_text(row)
                doc['combined_text'] = combined_text
                
                embedding = get_embedding(combined_text)
                if embedding:
                    doc['embedding'] = embedding
                    
                    # FIXED: Removed id parameter for OpenSearch Serverless
                    os_client.index(
                        index=INDEX_NAME,
                        body=doc
                    )
                    processed += 1
                    
                    if processed % 5 == 0:
                        print(f"Processed {processed} documents...")
                else:
                    failed += 1
                    
            except Exception as e:
                print(f"Error processing row: {e}")
                failed += 1
        
        print(f"Complete: {processed} processed, {failed} failed")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'processed': processed,
                'failed': failed,
                'total': len(rows)
            })
        }
        
    except Exception as e:
        print(f"Lambda error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }