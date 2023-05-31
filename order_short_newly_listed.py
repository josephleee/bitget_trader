import requests
import json
import jsondiff
from modules.order_module import BitgetOrder
from modules.alert_module import send_message_to_slack

def get_bitget_list():
    url = "https://www.bitget.com/v1/trigger/tracking/getOpenSymbol"
    headers = {"Content-Type": "application/json"}
    data = {"languageType": 0}

    # Check if response is different from saved data
    with open("./data/USDT_UMCBL.json", "r") as f:
        saved_data = json.load(f)

    response = requests.post(url, headers=headers, json=data)
    response_json = response.json()["data"]
    return response_json, saved_data


response_json, saved_data = get_bitget_list()
if response_json != saved_data:
    umcbl_chg = []

    # If different, print only the differences
    changes = jsondiff.diff(saved_data, response_json, syntax="explicit")
    for k, v in changes.items():
        print(f"----{k}----")
        for i in v:
            if str(k) == "$delete":
                print(f"Delete in {i}")
            else:
                print("Change in {}: \n{}".format(i[0], i[1]))
                if "UMCBL" in i[1].get("symbolId"):
                    umcbl_chg.append(i[1].get("symbolId"))

    print(f"Changes: {umcbl_chg}")

    bitget = BitgetOrder()
    for symbol in umcbl_chg:
        # orders = bitget.order(symbol, amount=1)
        # send_message_to_slack(orders)
        send_message_to_slack(f"test order, symbol: {symbol}")

    # Save new response to file
    with open("./data/USDT_UMCBL.json", "w") as f:
        json.dump(response_json, f, indent=4)
        


