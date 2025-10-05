import json
import boto3
import os
import re
from datetime import datetime
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

# Initialize clients
bedrock_runtime = boto3.client('bedrock-runtime')
s3_client = boto3.client('s3')

# Configuration
OPENSEARCH_ENDPOINT = os.environ.get('OPENSEARCH_ENDPOINT')
INDEX_NAME = os.environ.get('INDEX_NAME', 'property-listings')
REGION = os.environ.get('REGION', 'us-east-1')
INTENTS_BUCKET = os.environ.get('INTENTS_BUCKET')
EMBEDDING_MODEL = 'amazon.titan-embed-text-v2:0'
CHAT_MODEL = 'anthropic.claude-3-5-sonnet-20240620-v1:0'
TOP_K = 5

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
        timeout=30
    )

def get_embedding(text):
    try:
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

def search_properties(query_text, filters=None):
    try:
        os_client = get_opensearch_client()
        
        query_embedding = get_embedding(query_text)
        if not query_embedding:
            return []
        
        # Build filter clauses
        must_clauses = []
        
        if filters:
            # Price filters
            if filters.get('min_price'):
                must_clauses.append({"range": {"asking_price": {"gte": filters['min_price']}}})
            
            if filters.get('max_price'):
                must_clauses.append({"range": {"asking_price": {"lte": filters['max_price']}}})
            
            # Bedroom filter
            if filters.get('bedrooms'):
                must_clauses.append({"term": {"number_of_bedrooms": filters['bedrooms']}})
            
            # Location filter
            if filters.get('city_name'):
                must_clauses.append({"term": {"city_name": filters['city_name']}})
            
            # Sale/Rent filters
            if filters.get('for_sale') is not None:
                must_clauses.append({"term": {"for_sale": filters['for_sale']}})
            
            if filters.get('for_rent') is not None:
                must_clauses.append({"term": {"for_rent": filters['for_rent']}})
            
            # Property type filter
            if filters.get('property_type'):
                must_clauses.append({"term": {"property_type.keyword": filters['property_type']}})
            
            # Furnished filter
            if filters.get('furnished') is not None:
                must_clauses.append({"term": {"furnished_yn": filters['furnished']}})
        
        # Build search query
        if must_clauses:
            search_query = {
                "size": TOP_K,
                "_source": {"excludes": ["embedding"]},
                "query": {
                    "bool": {
                        "must": [
                            {
                                "knn": {
                                    "embedding": {
                                        "vector": query_embedding,
                                        "k": TOP_K * 3
                                    }
                                }
                            }
                        ],
                        "filter": must_clauses
                    }
                }
            }
        else:
            search_query = {
                "size": TOP_K,
                "_source": {"excludes": ["embedding"]},
                "query": {
                    "knn": {
                        "embedding": {
                            "vector": query_embedding,
                            "k": TOP_K
                        }
                    }
                }
            }
        
        response = os_client.search(
            index=INDEX_NAME,
            body=search_query
        )
        
        results = []
        for hit in response['hits']['hits']:
            result = hit['_source']
            result['relevance_score'] = hit['_score']
            results.append(result)
        
        return results
        
    except Exception as e:
        print(f"Search error: {e}")
        return []

def extract_intent(query):
    try:
        intent_prompt = f"""Analyze this property search query and extract user intent as JSON.

Query: {query}

Extract:
{{
  "intent_type": "search|comparison|information",
  "location_interest": ["cities/areas mentioned"],
  "property_type_interest": ["apartment|villa|penthouse|townhouse"],
  "price_range": {{"min": null, "max": null}},
  "bedrooms": null,
  "key_requirements": ["specific requirements"],
  "buying_signals": ["for_sale|for_rent|both"]
}}

Respond ONLY with valid JSON."""

        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 500,
            "messages": [{"role": "user", "content": intent_prompt}],
            "temperature": 0.3
        }
        
        response = bedrock_runtime.invoke_model(
            modelId=CHAT_MODEL,
            body=json.dumps(payload)
        )
        
        response_body = json.loads(response['body'].read())
        intent_text = response_body['content'][0]['text']
        
        intent_data = json.loads(intent_text.strip())
        return intent_data
        
    except Exception as e:
        print(f"Intent extraction error: {e}")
        return None

