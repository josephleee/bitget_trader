import requests
import json
from os.path import dirname, abspath
def send_message_to_slack(text):
    fpath = dirname(dirname(abspath(__file__)))
    with open(fpath + "/modules/slack.json", "r") as r:
        slack_config = json.load(r)
    url = slack_config.get("alert_webhook")

    payload = { "text" : text }

    requests.post(url, json=payload)