import os
from time import sleep
from byteclass import ByteClass
from dataclasses import dataclass
import numpy as np
import text
from coms import *
from evk import IxanaEVK
# import backend
import apicall


#################### EXAMPLE: MODE_STATS ####################
def example_mode_stats_tx(evk: IxanaEVK, data_size: int):
    """
    data_size: number of bytes to send in each packet (match with rx)
    """
    print('----------MODE STATS TX----------')

    field = FieldModeStatsTX(
        icsetting_bitrate=evk.ic_setting,
        data_size=data_size
    )
    evk.mode_start(MODE.STATS_TX, FIELD_NAME.MODE_STATS_TX, field)

import csv
import time
class ModeStatsRXFile:
    def __init__(self, dir: str) -> None:
        if not os.path.exists(dir):
            os.makedirs(dir)
        timestr = time.strftime('%Y%m%d_%H%M')
        file_name = os.path.join(dir, 'output_' + timestr + '.csv')

        self.csv_file = open(file_name, 'w', newline='')
        self.csv_writer = csv.DictWriter(self.csv_file, [], extrasaction='ignore')
    
    def save_row(self, values: dict):
        if not self.csv_writer.fieldnames:
            self.csv_writer.fieldnames = list(values.keys())
            self.csv_writer.writeheader()
        self.csv_writer.writerow(values)
        self.csv_file.flush()

def example_mode_stats_rx(evk: IxanaEVK, save_dir: str, data_size: int, duration: float, runs: int):
    """
    save_dir: directory to save the result file
    data_size: number of bytes to expect in each packet (match with tx)
    duration: time of acquisition (seconds)
    runs: number of times to repeat the acquisition
    """
    print('----------MODE STATS RX----------')

    output_file = ModeStatsRXFile(save_dir)
    common_dict = {
        'mac': evk.ser.mac_address,
        'board_id': evk.boardid,
        'py_version': evk.PYVERSION,
        'fw_version': evk.version,
    }

    field = FieldModeStatsRX(
        icsetting_bitrate=evk.ic_setting,
        data_size=data_size,
        duration_us=round(duration * 1e6)
    )
    evk.mode_start(MODE.STATS_RX, FIELD_NAME.MODE_STATS_RX, field)

    for i in range(runs):
        sleep(duration)
        result_type, result_bytes = evk.data_rd()

        print(f'\n----------{i}: {repr(result_type)}----------')
        reply = apicall.send_stats_result(
            **{k:str(v) for k,v in common_dict.items()},
            settings=field.to_bytes('little'),
            data=result_bytes
        )
        csv_dict = common_dict.copy()
        csv_dict.update(reply)
        output_file.save_row(csv_dict)
        for k,v in reply.items():
            print(f'{k}: {v}')

    evk.mode_reset()

#################### EXAMPLE: MODE_SERIAL ####################
import threading
ser_lock = threading.Lock()

class SerialTX(threading.Thread):
    def __init__(self, evk: IxanaEVK) -> None:
        super().__init__(daemon=True)
        self.evk = evk
        self.start()
    
    def run(self):
        while True:
            data_in = input()
            print('\033[1A' + '\33[2K', end='')
            ser_lock.acquire()
            print(text.style('<<<', text.STYLE.FG_RED) + ' ' + data_in)
            self.evk.data_wr(MODE.SERIAL, data_in.encode())
            ser_lock.release()

class SerialRX(threading.Thread):
    def __init__(self, evk: IxanaEVK) -> None:
        super().__init__(daemon=True)
        self.evk = evk
        self.start()

    def run(self):
        while True:
            ser_lock.acquire()
            in_waiting = self.evk.ser.in_waiting
            ser_lock.release()
            if not in_waiting:
                sleep(0.1)
                continue
            try:
                ser_lock.acquire()
                result_type, result_bytes = self.evk.data_rd()
                print(text.style('>>>', text.STYLE.FG_BLUE) + ' ' + f'{result_bytes.decode()}')
            except ValueError:
                pass
            finally:
                ser_lock.release()

