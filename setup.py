#!/usr/bin/env python3
"""
Setup script to generate config files from .env
"""
import os
from dotenv import load_dotenv

load_dotenv()

def generate_frontend_config():
    """Generate frontend config.js from .env"""
    api_endpoint = os.getenv('API_ENDPOINT')
    
    config_js = f"""// This file is generated from .env - DO NOT EDIT MANUALLY
const CONFIG = {{
    API_ENDPOINT: '{api_endpoint}'
}};
"""
    
    with open('frontend/config.js', 'w') as f:
        f.write(config_js)
    
    print("✓ Generated frontend/config.js")

def verify_env():
    """Verify all required env vars are set"""
    required = [
        'AWS_REGION', 'AWS_ACCOUNT_ID', 'SOURCE_BUCKET', 
        'INTENTS_BUCKET', 'OPENSEARCH_ENDPOINT', 'API_ENDPOINT'
    ]
    
    missing = [var for var in required if not os.getenv(var)]
    
    if missing:
        print("✗ Missing required environment variables:")
        for var in missing:
            print(f"  - {var}")
        return False
    
    print("✓ All required environment variables are set")
    return True

if __name__ == "__main__":
    print("=== Setup Configuration ===\n")
    
    if not os.path.exists('.env'):
        print("✗ .env file not found!")
        print("  Copy .env.example to .env and fill in your values")
        exit(1)
    
    if verify_env():
        generate_frontend_config()
        print("\n✓ Setup complete!")
    else:
        print("\n✗ Setup failed - fix the errors above")
        exit(1)