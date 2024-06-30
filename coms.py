from enum import auto, IntEnum
from dataclasses import dataclass
import byteclass
import numpy as np

#################### CMD ####################

class CMD_TYPE(IntEnum):
    FIELD = 0
    DATA = auto()
    RESP_FIELD = auto()
    RESP_DATA = auto()
    DATA_ENABLE = auto()
    TOTAL = auto()

#################### FIELD ####################
class FIELD_NAME(IntEnum):
    VERSION = 0
    BOARDID = auto()
    ICSETTING = auto()
    ICSTATUS = auto()
    MODE = auto()
    MODE_STATS_TX = auto()
    MODE_STATS_RX = auto()
    MODE_SERIAL = auto()
    MODE_LED_TX = auto()
    MODE_LED_RX = auto()
    TOTAL = auto()

@dataclass
class FieldVersion(byteclass.ByteClass):
    major: np.uint8
    minor: np.uint8
    patch: np.uint8

    def __str__(self) -> str:
        return f'{self.major}.{self.minor}.{self.patch}'
@dataclass
class FieldBoardID(byteclass.ByteClass):
    id0: np.uint32
    id1: np.uint32
    id2: np.uint32
    id3: np.uint32

    def __str__(self) -> str:
        return ''.join([f'{id:08X}' for id in vars(self).values()])
@dataclass
class FieldMode(byteclass.ByteClass):
    mode: np.uint8
@dataclass
class FieldICStatus(byteclass.ByteClass):
    status: np.uint8
@dataclass
class FieldModeStatsTX(byteclass.ByteClass):
    data_size: np.uint8
@dataclass
class FieldModeStatsRX(byteclass.ByteClass):
    ic_setting_id: np.uint32
    data_size: np.uint8
    duration_us: np.uint32
    cal_offset: np.uint16
@dataclass
class FieldModeSerial(byteclass.ByteClass):
    ecc: np.uint8
    mode_serial_mode: np.uint8
@dataclass
class FieldModeLED(byteclass.ByteClass):
    dummy: np.uint8
FIELD_TYPE: dict[FIELD_NAME, byteclass.ByteClass] = {
    FIELD_NAME.VERSION: FieldVersion,
    FIELD_NAME.BOARDID: FieldBoardID,
    FIELD_NAME.ICSTATUS: FieldICStatus,
    FIELD_NAME.MODE: FieldMode,
    FIELD_NAME.MODE_STATS_TX: FieldModeStatsTX,
    FIELD_NAME.MODE_STATS_RX: FieldModeStatsRX,
    FIELD_NAME.MODE_SERIAL: FieldModeSerial,
    FIELD_NAME.MODE_LED_TX: FieldModeLED,
    FIELD_NAME.MODE_LED_RX: FieldModeLED,
}
class FIELD_DIR(IntEnum):
    RD = 0
    WR = auto()
    TOTAL = auto()
class FIELD_STATUS(IntEnum):
    SUCCESS = 0
    ERROR_NAME = auto()
    ERROR_DIR = auto()
    ERROR_SIZE = auto()
    ERROR_DATA = auto()
    TOTAL = auto()

#################### DATA ####################
class DATA_STATUS(IntEnum):
    SUCCESS = 0
    ERROR_MODE = auto()
    ERROR_MODE_HAS_NO_DATA = auto()
    ERROR_WRONG_MODE = auto()
    ERROR_SIZE = auto()
    ERROR_DATA_TIMEOUT = auto()
    ERROR_NOT_READY = auto()
    TOTAL = auto()

#################### MODE ####################
class MODE(IntEnum):
    NONE = 0
    STATS_TX = auto()
    STATS_RX = auto()
    SERIAL = auto()
    LED_TX = auto()
    LED_RX = auto()
    TOTAL = auto()

class IC_STATUS(IntEnum):
    NONE = 0
    ERROR_INVALID = auto()
    ERROR = auto()
    ERROR_SCAN = auto()
    ERROR_CACHE = auto()
    SUCCESS = auto()

#################### MODE_SERIAL ####################
class MODE_SERIAL_MODE(IntEnum):
    NONE = 0
    BLE_TX = auto()
    BLE_RX = auto()
    BLE_TXRX_HUB = auto()
    BLE_TXRX_NODE = auto()

    TOTAL = auto()