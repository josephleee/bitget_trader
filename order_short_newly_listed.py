import requests
import json
import jsondiff
import os
from modules.order_module import BitgetOrder
from modules.alert_module import send_message_to_slack
import datetime
import pytz

# Get the current time in Korea
tz = pytz.timezone("Asia/Seoul")

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
# FILE_NAME = "USDT_UMCBL"
FILE_NAME = "USDT_UMCBL_HQ"


def p_log(message):
    print(datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S") + "| " + message)


def get_bitget_list():
    url = "https://www.bitget.com/v1/trigger/tracking/getOpenSymbol"
    headers = {"Content-Type": "application/json"}
    data = {"languageType": 0}

    # Check if response is different from saved data
    with open(DIR_PATH + f"/data/{FILE_NAME}.json", "r") as f:
        saved_data = json.load(f)

    response = requests.post(url, headers=headers, json=data)
    response_json = response.json()["data"]
    response_json = [i.get("symbolId") for i in response_json]
    return response_json, saved_data


def get_bitget_list_homequotation():
    url = "https://www.bitget.com/v1/mix/market/homeQuotation"
    headers = {"Content-Type": "application/json"}
    data = {
        "businessLine": 10,
        "isHome": False,
        "rankingType": 3,
        "switchNew": True,
        "languageType": 0,
    }

    # Check if response is different from saved data
    with open(DIR_PATH + f"/data/{FILE_NAME}.json", "r") as f:
        saved_data = json.load(f)

    response = requests.post(url, headers=headers, json=data)
    response_json = response.json()["data"]
    response_json = [i.get("symbolId") for i in response_json]
    return response_json, saved_data


# response_json, saved_data = get_bitget_list()
response_json, saved_data = get_bitget_list_homequotation()
if not saved_data:
    with open(DIR_PATH + f"/data/{FILE_NAME}.json", "w") as f:
        json.dump(response_json, f, indent=4)
else:
    changes = jsondiff.diff(sorted(saved_data), sorted(response_json), syntax="explicit")
    if changes:
        umcbl_chg = []

        for k, v in changes.items():
            p_log(f"----{k}----")
            for i in v:
                if str(k) == "$delete":
                    p_log(f"Delete in {i}")
                else:
                    p_log("{}: {}".format(i[0], i[1]))
                    symbolId = i[1]
                    if "UMCBL" in symbolId:
                        umcbl_chg.append(i[1])

        p_log(f"Changes: {umcbl_chg}")

        bitget = BitgetOrder()
        for symbol in umcbl_chg:
            # orders = bitget.order(symbol, margin_mode="cross", amount=1)
            # send_message_to_slack(orders)
            pass

        send_message_to_slack(f"symbols: {umcbl_chg}")

        # Save new response to file
        with open(DIR_PATH + f"/data/{FILE_NAME}.json", "w") as f:
            json.dump(saved_data + umcbl_chg, f, indent=4)
