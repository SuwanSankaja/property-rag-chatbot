from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3
import json

with open('config.json', 'r') as f:
    config = json.load(f)

OPENSEARCH_ENDPOINT = config['opensearch_endpoint']
REGION = config['region']

credentials = boto3.Session().get_credentials()
auth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    REGION,
    'aoss',
    session_token=credentials.token
)

client = OpenSearch(
    hosts=[{'host': OPENSEARCH_ENDPOINT, 'port': 443}],
    http_auth=auth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection
)

# Count documents
result = client.count(index='property-listings')
print(f"Documents in index: {result['count']}")

# Get sample
sample = client.search(index='property-listings', body={'size': 1})
if sample['hits']['hits']:
    doc = sample['hits']['hits'][0]['_source']
    print(f"\nSample property:")
    print(f"  Name: {doc.get('property_name', 'N/A')}")
    print(f"  City: {doc.get('city_name', 'N/A')}")
    print(f"  Type: {doc.get('property_type', 'N/A')}")
    print(f"  Bedrooms: {doc.get('number_of_bedrooms', 'N/A')}")
    print(f"  Has embedding: {'Yes' if doc.get('embedding') else 'No'}")