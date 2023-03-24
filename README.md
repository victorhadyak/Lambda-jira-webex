# Testing Jenkins
Lambda function that automate the process of creating Jira tickets.

-PagerDuty sends a webhook payload to the Lambda function, which parses the payload to extract the incident ID and summary.

-The function then uses the Jira REST API to create a new Jira ticket, with the incident summary as the ticket summary, and the incident URL as the ticket description.

-Once the Jira ticket is created, the function uses the Webex Teams REST API to send a message to a specified Webex Teams space, notifying of the new ticket and providing a link to the Jira ticket.
![Lambda](https://user-images.githubusercontent.com/109483154/224041505-8dd943f3-8e70-49de-aeb4-0af5e446b991.jpeg)

Steps :
-Created a Terraform project to provision a Lambda function with all necessary dependencies.
-Created a GitHub repository and pushed your Terraform project to it.
-Created a Jenkins host and provided it with all necessary credentials.
-Created an agent container from a Dockerfile that includes Terraform and AWS CLI tools needed for building and deploying your project.
-Delegated the build job to the agent container.
-Created a GitHub webhook to trigger the Jenkins build whenever changes are pushed to the repository.
-Exposed your IP address to the internet using SSH tunneling to an EC2 instance and created a Python script to run it.
-Created a test branch in GitHub and pushed changes to it.
-Merged the test branch with the main branch to trigger the Jenkins build and provision the infrastructure. 
-Ran a testing Python script to trigger the Lambda function and test its workflow.
Improved the lambda function:
-Added code to the lambda function to process the input data and perform any necessary logic.
-Added error handling code to handle any potential errors that might occur during execution.
-Created a separate function for each step of the lambda function's logic.
-Refactored the lambda function to call these functions in sequence.
-Created a class that encapsulated the logic of the lambda function.
-Added a logging handler to the class to store the logs in memory.
-Added code to the lambda function to write the logs to the S3 bucket at the end of the invocation.
-Added code to the lambda function to create a response object to send back to the trigger.
-Tested the lambda function to make sure it worked as expected.
-Debugged any issues that arose during testing.

