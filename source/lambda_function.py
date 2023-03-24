import os
import json
import boto3
import logging
import requests
from datetime import datetime
from requests.auth import HTTPBasicAuth
from botocore.exceptions import ClientError

#Variables stored in Jenkins
jira_url = os.environ['JIRA_URL']
jira_user = os.environ['JIRA_USER']
jira_token = os.environ['JIRA_TOKEN']
jira_key = os.environ['JIRA_KEY']
jira_issue = os.environ['JIRA_ISSUE']
jira_id = os.environ['JIRA_ID']
webex_token = os.environ['WEBEX_ACCESS_TOKEN'] 
webex_space_id = os.environ['WEBEX_SPACE_ID']
s3_bucket_name = os.environ['S3_BUCKET_NAME']

# Set up the S3 client    
s3 = boto3.client('s3')
s3_key = 'logs'
auth = HTTPBasicAuth(jira_user, jira_token)
headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

#Custom logging handler stores logs in memory and writes them to an S3 bucket at the end of the invocation.
class S3LogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.log_entries = []
        self.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))

    #Format the log record and append it to the log_entries list.
    def emit(self, record):
        log_entry = self.format(record)
        self.log_entries.append(log_entry)
        print(f"Log entry added: {log_entry}")

    #Write the logs collected in the log_entries list to an S3 bucket.
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

def create_jira_payload(incident_id, incident_summary, incident_url, jira_issue, jira_id):
    return json.dumps({
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

# Initialize the custom S3 log handler and configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
s3_log_handler = S3LogHandler()
logger.addHandler(s3_log_handler)

#Create a Jira ticket using the provided payload, authentication, and headers
def create_jira_ticket(jira_payload, auth, headers): 
    try:
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
            logger.error(f"Failed to create Jira ticket. Status Code: {response.status_code}, Response: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error creating Jira ticket: {e}")
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
    sender_ip = event['requestContext']['identity']['sourceIp']
    if 'body' in pd_payload:
        pd_payload = pd_payload['body']
    # Additional inserting ip of a sender
    pd_payload['sender_ip'] = sender_ip
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
             
    # Create the Jira payload by passing necessary parameters
    jira_payload = create_jira_payload(incident_id, incident_summary, incident_url, jira_issue, jira_id)

    # Call the create_jira_ticket function to create a Jira ticket and returns the ticket ID and the ticket URL
    incident_jira_ticket_id, incident_jira_ticket_url = create_jira_ticket(jira_payload, auth, headers)

    # Check if the Jira ticket was created successfully by verifying if the incident_jira_ticket_id is not None
    if incident_jira_ticket_id:
        logger.info(f"Jira ticket URL: {incident_jira_ticket_url}")

        # Send the Jira ticket URL as a Webex message
        send_webex_message(incident_jira_ticket_url)
    
    # Response to the trigger request sender
    response = {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({"message": "success"})
    }

    return response
