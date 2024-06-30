import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../FW-toolchain/Ambiq_AMA4BP/ble_serial/ble_py_app"))
import ble
from enum import IntEnum
from coms import *
from byteclass import ByteClass
from time import sleep

import autologging

@autologging.traced
class IxanaEVK:
    PYVERSION = '0.1.0'
    def __init__(self, mac: str) -> None:
        self.ser = ble.BLESerial(mac)
        self.ser.open()
        self.mode_reset()
        self.version = byteclass.from_bytes(FieldVersion, self.field_rd(FIELD_NAME.VERSION))
        self.boardid = byteclass.from_bytes(FieldBoardID, self.field_rd(FIELD_NAME.BOARDID))
        self.ic_setting_id = None

    def _write(self, data: bytearray | list[int]) -> None:
        self.ser.write(data)

    def _read(self, size: int) -> bytearray:
        return self.ser.read(size)
    #################### FIELD ####################

    @staticmethod
    def _field_data_format(data) -> bytearray:
        if type(data) == int:
            return data.to_bytes(1, byteorder='little', signed=False)
        if issubclass(type(data), IntEnum):
            return data.to_bytes(1, byteorder='little', signed=False)
        if type(data) == list:
            return bytearray(data)
        if type(data) == bytes:
            return bytearray(data)
        if type(data) == bytearray:
            return data
        raise TypeError(f'{type(data)}')

    def field_rd(self, name: FIELD_NAME) -> bytearray:
        # logger.debug(f'{self.field_rd.__name__}({locals().items()})')
        if name > FIELD_NAME.TOTAL:
            raise ValueError(f"invalid FIELD_NAME: {name}")
        
        cmd = bytearray([CMD_TYPE.FIELD.value, name.value, FIELD_DIR.RD.value])
        self._write(cmd)

        response = list(self._read(4))
        if response[:3] != [CMD_TYPE.RESP_FIELD.value, name.value, FIELD_DIR.RD.value]:
            raise ValueError(f"field rd error: {response}")
        if response[3] != FIELD_STATUS.SUCCESS.value:
            raise ValueError(f'field rd error: {repr(FIELD_STATUS(response[3]))}')
        
        return self._read(byteclass.nbytes(FIELD_TYPE[name]))

    def field_wr(self, name: FIELD_NAME, data) -> bytearray:
        if name > FIELD_NAME.TOTAL:
            raise ValueError(f"invalid FIELD_NAME: {name}")
        
        data_list = self._field_data_format(data)
        field_size = 2027 if name == FIELD_NAME.ICSETTING else byteclass.nbytes(FIELD_TYPE[name])
        if len(data_list) != field_size:
            raise ValueError(f"invalid data size: {len(data_list)} != {field_size}")
        
        cmd = bytearray([CMD_TYPE.FIELD.value, name.value, FIELD_DIR.WR.value]) + data_list
        self._write(cmd)

        response = list(self._read(4))
        if response[:3] != [CMD_TYPE.RESP_FIELD.value, name.value, FIELD_DIR.WR.value]:
            raise ValueError(f"field wr error: {response}")
        if response[3] != FIELD_STATUS.SUCCESS.value:
            raise ValueError(f'field wr error: {repr(FIELD_STATUS(response[3]))}')


    def field_wrrd(self, name: FIELD_NAME, data):
        self.field_wr(name, data)
        wr = self._field_data_format(data)
        rd = self.field_rd(name)
        if wr != rd:
            raise ValueError(f'{list(wr)} --> {list(rd)}')

    #################### DATA ####################

    def data_enable(self, enable: bool):
        cmd = [CMD_TYPE.DATA_ENABLE, int(enable)]
        self._write(bytearray(cmd))

    def rd8(self, signed=False) -> int:
        return int.from_bytes(self._read(1), byteorder='little', signed=signed)

    def data_rd(self) -> tuple[MODE, bytearray]:
        cmd_type = CMD_TYPE(self.rd8())
        if cmd_type != CMD_TYPE.DATA:
            raise ValueError(f'{cmd_type}')

        mode = MODE(self.rd8())
        size = self.rd8()
        return (mode, self._read(size))

    def data_wr(self, mode: MODE, data):
        cmd = bytearray([CMD_TYPE.DATA, mode, len(data)]) + self._field_data_format(data)
        self._write(cmd)

        response = list(self._read(3))
        if response[0] != CMD_TYPE.RESP_DATA:
            raise ValueError(f"data wr error: {response}")
        if response[1] != mode:
            raise ValueError(f'data wr incorrect mode: {repr(MODE(response[1]))}')
        if response[2] != DATA_STATUS.SUCCESS:
            raise ValueError(f'data wr failure: {repr(DATA_STATUS(response[2]))}')
    #################### MODE ####################

    def mode_rd(self):
        mode_bytes = self.field_rd(FIELD_NAME.MODE)
        mode_int = int.from_bytes(mode_bytes, byteorder='little', signed=False)
        return MODE(mode_int)

    def mode_wr(self, mode: MODE):
        self.field_wr(FIELD_NAME.MODE, mode)
        print(repr(mode))

    def mode_wrrd(self, mode: MODE):
        self.mode_wr(mode)
        rd = self.mode_rd()
        if rd != mode:
            raise ValueError(repr(mode))

    def mode_reset(self):
        self._write(bytearray([CMD_TYPE.FIELD, FIELD_NAME.MODE, FIELD_DIR.WR, MODE.NONE])) # stop any operations
        sleep(0.5) # pause in case of remaining actions
        self.data_enable(False)
        self.ser.reset_input_buffer() # clear any remaining data

    def mode_start(self, mode: MODE, field: FIELD_NAME | None, field_data: bytearray | ByteClass):
        self.mode_reset()
        self.mode_wrrd(MODE.NONE)

        if field is not None:
            field_bytes = field_data.to_bytes('little') if issubclass(type(field_data), ByteClass) else field_data
            self.field_wrrd(field, field_bytes)

        self.mode_wrrd(mode)
        self.check_ic_status()
        self.data_enable(True)

    #################### ICSTATUS ####################

    def icstatus_rd(self):
        status_bytes = self.field_rd(FIELD_NAME.ICSTATUS)
        status_int = int.from_bytes(status_bytes, byteorder='little', signed=False)
        return IC_STATUS(status_int)

    def check_ic_status(self):
        icstatus = self.icstatus_rd()
        print(repr(icstatus))
        if icstatus != IC_STATUS.SUCCESS:
            raise ValueError(repr(icstatus))