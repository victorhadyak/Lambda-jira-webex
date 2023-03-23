import boto3
from datetime import datetime
import requests
from requests.auth import HTTPBasicAuth
import json
import os

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

def append_logs_to_s3(logs):
    s3 = boto3.client('s3')
    
    try:
        response = s3.get_object(Bucket=s3_bucket_name, Key=s3_key)
        existing_logs = response['Body'].read().decode('utf-8')
    except s3.exceptions.NoSuchKey:
        existing_logs = ""
    
    updated_logs = existing_logs + logs + "\n"
    s3.put_object(Bucket=s3_bucket_name, Key=s3_key, Body=updated_logs)

def lambda_handler(event, context):  

   # Check if the received request is valid
    if 'body' not in event:
        log_message = ("Invalid request: Missing 'body' in the event")
        log_entry = f"{datetime.now()} -  {log_message} - Status Code: {response.status_code}, Response: {response.text}"
        return

   # Parse the JSON payload into a Python object

    pd_payload = json.loads(event['body'])
    log_message = (f"Received payload: {pd_payload}")
    log_entry = f"{datetime.now()} -  {log_message} - Status Code: {response.status_code}, Response: {response.text}"
    append_logs_to_s3(log_entry)
    
    # Extract the incident ID, summary, and URL from the payload
    try:
        incident_id = pd_payload['incident']['id']
        incident_summary = pd_payload['incident']['summary']
        incident_url = pd_payload['incident']['html_url']
    except KeyError as e:
        log_message = (f"Invalid payload: Missing key {e}")
        log_entry = f"{datetime.now()} - {log_message} - Status Code: {response.status_code}, Response: {response.text}"
        append_logs_to_s3(log_entry)
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

    if response.status_code == 201:  # Assuming 201 as the successful status code for Jira ticket creation           
        jira_ticket_url = f'{jira_url}/jira/core/projects/{jira_key}/issues'
        incident_message = jira_ticket_url
        log_message = ("Jira ticket created successfully") 
        log_entry = f"{datetime.now()} - {log_message} - Status Code: {response.status_code}, Response: {response.text}"     
    else:
        log_message(f"{Jira ticket creation error, Status Code: {response.status_code}, Response: {response.text}")    
        log_entry = f"{datetime.now()} - {log_message}, Status Code: {response.status_code}, Response: {response.text}"
    append_logs_to_s3(log_entry)    
        
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
        resp = {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "message": "OK"
            })
        }
        return resp
        log_entry = f"{datetime.now()} - Webex response - Status Code: {response.status_code}, Response: {response.text}"
        
    else:
    	#erro message
        error_webex = "Webex POST request error"
	log_entry = f"{datetime.now()} - {error_webex} - Status Code: {response.status_code}, Response: {response.text}"
    append_logs_to_s3(log_entry)

