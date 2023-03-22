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

def lambda_handler(event, context):  

   # Check if the received request is valid
    if 'body' not in event:
        print("Invalid request: Missing 'body' in the event")
        return

   # Parse the JSON payload into a Python object

    pd_payload = json.loads(event['body'])
    print(f"Received payload: {pd_payload}")
    
    if 'body' in pd_payload:
        pd_payload = pd_payload['body']
   
    # Extract the incident ID, summary, and URL from the payload
    try:
        incident_id = pd_payload['incident']['id']
        incident_summary = pd_payload['incident']['summary']
        incident_url = pd_payload['incident']['html_url']
    except KeyError as e:
        print(f"Invalid payload: Missing key {e}")
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
        print("Jira ticket created successfully")
        jira_ticket_url = f'{jira_url}/jira/core/projects/{jira_key}/issues'  # Fixed syntax error
        incident_message = jira_ticket_url
        
    else:
        print(f"Status Code: {response.status_code}, Response: {response.text}")
	
    incident_message = jira_ticket_url
    	
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
    else:
        print(f"Status Code: {response.status_code}, Response: {response.text}")
