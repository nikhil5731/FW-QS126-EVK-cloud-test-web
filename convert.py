import byteclass
import numpy as np
from dataclasses import dataclass
import text
import json
from coms import IC_SETTING, FieldModeStatsRX
from typing import Literal
import rssi
import functools
from collections import Counter
from offsetdict import mac_avg
from telemetrics import push_json, push_json_raw
import concurrent.futures

try:
    import cPickle as pickle
except ImportError:  # Python 3.x
    import pickle

executor = concurrent.futures.ThreadPoolExecutor()

avg_length = 5

@dataclass
class ICSettings:
    bitrate_hz: int
    carrier_hz: int
    lna_mode: Literal['SE', 'Diff']
    gain: int


SETTINGS = {
    IC_SETTING.LOW_SPEED: ICSettings(
        bitrate_hz=208333,
        carrier_hz=12000000,
        lna_mode='SE',
        gain=0x1F
    )
}


@dataclass
class StatsRXResult(byteclass.ByteClass):
    bytes_per_packet: np.uint32
    acq_duration_us: np.uint32
    packets_missed: np.uint32
    packets_received: np.uint32
    packets_with_errors: np.uint32
    bit_count: np.uint32
    bit_errors: np.uint32
    rssi_base_avg: np.int16
    rssi_avg: np.int16


class StatsRXReply:
    def __init__(self, settings: FieldModeStatsRX, result: StatsRXResult) -> None:
        ic_settings = SETTINGS[settings.icsetting_bitrate]
        rssi_conversion = functools.partial(
            rssi.convert_uv, **vars(ic_settings))
        rssi_base_uv = rssi_conversion(rssi=result.rssi_base_avg)
        rssi_signal_uv = rssi_conversion(rssi=result.rssi_avg)

        self.Bitrate = ic_settings.bitrate_hz
        self.BytesPerPacket = result.bytes_per_packet
        self.Duration = result.acq_duration_us / 1e6
        #print ('calculated RSSI') # Comment for prod
        # PER was PwE
        # PMDR was PER+PwE
        self.BER = result.bit_errors / result.bit_count if result.bit_count else 0.5
        self.PER = result.packets_with_errors / \
            result.packets_received if result.packets_received else 1.0
        self.PMDR = (result.packets_with_errors + result.packets_missed) / \
            (result.packets_missed +
             result.packets_received) if result.packets_received else 1.0
        # TODO proper calculation with spi delays...
        self.Latency = self.Duration / \
            result.packets_received if result.packets_received else None
        self.LinkMargin = rssi.link_margin(
            rssi_base_uv, rssi_signal_uv) if result.rssi_base_avg != 32767 and result.rssi_avg != 32767 else 0.0
        self.Throughput = (result.packets_received-result.packets_with_errors) * \
            self.BytesPerPacket*8/self.Duration if self.Duration else 0.0
        self.RSSIBaseV = rssi_base_uv/1e6
        self.RSSISignalV = rssi_signal_uv/1e6


def convert_stats_result(mac: str, board_id: str, py_version: str, fw_version: str, settings_b: bytearray, data: bytearray) -> dict:
    future = executor.submit(
        push_json_raw({'mac': mac, 'board_id': board_id, 'py_version': py_version, 'fw_version': fw_version,'settings': settings_b, 'data': data}))

    settings = byteclass.from_bytes(FieldModeStatsRX, settings_b)
    result = byteclass.from_bytes(StatsRXResult, data)

    # comment print for prod

    # print(text.style('SETTINGS', text.STYLE.FG_RED))
    # for k, v in vars(settings).items():
    #     print(text.style(f'{k}: {v}', text.STYLE.FG_RED))
    # print(text.style('RESULT', text.STYLE.FG_RED))
    # for k, v in vars(result).items():
    #     print(text.style(f'{k}: {v}', text.STYLE.FG_RED))

    response = vars(StatsRXReply(settings, result))

    # print(type(response))

    input = {'mac': mac, 'board_id': board_id, 'py_version': py_version, 'fw_version': fw_version}

    # todo: Deal with none response. Done

    response_dict = dict(response)

# The following code is to make sure we give certain customers averaged value 

    if mac in mac_avg and None not in response_dict.values(): #We skip None values because it's hard to average when there are none values

        # Define response store or load, if it already exists
        try:

            with open('data.p', 'rb') as fp:
                response_store = pickle.load(fp)
        except:
            response_store = {}

        # If the mac has already been tested

        if mac in response_store.keys():
            # print("stored data",len(response_store[mac]))
            if len(response_store[mac])>avg_length-1:
                response_store[mac].pop(0)  # Make sure the stored value is always equal to the avg length of averaging window
                # print(type(update_mac_response),type(response_store[mac]))
            # else :
            update_mac_response = response_store[mac]

            # Add the new response to the list of data being averaged over
            
            update_mac_response.append(response_dict) 
            response_store[mac]=update_mac_response
            # Use counter to sum over the list of dicts

            Counter_sum = Counter()
            for x in range(0,len(update_mac_response)):
                Counter_sum.update(Counter(update_mac_response[x]))
            # print("counter_sum",dict(Counter_sum))
            return_dict = {key: value / len(update_mac_response) for key, value in Counter_sum.items()} # This is the average of the values
            # avg_mac_response = dict(Counter_sum)
        else:

            # Create new response store if it doesn't already exists for the mac

            update_mac_response = []
            update_mac_response.append(response_dict)
            response_store.update({mac:update_mac_response})
            return_dict = response_dict

        # convert_stats_result.store = response_store

        # print("trying to write")
        # print(type(response_store))
        # with open('data.json', 'w') as outfile:
        #     json.dump(response_store, outfile)
        
        with open('data.p', 'wb') as fp:
            pickle.dump(response_store, fp, protocol=pickle.HIGHEST_PROTOCOL)

            ## avg over the update_mac_response to create the response
    else:
        return_dict = response_dict

    response_dict.update(input)
    return_dict.update(input)




    #print('response sent')

    # future = executor.submit(push_json(response))

    future = executor.submit(push_json(response_dict))

    return return_dict