def _example_mode_serial_config(evk: IxanaEVK, ecc: str, mode: MODE_SERIAL_MODE):
    print(f'----------MODE SERIAL: {mode.name}----------')
    
    if ecc.upper() in ['TRUE', '1']:
        ecc_bool = True
    elif ecc.upper() in ['FALSE', '0']:
        ecc_bool = False
    else:
        ecc_bool = False
        print(text.style('WARNING: unrecognized ecc value, defaulting to False', text.STYLE.FG_YELLOW))
    print(f'ECC: {ecc_bool}')


    field = FieldModeSerial(
        icsetting_bitrate=evk.ic_setting,
        ecc=ecc_bool,
        mode_serial_mode=mode
    )
    evk.mode_start(MODE.SERIAL, FIELD_NAME.MODE_SERIAL, field)

def example_mode_serial_ble_tx(evk: IxanaEVK, ecc: str):
    '''
    ecc: enables ecc on the communication, should match on both sides
    '''
    _example_mode_serial_config(evk, ecc, MODE_SERIAL_MODE.BLE_TX)

    print('Input Data Below:')
    serial_tx = SerialTX(evk)
    while evk.ser.client.is_connected and serial_tx.is_alive():
        serial_tx.join(1)

def example_mode_serial_ble_rx(evk: IxanaEVK, ecc: str):
    '''
    ecc: enables ecc on the communication, should match on both sides
    '''
    _example_mode_serial_config(evk, ecc, MODE_SERIAL_MODE.BLE_RX)
    
    print('Read Data Below:')
    serial_rx = SerialRX(evk)
    while evk.ser.client.is_connected and serial_rx.is_alive():
        serial_rx.join(1)

def example_mode_serial_ble_txrx_hub(evk: IxanaEVK, ecc: str):
    '''
    ecc: enables ecc on the communication, should match on both sides
    '''
    _example_mode_serial_config(evk, ecc, MODE_SERIAL_MODE.BLE_TXRX_HUB)

    print('Input/Read Data Below:')
    serial_tx = SerialTX(evk)
    serial_rx = SerialRX(evk)
    while evk.ser.client.is_connected and serial_tx.is_alive() and serial_rx.is_alive():
        sleep(1.0)

def example_mode_serial_ble_txrx_node(evk: IxanaEVK, ecc: str):
    '''
    ecc: enables ecc on the communication, should match on both sides
    '''
    _example_mode_serial_config(evk, ecc, MODE_SERIAL_MODE.BLE_TXRX_NODE)
    
    print('Input/Read Data Below:')
    serial_tx = SerialTX(evk)
    serial_rx = SerialRX(evk)
    while evk.ser.client.is_connected and serial_tx.is_alive() and serial_rx.is_alive():
        sleep(1.0)

#################### EXAMPLE: MODE_LED ####################
@dataclass
class RGB(ByteClass):
    r: np.uint8
    g: np.uint8
    b: np.uint8
def example_mode_led_tx(evk: IxanaEVK, colors: list[RGB], interval: float):
    print('----------MODE LED TX----------')

    field = FieldModeLED(
        icsetting_bitrate=evk.ic_setting
    )
    evk.mode_start(MODE.LED_TX, FIELD_NAME.MODE_LED_TX, field)

    while True:
        for color in colors:
            print(f'\t{color}')
            evk.data_wr(MODE.LED_TX, color.to_bytes('little'))
            sleep(interval)

def example_mode_led_rx(evk: IxanaEVK):
    print('----------MODE LED RX----------')

    field = FieldModeLED(
        icsetting_bitrate=evk.ic_setting
    )
    evk.mode_start(MODE.LED_RX, FIELD_NAME.MODE_LED_RX, field)

def interp(p1: np.ndarray, p2: np.ndarray, count: int):
    slope = (p2-p1).reshape(1, p1.shape[0])
    pts = np.linspace(0, 1, count).reshape(count, 1)
    result = np.matmul(pts, slope)
    result = result + p1
    return result


