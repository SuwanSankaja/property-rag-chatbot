import boto3
import time

opensearch_serverless = boto3.client('opensearchserverless')

COLLECTION_NAME = 'property-listings-rag'

def delete_collection():
    try:
        print("Finding collection...")
        # First, get the collection ID
        response = opensearch_serverless.batch_get_collection(names=[COLLECTION_NAME])
        
        if not response.get('collectionDetails'):
            print("✓ Collection doesn't exist (already deleted)")
            return True
        
        collection_id = response['collectionDetails'][0]['id']
        print(f"  Found collection ID: {collection_id}")
        
        print("Deleting collection...")
        opensearch_serverless.delete_collection(id=collection_id)
        print("✓ Collection deletion initiated")
        
        # Wait for deletion
        print("  Waiting for collection to be deleted...")
        time.sleep(5)
        
        while True:
            try:
                response = opensearch_serverless.batch_get_collection(ids=[collection_id])
                if response['collectionDetails']:
                    status = response['collectionDetails'][0]['status']
                    print(f"  Status: {status}")
                    if status == 'DELETING':
                        time.sleep(5)
                    else:
                        break
                else:
                    break
            except Exception as e:
                if 'ResourceNotFoundException' in str(e):
                    break
                print(f"  Check error: {e}")
                break
        
        print("✓ Collection deleted")
        return True
        
    except Exception as e:
        if 'ResourceNotFoundException' in str(e):
            print("✓ Collection doesn't exist (already deleted)")
            return True
        print(f"✗ Error deleting collection: {e}")
        return False

def delete_data_access_policy():
    try:
        print("\nDeleting data access policy...")
        opensearch_serverless.delete_access_policy(
            name=f'{COLLECTION_NAME}-access',
            type='data'
        )
        print("✓ Data access policy deleted")
        return True
    except Exception as e:
        if 'ResourceNotFoundException' in str(e):
            print("✓ Data access policy doesn't exist")
            return True
        print(f"✗ Error: {e}")
        return False

def delete_network_policy():
    try:
        print("\nDeleting network policy...")
        opensearch_serverless.delete_security_policy(
            name=f'{COLLECTION_NAME}-network',
            type='network'
        )
        print("✓ Network policy deleted")
        return True
    except Exception as e:
        if 'ResourceNotFoundException' in str(e):
            print("✓ Network policy doesn't exist")
            return True
        print(f"✗ Error: {e}")
        return False

def delete_encryption_policy():
    try:
        print("\nDeleting encryption policy...")
        opensearch_serverless.delete_security_policy(
            name=f'{COLLECTION_NAME}-encryption',
            type='encryption'
        )
        print("✓ Encryption policy deleted")
        return True
    except Exception as e:
        if 'ResourceNotFoundException' in str(e):
            print("✓ Encryption policy doesn't exist")
            return True
        print(f"✗ Error: {e}")
        return False

def main():
    print("=== Cleaning Up OpenSearch Resources ===\n")
    
    # Delete in reverse order (collection first, then policies)
    success = True
    
    success = delete_collection() and success
    time.sleep(3)
    
    success = delete_data_access_policy() and success
    time.sleep(2)
    
    success = delete_network_policy() and success
    time.sleep(2)
    
    success = delete_encryption_policy() and success
    
    if success:
        print("\n=== Cleanup Complete! ===")
        print("\nYou can now run: python opensearch_setup.py")
    else:
        print("\n=== Cleanup had some errors ===")
        print("Check the errors above and try again")

if __name__ == "__main__":
    main()