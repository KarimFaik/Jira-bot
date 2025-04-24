import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

JIRA_URL = os.getenv("JIRA_URL")
JIRA_TOKEN = os.getenv("JIRA_TOKEN")

headers = {
    "Authorization": f"Bearer {JIRA_TOKEN}",
    "Accept": "application/json",
    "Content-type": "application/json"
}

def create_issue(project_key, summary, description, issue_type="Задача"):
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
        print("Issue created")
        print(json.dumps(issue_data, indent = 2))
        return issue_data['key']

    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")


'''
create_issue(
        project_key= "TEMT",
        summary = "Probnaya  2",
        description = f"prosto 2",
        issue_type = "Задача")
'''