from dataclasses import dataclass
from typing import Literal
import csv
from operator import itemgetter
import os
from collections import defaultdict
import functools

@dataclass
class CalPiece:
    start: int
    end: int
    coef: list[float]

@dataclass(frozen=True)
class Calibration:
    bitrate: float
    carrier: float
    lna_mode: Literal['SE', 'Diff']
    gain: int

def read_csv(file_path: str) -> dict[Calibration, list[CalPiece]]:
    MAX_ORDER = 8
    with open(file_path, 'r', newline='') as file:
        csv_reader = csv.DictReader(file)
        rows = [row for row in csv_reader if row['bitrate (Hz)']]

    COL_TYPE: dict[str,type] = {
        'bitrate (Hz)': lambda x: round(float(x)),
        'carrier (Hz)': float,
        'gain': functools.partial(int, base=2),
        'lna_mode': str,
        'adc_offset': str,
        '>=start': int,
        '<end': int
    }

    for row in rows:
        for k, t in COL_TYPE.items():
            row[k] = t(row[k])
    
    for key in list(COL_TYPE.keys())[::-1]:
        rows = sorted(rows, key=itemgetter(key))
    
    cals = defaultdict(list)
    for row in rows:
        cal = Calibration(
            bitrate=row['bitrate (Hz)'],
            carrier=row['carrier (Hz)'],
            lna_mode=row['lna_mode'],
            gain=row['gain'],
        )
        cal_piece = CalPiece(
            start=row['>=start'],
            end=row['<end'],
            coef=[float(row[str(order)]) for order in range(MAX_ORDER+1) if row[str(order)]]
        )
        cals[cal].append(cal_piece)
    
    return cals

if __name__ == '__main__':
    MY_DIR = os.path.dirname(__file__)
    FILE_PATH = os.path.join(MY_DIR, 'RSSI2uV_QS126.csv')
    OUT_PATH = os.path.join(MY_DIR, 'cals.py')

    cals = read_csv(FILE_PATH)

    entries = []
    for cal, pieces in cals.items():
        key_str = str(cal)
        vals = []
        for piece in pieces:
            vals.append(str(piece))
        val_str = ',\n\t\t'.join(vals)
        entries.append(f'{key_str}: [\n\t\t{val_str}\n\t]')
    
    with open(OUT_PATH, 'w') as cal_file:
        cal_file.write('from .generate import Calibration, CalPiece\n\n')
        cal_file.write('cal_pieces = {\n')
        cal_file.write('\t' + ',\n\t'.join(entries))
        cal_file.write('\n}\n')