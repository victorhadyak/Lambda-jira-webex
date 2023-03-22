import argparse
import json
import requests

parser = argparse.ArgumentParser()
parser.add_argument("api_gateway_url", help="API Gateway URL")
args = parser.parse_args()

API_GATEWAY_URL = args.api_gateway_url

payload = {
    "body": {
        "incident": {
            "id": "123456",
            "summary": "Test Incident",
            "html_url": "https://www.pagerduty.com/"
        }
    }
}

headers = {
    "Content-Type": "application/json"
}

response = requests.post(API_GATEWAY_URL, headers=headers, data=json.dumps(payload))

if response.status_code == 200:
	print("Test passed")    
else:
	print(f"Test failed Status Code: {response.status_code}, Response: {response.text}")