def extract_filters_from_query(query, intent_data):
    """Extract ALL filters from query - price, bedrooms, sale/rent, etc."""
    filters = {}
    query_lower = query.lower()
    
    # Price filters
    under_match = re.search(r'(?:under|below|less than|max|maximum)\s*(\d[\d,]*)', query_lower)
    if under_match:
        filters['max_price'] = int(under_match.group(1).replace(',', ''))
    
    over_match = re.search(r'(?:above|over|more than|min|minimum)\s*(\d[\d,]*)', query_lower)
    if over_match:
        filters['min_price'] = int(over_match.group(1).replace(',', ''))
    
    between_match = re.search(r'between\s*(\d[\d,]*)\s*and\s*(\d[\d,]*)', query_lower)
    if between_match:
        filters['min_price'] = int(between_match.group(1).replace(',', ''))
        filters['max_price'] = int(between_match.group(2).replace(',', ''))
    
    # Bedroom count
    bed_match = re.search(r'(\d+)\s*(?:bed|bedroom)', query_lower)
    if bed_match:
        filters['bedrooms'] = int(bed_match.group(1))
    
    # For rent vs for sale
    if any(word in query_lower for word in ['for rent', 'to rent', 'rental', 'renting', 'lease']):
        filters['for_rent'] = True
        filters['for_sale'] = False
    elif any(word in query_lower for word in ['for sale', 'to buy', 'purchase', 'buying']):
        filters['for_sale'] = True
        filters['for_rent'] = False
    
    # Property type
    if 'apartment' in query_lower or 'apt' in query_lower:
        filters['property_type'] = 'Apartment'
    elif 'villa' in query_lower:
        filters['property_type'] = 'Villa'
    elif 'penthouse' in query_lower:
        filters['property_type'] = 'Penthouse'
    elif 'townhouse' in query_lower:
        filters['property_type'] = 'Townhouse'
    
    # Furnished status
    if 'furnished' in query_lower and 'unfurnished' not in query_lower:
        filters['furnished'] = True
    elif 'unfurnished' in query_lower:
        filters['furnished'] = False
    
    # Location
    if 'dubai' in query_lower:
        filters['city_name'] = 'Dubai'
    
    # Try to get from intent if not found in query
    if intent_data:
        if not filters.get('bedrooms') and intent_data.get('bedrooms'):
            filters['bedrooms'] = intent_data['bedrooms']
        
        if intent_data.get('price_range'):
            if not filters.get('min_price') and intent_data['price_range'].get('min'):
                filters['min_price'] = intent_data['price_range']['min']
            if not filters.get('max_price') and intent_data['price_range'].get('max'):
                filters['max_price'] = intent_data['price_range']['max']
    
    return filters

def is_count_query(query):
    """Detect if user is asking for total count, not search"""
    query_lower = query.lower()
    count_keywords = [
        'how many total',
        'total number of',
        'all properties',
        'total properties',
        'how many properties are there',
        'how many properties do you have',
        'number of properties in database',
        'property count',
        'total count'
    ]
    return any(keyword in query_lower for keyword in count_keywords)

def save_intent_to_s3(user_id, query, intent_data):
    try:
        timestamp = datetime.utcnow().isoformat()
        filename = f"intents/user_{user_id}_{timestamp.replace(':', '-')}.json"
        
        intent_record = {
            "user_id": user_id,
            "timestamp": timestamp,
            "query": query,
            "intent": intent_data
        }
        
        s3_client.put_object(
            Bucket=INTENTS_BUCKET,
            Key=filename,
            Body=json.dumps(intent_record, indent=2),
            ContentType='application/json'
        )
        
        print(f"Saved intent to s3://{INTENTS_BUCKET}/{filename}")
        return True
        
    except Exception as e:
        print(f"Error saving intent: {e}")
        return False

