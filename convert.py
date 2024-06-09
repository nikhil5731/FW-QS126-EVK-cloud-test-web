import byteclass
import numpy as np
from dataclasses import dataclass
import text
import json
from coms import IC_SETTING, FieldModeStatsRX
from typing import Literal
import rssi
import functools
from telemetrics import push_json, push_json_raw
import concurrent.futures

executor = concurrent.futures.ThreadPoolExecutor()


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

    #print(type(response))

    input = {'mac': mac, 'board_id': board_id, 'py_version': py_version, 'fw_version': fw_version}

    response_dict = dict(response)

    response_dict.update(input)

    #print('response sent')

    # future = executor.submit(push_json(response))

    future = executor.submit(push_json(response_dict))

    return response
