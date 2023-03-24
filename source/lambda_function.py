import requests
from requests.auth import HTTPBasicAuth
import json
import os
import boto3
import logging
from botocore.exceptions import ClientError
from datetime import datetime

jira_url = os.environ['JIRA_URL']
jira_user = os.environ['JIRA_USER']
jira_token = os.environ['JIRA_TOKEN']
jira_key = os.environ['JIRA_KEY']
jira_issue = os.environ['JIRA_ISSUE']
jira_id = os.environ['JIRA_ID']
webex_token = os.environ['WEBEX_ACCESS_TOKEN'] 
webex_space_id = os.environ['WEBEX_SPACE_ID']
s3_bucket_name = os.environ['S3_BUCKET_NAME']
s3_key = os.environ['S3_KEY']

# Set up the S3 client    
s3 = boto3.client('s3')

# Custom logging handler class to store logs and write them to S3
class S3LogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.log_entries = []

    def emit(self, record):
        log_entry = self.format(record)
        self.log_entries.append(log_entry)

    def write_logs_to_s3(self):
        log_data = "\n".join(self.log_entries)
        log_filename = f'{datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")}_{s3_key}.txt'
        try:
            s3.put_object(
                Body=log_data,
                Bucket=s3_bucket_name,
                Key=log_filename
            )
        except Exception as e:
            logging.error(f'Error writing log to S3: {e}')

# Initialize the custom S3 log handler and configure logging
s3_log_handler = S3LogHandler()
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s', handlers=[s3_log_handler])

def create_jira_ticket(jira_payload, auth, headers):
    response = requests.post(
        f'{jira_url}/rest/api/3/issue',
        auth=auth,
        data=jira_payload,
        headers=headers
    )

    if response.status_code == 201:  # Assuming 201 as the successful status code for Jira ticket creation
        logging.info("Jira ticket created successfully")
        jira_ticket_url = f'{jira_url}/jira/core/projects/{jira_key}/issues'
        return jira_ticket_url
    else:
        logging.error(f"Jira ticket creation error, Status Code: {response.status_code}, Response: {response.text}")
        return None
        
def send_webex_message(incident_message, headers):
    url = "https://webexapis.com/v1/messages"
    payload = {
        "roomId": webex_space_id,
        "text": incident_message
    }
    response = requests.post(url, data=json.dumps(payload), headers=headers)

    if response.status_code == 200:
        logging.info("Webex POST request successful")
    else:
        logging.error(f"Webex POST request error, Status Code: {response.status_code}, Response: {response.text}")

def lambda_handler(event, context):
    # Validate the received request
    if 'body' not in event:
        logging.error("Invalid request: Missing 'body' in the event")
        s3_log_handler.write_logs_to_s3()
        return "Invalid request: Missing 'body' in the event"

    # Parse and log the payload
    pd_payload = json.loads(event['body'])
    if 'body' in pd_payload:
        pd_payload = pd_payload['body']
        logging.info(f"payload: {pd_payload}")

    # Extract incident information from the payload
    try:
        incident_id = pd_payload['incident']['id']
        incident_summary = pd_payload['incident']['summary']
        incident_url = pd_payload['incident']['html_url']
    except KeyError as e:
        logging.error(f"Invalid payload: Missing key {e}")
        s3_log_handler.write_logs_to_s3()
        return f"Invalid payload: Missing key {e}"
         
    # Create a new Jira ticket  
    auth = HTTPBasicAuth(jira_user, jira_token)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    jira_payload = json.dumps({
        "fields": {      
            "issuetype": {
                "name": jira_issue
            },
            "labels": [
                incident_id,
                incident_url
            ],   
            "project": {
                "id": jira_id
            },
            "summary": incident_summary,
        },
        "update": {}
    })
    
    # Create a new Jira ticket
    incident_message = create_jira_ticket(jira_payload, auth, headers)
    if incident_message:
        send_webex_message(incident_message, headers)

    # Write logs to S3 at the end of the Lambda invocation
    s3_log_handler.write_logs_to_s3()

    return message
