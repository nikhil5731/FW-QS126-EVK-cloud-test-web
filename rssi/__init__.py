from typing import Literal
if __name__ == '__main__':
    from cals import cal_pieces
    from generate import Calibration
else:
    from .cals import cal_pieces
    from .generate import Calibration

from math import log10

def convert_uv(bitrate_hz: float, carrier_hz: float, lna_mode: Literal['SE', 'Diff'], gain: int, rssi: int):
    cal = Calibration(bitrate_hz,carrier_hz,lna_mode,gain)
    if cal not in cal_pieces.keys():
        return None

    rssi_clamped = max(int(rssi), 0) # minimum value of 0
    rssi_clamped = min(rssi_clamped, cal_pieces[cal][-1].end-1) # cap to the max of the last piece

    if rssi_clamped < cal_pieces[cal][0].start: # if rssi is below the start of the first piece, use the first piece
        piece_sel = cal_pieces[cal][0]
    else:
        for piece in cal_pieces[cal]:
            if rssi_clamped >= piece.start and rssi_clamped < piece.end:
                piece_sel = piece
                break
    
    result = 0.0
    for i, coef in enumerate(piece_sel.coef):
        result += coef*rssi_clamped**i

    result = max(10, result) # minimum value of 10uV

    return result

def link_margin(baseline_uv: float, signal_uv: float):
    if baseline_uv > 0.0 and signal_uv > 0.0:
        return 20 * log10(signal_uv/baseline_uv)
    return None

def main():
    from functools import partial
    import matplotlib.pyplot as plt

    
    for key in cal_pieces.keys():
        conversion = partial(convert_uv,
            bitrate_hz=key.bitrate,
            carrier_hz=key.carrier,
            lna_mode=key.lna_mode,
            gain=key.gain
        )

        rssi_uv = {}
        for i in range(-512, 512, 1):
            rssi_uv[i] = conversion(rssi=i)
        
        plt.title(f'{key.bitrate}, {key.carrier}, {key.lna_mode}, 0b{key.gain:05b}/{key.gain}')
        plt.plot(rssi_uv.keys(), rssi_uv.values())
        plt.show()

if __name__ == '__main__':
    main()