#################### ARGS ####################
def read_devices(file_path: str):
    import json

    if not file_path:
        print('no device file path provide, skipping. please use mac address or setup a device file')

    if not os.path.exists(file_path):
        with open(file_path, 'w') as json_file:
            json.dump({'DEVICE1 NAME HERE': 'MAC ADDRESS HERE','DEVICE2 NAME HERE': 'MAC ADDRESS HERE', 'DEVICE...': 'MAC...' }, json_file, indent=4)
        raise FileExistsError(f'missing device file generating default at provided path: {file_path}. please configure and run again')


    with open(file_path, 'r') as json_file:
        devices = json.load(json_file)
    return devices


def arg_example_mode_led_tx(evk: IxanaEVK, interval: float):
    """
    interval: time to wait between changing colors
    """
    pts = [
        (255,0,0),
        (255,255,0),
        (0,255,0),
        (0,255,255),
        (0,0,255),
        (255,0,255),
        ]
    count = 6
    alpha = 1/64
    
    tx_colors = []
    for p1,p2 in zip(pts, pts[1:] + [pts[0]]):
        rgbs = interp(np.array(p1), np.array(p2), count)
        for rgb in rgbs[:-1]:
            tx_colors.append(RGB(*(rgb*alpha)))

    example_mode_led_tx(evk, tx_colors, interval)
MODE_FUNCS = {
    MODE.STATS_TX.name: example_mode_stats_tx,
    MODE.STATS_RX.name: example_mode_stats_rx,
    MODE.SERIAL.name+'_BLE_TX': example_mode_serial_ble_tx,
    MODE.SERIAL.name+'_BLE_RX': example_mode_serial_ble_rx,
    MODE.SERIAL.name+'_BLE_TXRX_HUB': example_mode_serial_ble_txrx_hub,
    MODE.SERIAL.name+'_BLE_TXRX_NODE': example_mode_serial_ble_txrx_node,
    MODE.LED_TX.name: arg_example_mode_led_tx,
    MODE.LED_RX.name: example_mode_led_rx,
}
if __name__ == "__main__":
    import argparse
    import inspect
    from collections import defaultdict

    DEVICES_PATH = 'local/devices.json'
    devices = read_devices(DEVICES_PATH)

    parser = argparse.ArgumentParser()
    dev_mac_group = parser.add_mutually_exclusive_group(required=True)
    dev_mac_group.add_argument('--dev', help='name of device to connect to', choices=list(devices.keys()))
    dev_mac_group.add_argument('--mac', help='mac address of device to connect to')
    parser.add_argument('--brsel', type=int, help='bitrate selection', default=IC_SETTING.LOW_SPEED.value, choices=[v for v in IC_SETTING][:-1])
    subparsers = parser.add_subparsers(help='sub-command help')

    for mode, func in MODE_FUNCS.items():
        subparser = subparsers.add_parser(mode, help=f'help')
        subparser.set_defaults(func=func)

        arg_helps = defaultdict(str)
        if func.__doc__:
            for line in str(func.__doc__).strip().split('\n'):
                arg_name, arg_help = line.split(':')
                arg_name = arg_name.strip()
                arg_help = arg_help.strip()
                arg_helps[arg_name] = arg_help

        relevant_args = inspect.getfullargspec(func).annotations
        relevant_args.pop('evk')
        for arg_name, arg_type in relevant_args.items():
            subparser.add_argument(arg_name, type=arg_type, help=arg_helps[arg_name])

    args = parser.parse_args()
    mac = args.mac if args.mac else devices[args.dev]

    evk = IxanaEVK(mac)
    print(f'VERSION: {evk.version}')
    print(f'BOARD ID: {evk.boardid}')
    print(f'MODE: {repr(evk.mode_rd())}')
    evk.ic_setting = IC_SETTING(args.brsel)

    if hasattr(args, 'func') and args.func:
        relevant_args = inspect.getfullargspec(args.func).annotations
        relevant_args.pop('evk')
        func_args = { k:v for k,v in args.__dict__.items() if k in relevant_args.keys()}
        args.func(evk, **func_args)
    print()
