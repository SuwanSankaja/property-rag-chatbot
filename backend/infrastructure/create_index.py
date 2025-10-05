from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3
import json
import time

# Load config
with open('config.json', 'r') as f:
    config = json.load(f)

OPENSEARCH_ENDPOINT = config['opensearch_endpoint']
INDEX_NAME = 'property-listings'
REGION = config['region']

print(f"Connecting to: {OPENSEARCH_ENDPOINT}")
print(f"Region: {REGION}")

# Get AWS credentials
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    REGION,
    'aoss',
    session_token=credentials.token
)

# Create OpenSearch client
client = OpenSearch(
    hosts=[{'host': OPENSEARCH_ENDPOINT, 'port': 443}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    timeout=300
)

# Index mapping
index_mapping = {
    "settings": {
        "index": {
            "knn": True,
            "knn.algo_param.ef_search": 512
        }
    },
    "mappings": {
        "properties": {
            "embedding": {
                "type": "knn_vector",
                "dimension": 1024,
                "method": {
                    "name": "hnsw",
                    "space_type": "l2",
                    "engine": "faiss",
                    "parameters": {
                        "ef_construction": 512,
                        "m": 16
                    }
                }
            },
            "listing_id": {"type": "keyword"},
            "property_name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
            "city_name": {"type": "keyword"},
            "property_address": {"type": "text"},
            "property_category": {"type": "keyword"},
            "property_type": {"type": "keyword"},
            "asking_price": {"type": "long"},
            "asking_price_currency": {"type": "keyword"},
            "bathrooms_total": {"type": "integer"},
            "rooms_total": {"type": "integer"},
            "total_area_sqm": {"type": "float"},
            "total_area_sqft": {"type": "float"},
            "price_per_sqm": {"type": "float"},
            "number_of_bedrooms": {"type": "integer"},
            "community_name": {"type": "keyword"},
            "area_name_en": {"type": "keyword"},
            "development_name": {"type": "keyword"},
            "city_region": {"type": "keyword"},
            "map_coordinates_latitude": {"type": "float"},
            "map_coordinates_longitude": {"type": "float"},
            "for_sale": {"type": "boolean"},
            "for_rent": {"type": "boolean"},
            "completion_status": {"type": "keyword"},
            "development_status": {"type": "keyword"},
            "furnished_yn": {"type": "boolean"},
            "furnished_info": {"type": "keyword"},
            "description": {"type": "text"},
            "amenities_text": {"type": "text"},
            "date_listed": {"type": "date"},
            "listing_url": {"type": "keyword"},
            "list_agent_full_name": {"type": "keyword"},
            "list_agent_email": {"type": "keyword"},
            "list_agent_mobile_phone": {"type": "keyword"},
            "list_office_name": {"type": "keyword"},
            "building_name": {"type": "keyword"},
            "building_floor_count": {"type": "integer"},
            "listing_floor_number": {"type": "integer"},
            "combined_text": {"type": "text"},
            "date_scraped": {"type": "date"}
        }
    }
}

def test_connection(max_retries=3):
    """Test connection with retries"""
    for attempt in range(max_retries):
        try:
            # Use cat.indices instead of info() - it works with OpenSearch Serverless
            indices = client.cat.indices(format='json')
            print(f"✓ Successfully connected to OpenSearch (attempt {attempt + 1})")
            print(f"  Current indices: {len(indices)}")
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5
                print(f"  Connection attempt {attempt + 1} failed. Retrying in {wait_time}s...")
                print(f"  Error: {e}")
                time.sleep(wait_time)
            else:
                print(f"✗ Connection failed after {max_retries} attempts: {e}")
                return False

def create_index():
    try:
        if client.indices.exists(index=INDEX_NAME):
            print(f"\nIndex '{INDEX_NAME}' already exists.")
            response = input("Delete and recreate? (yes/no): ")
            if response.lower() == 'yes':
                client.indices.delete(index=INDEX_NAME)
                print(f"✓ Deleted existing index")
        
        print(f"\nCreating index '{INDEX_NAME}'...")
        response = client.indices.create(
            index=INDEX_NAME,
            body=index_mapping
        )
        
        print(f"✓ Index '{INDEX_NAME}' created successfully!")
        print(f"  Response: {response}")
        
        # Verify
        index_info = client.indices.get(index=INDEX_NAME)
        field_count = len(index_info[INDEX_NAME]['mappings']['properties'])
        print(f"✓ Verified: {field_count} fields mapped")
        
    except Exception as e:
        print(f"✗ Error creating index: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=== Creating OpenSearch Index ===\n")
    
    if test_connection():
        create_index()
    else:
        print("\n⚠️  Could not connect to OpenSearch.")
        print("The collection was just created and might need a few more minutes.")
        print("\nPlease wait 2-3 minutes and run this script again:")
        print("  python create_index.py")