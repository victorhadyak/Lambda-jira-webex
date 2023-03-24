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

# Set up the S3 client    
s3 = boto3.client('s3')

def write_logs_to_s3(log_data):
    log_filename = f'{datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")}_{s3_key}.txt'
    try:
        s3.put_object(
            Body=log_data,
            Bucket=s3_bucket_name,
            Key=log_filename
        )
    except ClientError as e:
        print(f'Error writing log to S3: {e}')

def lambda_handler(event, context):   
    
    # Check if the received request is valid and extract payload     
    if 'body' not in event:
        log_messages = "Invalid request: Missing 'body' in the event"
        print(log_messages)    
        log_data = log_messages    
        write_logs_to_s3(log_data)
        return log_messages

    # Parse the JSON payload into a Python object
    pd_payload = json.loads(event['body'])

    if 'body' in pd_payload:
        pd_payload = pd_payload['body']
        log_messages = pd_payload
        log_data = log_messages    
        write_logs_to_s3(log_data)
        return log_messages

    # Extract the incident ID, summary, and URL from the payload
    try:
        incident_id = pd_payload['incident']['id']
        incident_summary = pd_payload['incident']['summary']
        incident_url = pd_payload['incident']['html_url']
    except KeyError as e:
        log_messages = f"Invalid payload: Missing key {e}"
        print(log_messages)
        log_data = log_messages
        write_logs_to_s3(log_data)
        return log_messages
         
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
        log_data = incident_message       
        write_logs_to_s3(log_data)
        return incident_message

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

    if response.status_code == 200:
        status_message = f"Webex POST request successful"
    else:
        status_message = f"Webex POST request error"
    message = f"{status_message}, Status Code: {response.status_code}, Response: {response.text}"
    log_data = message
    write_logs_to_s3(log_data)
    return message
