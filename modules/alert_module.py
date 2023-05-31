import requests

import requests

def send_message_to_slack(text):
    url = ""

    payload = { "text" : text }

    requests.post(url, json=payload)