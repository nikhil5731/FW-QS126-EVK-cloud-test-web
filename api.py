import json
import numpy as np
from convert import convert_stats_result
from offsetdict import devices
from flask import Flask, jsonify, request
from flask.json.provider import DefaultJSONProvider

# A custom JSON Provider has been defined because default flask version can't handle int32

class NumpyArrayEncoder(DefaultJSONProvider):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        else:
            return super().default(obj)


class CustomizedFlask(Flask):
    json_provider_class = NumpyArrayEncoder



app = CustomizedFlask(__name__)



# Define routes


@app.route('/processdev', methods=['POST'])
def call_convert():
 
 # Unpack data

 event = json.loads(request.data)
 mac = event["mac"]
 board_id = event["board_id"]
 py_version = event["py_version"]
 fw_version = event["fw_version"]

 settings = event["settings"]
 settings = eval(f'"{settings}"')
 settings = bytearray(bytes(settings, encoding='latin'))
 #print(settings)

 data = event["data"]
 data = eval(f'"{data}"')
 data = bytearray(bytes(data, encoding='latin'))
 #print(data)



 try: 

  result = convert_stats_result(mac, board_id, py_version, fw_version, settings, data)
  #print ('result received') #Comment for prod
  #print(result) #Comment for prod
  return jsonify(result)

 except Exception as e:
  print(e)
  return {
        'statusCode': 400,
        'body': json.dumps(e)
  }
    

# This route returns the calibration offset

@app.route('/caloffset/<mac>', methods=['GET'])
def get_device_by_mac(mac):
 cal_offset = get_device(mac)
 if cal_offset is None:
  return jsonify(324)
 return jsonify(cal_offset["offset"])

    # return jsonify(cal_offset)

def get_device(mac):
 return next((e for e in devices if e['mac'] == mac), None)

if __name__ == '__main__':
   app.run(port=5000)
