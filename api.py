import requests
from requests.exceptions import HTTPError, ConnectionError, Timeout
import json
import sys
import os
from dotenv import load_dotenv

path_to_logs = os.path.abspath(os.path.join(os.path.dirname(__file__),"logs"))
sys.path.append(path_to_logs)
from logs_ctrl import logger

#loading variables from .env file
load_dotenv()

JIRA_URL = os.getenv("JIRA_URL")
JIRA_TOKEN = os.getenv("JIRA_TOKEN")

type_of_issue = "Задача"


#access to site
headers = {
    "Authorization": f"Bearer {JIRA_TOKEN}",
    "Accept": "application/json",
    "Content-type": "application/json"
}
#creating issue at jira
def create_issue(project_key, summary, description, issue_type=type_of_issue, context=None):
    url=f"{JIRA_URL}/rest/api/2/issue"
    payload = {
        "fields": {
            "project":{"key": project_key},
            "summary": summary,
            "description": description,
            "issuetype": {"name": issue_type}
        }
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        issue_data = response.json()
        logger.info(f"Задачя создана")
        logger.info(f"{json.dumps(issue_data, indent = 2)}")
        issue_key = issue_data['key']
        return issue_key, None

 
    except HTTPError as e:
        logger.error(f"HTTP error occurred: {e}")
        # Handle specific HTTP errors
        if response.status_code == 400:
            error_msg= "Bad Request: Check your input data."
        elif response.status_code == 401:
            error_msg = "Unauthorized: Authentication failed."
        elif response.status_code == 403:
            error_msg = "Forbidden: You don't have permission to access this resource."
        elif response.status_code == 404:
            error_msg = "Not Found: The requested resource was not found."
        elif response.status_code >= 500:
            error_msg = "Server Error: Please try again later."
        return None, error_msg  
    except ConnectionError as conn_err:
        logger.error(f"Connection error occurred: {conn_err}")
        error_msg = "Connection error occurred."
        return None, error_msg  

    except Timeout as timeout_err:
        logger.error(f"Timeout error occurred: {timeout_err}")
        error_msg = "The request timed out. Try increasing the timeout or try again later."
        return None, error_msg  
    
    except Exception as err:
         logger.error(f"An unexpected error occurred: {err}")
         error_msg = f"An unexpected error occurred: {err}"
         return None, error_msg  

def upload_attachment(issue_key, file_stream, file_name):
    #file_stream = context.user_data['attachment_stream']
    #file_name = context.user_data['attachment_name']

    # Attach the file to the Jira issue
    attachment_url = f"{JIRA_URL}/rest/api/2/issue/{issue_key}/attachments"
    attachment_headers = {
        "Authorization": f"Bearer {JIRA_TOKEN}",
        "X-Atlassian-Token": "no-check"  # Required for Jira attachments
    }
    files = {'file': (file_name, file_stream, 'application/octet-stream')}

    try:
        attachment_response = requests.post(
            attachment_url,
            headers=attachment_headers,
            files=files
        )
        attachment_response.raise_for_status()
        logger.info(f"Attachment {file_name} added to issue {issue_key}")
        return None
    except HTTPError as e:
        logger.error(f"Failed to attach file to issue {issue_key}: {e}")
        return issue_key, f"Ошибка при прикреплении файла: {e}"

    finally:
        file_stream.close()  # Close the stream to free memory