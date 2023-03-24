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

class S3LogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.log_entries = []
        self.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))

    def emit(self, record):
        log_entry = self.format(record)
        self.log_entries.append(log_entry)
        print(f"Log entry added: {log_entry}")

    def write_logs_to_s3(self):
        log_data = "\n".join(self.log_entries)
        print(f"Writing logs to S3: {log_data}")
        log_filename = f'{datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")}_{s3_key}.log'
        try:
            s3.put_object(
                Body=log_data,
                Bucket=s3_bucket_name,
                Key=log_filename
            )
        except Exception as e:
            print(f'Error writing log to S3: {e}')

# Initialize the custom S3 log handler and configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
s3_log_handler = S3LogHandler()
logger.addHandler(s3_log_handler)

def create_jira_ticket(jira_payload, auth, headers):
    response = requests.post(
        f'{jira_url}/rest/api/3/issue',
        auth=auth,
        data=jira_payload,
        headers=headers
    )

    if response.status_code == 201:
        logger.info("Jira ticket created successfully")
        jira_ticket_data = response.json()
        jira_ticket_id = jira_ticket_data["id"]
        jira_ticket_key = jira_ticket_data["key"]
        jira_ticket_url = f'{jira_url}/browse/{jira_ticket_key}'
        return jira_ticket_id, jira_ticket_url
    else:
        logger.error(f"Jira ticket creation error, Status Code: {response.status_code}, Response: {response.text}")
        return None
        
def send_webex_message(incident_message):
    url = "https://webexapis.com/v1/messages"
    headers = {
        "Authorization": f"{webex_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "roomId": webex_space_id,
        "text": incident_message
    }
    response = requests.post(url, data=json.dumps(payload), headers=headers)

    if response.status_code == 200:
        logger.info("Webex POST request successful")
    else:
        logger.error(f"Webex POST request error, Status Code: {response.status_code}, Response: {response.text}")

def lambda_handler(event, context):
    # Validate the received request
    if 'body' not in event:
        logger.error("Invalid request: Missing 'body' in the event")
        s3_log_handler.write_logs_to_s3()
        return "Invalid request: Missing 'body' in the event"

    # Parse and log the payload
    pd_payload = json.loads(event['body'])
    sender_ip = event['sourceIp']
    pd_payload['sender_ip'] = sender_ip
    if 'body' in pd_payload:
        pd_payload = pd_payload['body']
        logger.info(f"payload: {pd_payload}")

    # Extract incident information from the payload
    try:
        incident_id = pd_payload['incident']['id']
        incident_summary = pd_payload['incident']['summary']
        incident_url = pd_payload['incident']['html_url']
    except KeyError as e:
        logger.error(f"Invalid payload: Missing key {e}")
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
    incident_jira_ticket_id, incident_jira_ticket_url = create_jira_ticket(jira_payload, auth, headers)
    if incident_jira_ticket_id:
        logger.info(f"Jira ticket URL: {incident_jira_ticket_url}")
        send_webex_message(incident_jira_ticket_url)
        
    # Write logs to S3 at the end of the Lambda invocation
    s3_log_handler.write_logs_to_s3()

    response = {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({"message": "success"})
    }

    return response
