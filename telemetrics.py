import json
import numpy as np
import requests
import base64

url = "http://52.5.91.228:5000/stats/pushjsonv2"


class B64Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytearray):
            return {'__B64__': base64.b64encode(obj).decode('ascii')}
        return super().default(obj)


class NumpyTypeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.generic):
            return obj.item()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


def push_json(json_data):
    try:
        payload = json.dumps({
            "data": json_data
        }, indent=2, cls=NumpyTypeEncoder)
        # print(payload)
        headers = {
            'Content-Type': 'application/json'
        }
        response = requests.request("PUT", url, headers=headers, data=payload)
        print(response.text)  # Comment for prod
        return True
    except Exception as e:
        print(f"An error occurred in push_json: {e}")  # Comment for prod
        return False


def push_json_raw(json_data):
    try:
        payload = json.dumps({
            "data": json_data
        }, indent=2, cls=B64Encoder)
        # print(payload)
        headers = {
            'Content-Type': 'application/json'
        }
        response = requests.request(
            "PUT", f"{url}?isRaw=true", headers=headers, data=payload)
        # print(response.text)  # Comment for prod
        return True
    except Exception as e:
        # print(f"An error occurred in push_json_raw: {e}")  # Comment for prod
        return False
