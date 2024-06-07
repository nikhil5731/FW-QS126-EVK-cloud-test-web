from coms import MODE
from convert import convert_stats_result
import text

import logging, autologging, uuid
from io import StringIO
import atexit
import time
import os
_log_stream = StringIO()
logging.basicConfig(stream=_log_stream, encoding='utf-8', level=autologging.TRACE, format='%(asctime)s\t%(levelname)s\t%(name)s.%(funcName)s\t%(message)s')

def send_stats_result(mac: str, board_id: str, py_version: str, fw_version: str, settings: bytearray, data: bytearray):
    # TODO backend should save result with these
    # mac: str
    # board_id: str
    # py_version: str
    # fw_version: str
    print(text.style('IDENTIFICATION', text.STYLE.FG_RED))
    print(text.style(f'mac: {mac}', text.STYLE.FG_RED))
    print(text.style(f'board_id: {board_id}', text.STYLE.FG_RED))
    print(text.style(f'py_version: {py_version}', text.STYLE.FG_RED))
    print(text.style(f'fw_version: {fw_version}', text.STYLE.FG_RED))

    result = convert_stats_result(settings, data)

    CUSTOMER_KEYS = [
        'Bitrate',
        'BytesPerPacket',
        'Duration',
        'BER',
        'PER',
        'PMDR',
        'Latency'
    ]
    for k,v in result.items():
        if k not in CUSTOMER_KEYS:
            print(text.style(f'{k}: {v}', text.STYLE.FG_RED))
    return {k:result[k] for k in CUSTOMER_KEYS}

# def send_logs(mac: str, board_id: str, py_version: str, fw_version: str, logs: str):
def send_logs():
    # TODO backend saving

    log_id = str(uuid.uuid4())
    print(f'LOG ID: {log_id}')
    timestr = time.strftime('%Y%m%d_%H%M')
    if not os.path.exists('log'):
        os.mkdir('log')
    file_name = os.path.join('log', timestr + '_' + log_id + '.log')
    with open(file_name, 'w') as wfile:
        wfile.write(_log_stream.getvalue())

atexit.register(send_logs)