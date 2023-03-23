import requests
from requests.auth import HTTPBasicAuth
import json
import os
import boto3
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
s3_bucket_name = ['S3_BUCKET_NAME']
s3_key = ['S3_KEY']

def lambda_handler(event, context):  
    # Set up the S3 client
    s3 = boto3.client('s3')
    
    log_messages = []
    
    # Check if the received request is valid
    if 'body' not in event:
        error_message = "Invalid request: Missing 'body' in the event"
        print(error_message)
        log_messages.append(error_message)
        return
    # Parse the JSON payload into a Python object
    pd_payload = json.loads(event['body'])
    message = f"Received payload: {pd_payload}"
    print(message)
    log_messages.append(message)

    # Extract the incident ID, summary, and URL from the payload
    try:
        incident_id = pd_payload['incident']['id']
        incident_summary = pd_payload['incident']['summary']
        incident_url = pd_payload['incident']['html_url']
    except KeyError as e:
        message = f"Invalid payload: Missing key {e}"
        print(message)
        log_messages.append(message)
        return
         
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

    # Posting Jira ticket
    response = requests.request(
        "POST",
        f'{jira_url}/rest/api/3/issue',
        auth=auth,
        data=jira_payload,
        headers=headers
    )

    incident_message = None
    if response.status_code == 201:  # Assuming 201 as the successful status code for Jira ticket creation
        print("Jira ticket created successfully")
        jira_ticket_url = f'{jira_url}/jira/core/projects/{jira_key}/issues'
        incident_message = jira_ticket_url
    else:
        error_jira = "Jira ticket creation error"
        incident_message = f"{error_jira}, Status Code: {response.status_code}, Response: {response.text}"
        print(incident_message)
    
    # Send a message to a Webex 
    url = "https://webexapis.com/v1/messages"
    headers = {
        "Authorization": webex_token,
        "Content-Type": "application/json"
    }
    payload = {
        "roomId": webex_space_id,
        "text": incident_message
    }
    response = requests.post(url, data=json.dumps(payload), headers=headers)

    message = None
    if response.status_code == 200:
        resp = {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "message": "OK"
            })
        }
        message = f"Webex response {resp}"
    else:
        error_webex = "Webex POST request error"
        message = f"{error_webex}, Status Code: {response.status_code}, Response: {response.text}"
        print(message)

    # Log the event to S3
    log_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'payload': log_messages,
        'incident_id': incident_id,       
        'message': message
    }

    log_filename = f'{datetime.utcnow().isoformat()}_{s3_key}.json'
    try:
        s3.put_object(
            Body=json.dumps(log_data),
            Bucket=s3_bucket_name,
            Key=log_filename
        )
    except ClientError as e:
        print(f'Error writing log to S3: {e}')
