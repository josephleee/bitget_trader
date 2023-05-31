import requests
import json

def send_message_to_slack(text):
    with open("./modules/slack.json", "r") as r:
        slack_config = json.load(r)
    url = slack_config.get("alert_webhook")

    payload = { "text" : text }

    requests.post(url, json=payload)