def generate_response(query, search_results, conversation_history):
    try:
        context_parts = []
        for idx, result in enumerate(search_results[:5], 1):
            property_info = f"""Property {idx}:
- Name: {result.get('property_name', 'N/A')}
- Type: {result.get('property_type', 'N/A')}
- Location: {result.get('community_name', 'N/A')}, {result.get('city_name', 'N/A')}
- Bedrooms: {result.get('number_of_bedrooms', 'N/A')}
- Area: {result.get('total_area_sqm', 'N/A')} sqm
- Price: {result.get('asking_price_currency', '')} {result.get('asking_price', 'N/A'):,}
- Status: {'For Sale' if result.get('for_sale') else ''} {'For Rent' if result.get('for_rent') else ''}
- URL: {result.get('listing_url', 'N/A')}
"""
            context_parts.append(property_info)
        
        context = "\n\n".join(context_parts)
        
        messages = []
        for msg in conversation_history[-5:]:
            messages.append({
                "role": msg['role'],
                "content": msg['content']
            })
        
        system_prompt = """You are a knowledgeable real estate assistant helping users find properties.

Your role:
- Provide helpful, accurate information based on search results
- Be conversational and friendly
- Highlight key features that match user needs
- Always include property URLs when discussing specific properties
- If no suitable properties found, acknowledge this and offer alternatives

Base responses on the actual property data provided."""

        user_message = f"""Based on these property search results:

{context}

User query: {query}

Please provide a helpful response about these properties."""

        messages.append({"role": "user", "content": user_message})
        
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,
            "system": system_prompt,
            "messages": messages,
            "temperature": 0.7
        }
        
        response = bedrock_runtime.invoke_model(
            modelId=CHAT_MODEL,
            body=json.dumps(payload)
        )
        
        response_body = json.loads(response['body'].read())
        assistant_response = response_body['content'][0]['text']
        
        return assistant_response
        
    except Exception as e:
        print(f"Response generation error: {e}")
        return "I apologize, but I'm having trouble generating a response right now. Please try again."

def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        user_id = body.get('user_id', 'anonymous')
        query = body.get('query', '')
        conversation_history = body.get('conversation_history', [])
        user_filters = body.get('filters', {})
        
        if not query:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Query is required'})
            }
        
        print(f"Processing query from user {user_id}: {query}")
        
        # Extract intent
        intent_data = extract_intent(query)
        
        # Save intent to S3
        if intent_data:
            save_intent_to_s3(user_id, query, intent_data)
        
        # Check if this is a count/total query
        if is_count_query(query):
            os_client = get_opensearch_client()
            count_result = os_client.count(index=INDEX_NAME)
            total_count = count_result['count']
            
            response_text = f"We have a total of {total_count} properties in our Dubai real estate database. Would you like to search for specific properties based on your preferences?"
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS'
                },
                'body': json.dumps({
                    'response': response_text,
                    'properties_found': total_count,
                    'intent': intent_data,
                    'filters_applied': {},
                    'properties': [],
                    'is_count_query': True
                })
            }
        
        # Extract filters from query (for regular searches)
        auto_filters = extract_filters_from_query(query, intent_data)
        
        # Merge auto-detected filters with user-provided filters
        combined_filters = {**auto_filters, **user_filters}
        
        print(f"Applied filters: {combined_filters}")
        
        # Search properties with filters
        search_results = search_properties(query, combined_filters)
        
        # Generate response
        response_text = generate_response(query, search_results, conversation_history)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            },
            'body': json.dumps({
                'response': response_text,
                'properties_found': len(search_results),
                'intent': intent_data,
                'filters_applied': combined_filters,
                'properties': search_results[:3]
            })
        }
        
    except Exception as e:
        print(f"Lambda error: {e}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }