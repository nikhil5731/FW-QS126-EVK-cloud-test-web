from flask import Flask, request, jsonify
import inspect
from main import read_devices,MODE_FUNCS
from coms import *
from evk import IxanaEVK
import apicall

app = Flask(__name__)

DEVICES_PATH = 'devices.json'
devices = read_devices(DEVICES_PATH)


@app.route('/connect', methods=['POST'])
def connect_device():
    data = request.json
    dev = data.get('dev')
    mac = data.get('mac')
    setting = data.get('setting', 0x12345678)

    if not (dev or mac):
        return jsonify({"error": "Either 'dev' or 'mac' must be provided"}), 400

    if dev:
        mac = devices.get(dev)
        if not mac:
            return jsonify({"error": f"Device '{dev}' not found"}), 404

    evk = IxanaEVK(mac)
    evk.ic_setting_id = setting

    response = {
        "VERSION": evk.version,
        "BOARD_ID": evk.boardid,
        "MODE": repr(evk.mode_rd())
    }

    common_dict = {
        'mac': evk.ser.mac_address,
        'board_id': evk.boardid,
        'py_version': evk.PYVERSION,
        'fw_version': evk.version,
    }
    evk.field_wr(FIELD_NAME.ICSETTING, apicall.get_ic_setting(**common_dict, id=evk.ic_setting_id))

    return jsonify(response)

@app.route('/<mode>', methods=['POST'])
def handle_mode(mode):
    if mode not in MODE_FUNCS:
        return jsonify({"error": "Invalid mode"}), 400

    func = MODE_FUNCS[mode]
    data = request.json
    mac = data.get('mac')
    dev = data.get('dev')

    if not (dev or mac):
        return jsonify({"error": "Either 'dev' or 'mac' must be provided"}), 400

    if dev:
        mac = devices.get(dev)
        if not mac:
            return jsonify({"error": f"Device '{dev}' not found"}), 404

    evk = IxanaEVK(mac)
    evk.ic_setting_id = data.get('setting', 0x12345678)

    common_dict = {
        'mac': evk.ser.mac_address,
        'board_id': evk.boardid,
        'py_version': evk.PYVERSION,
        'fw_version': evk.version,
    }
    evk.field_wr(FIELD_NAME.ICSETTING, apicall.get_ic_setting(**common_dict, id=evk.ic_setting_id))

    relevant_args = inspect.getfullargspec(func).annotations
    relevant_args.pop('evk', None)
    func_args = {arg: data[arg] for arg in relevant_args.keys() if arg in data}

    func(evk, **func_args)

    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(debug=True)
