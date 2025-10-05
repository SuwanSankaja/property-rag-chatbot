markdown# Property Assistant - RAG Chatbot

## Setup

1. **Copy environment template:**
```bash
   cp .env.example .env

Fill in your values in .env
Install dependencies:

bash   pip install python-dotenv boto3 opensearch-py requests-aws4auth

Run setup:

bash   python setup.py

Deploy infrastructure:

bash   cd backend/infrastructure
   python opensearch_setup.py
   python setup_api_gateway.py

Deploy Lambda functions:

bash   python deploy_lambda.py
Security

Never commit .env to git
Use .env.example as a template
Keep config.json local only


---

## **Step 9: Run Setup**
```cmd
# Install dotenv
pip install python-dotenv

# Run setup
python setup.py

# Open frontend
cd frontend
start index.html