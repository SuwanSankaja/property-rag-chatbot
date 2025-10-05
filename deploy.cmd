@echo off
echo Deploying Query Lambda...
cd backend\lamda

del query-lambda.zip 2>nul
rmdir /s /q query-lambda 2>nul

mkdir query-lambda
cd query-lambda
pip install opensearch-py requests-aws4auth boto3 -t .
copy ..\query_lambda.py lambda_function.py
powershell Compress-Archive -Path * -DestinationPath ..\query-lambda.zip -Force
cd ..

aws lambda update-function-code --function-name property-listings-query --zip-file fileb://query-lambda.zip

echo Deployment complete!
pause