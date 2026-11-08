"""Jam virtual dan perhitungan Berkeley; semua nilai dalam detik."""
import math
import time
import threading


class VirtualClock:
    def __init__(self, offset=0):
        self.origin = time.time() - time.monotonic()
        self.offset = offset
        self.lock = threading.Lock()

    def now(self):
        with self.lock:
            return self.origin + time.monotonic() + self.offset

    def adjust(self, correction):
        with self.lock:
            self.offset += correction

    def reset(self, offset):
        with self.lock:
            self.offset = offset


def calculate(offsets, threshold=120):
    """Koordinator (offset 0) selalu ikut; outlier tidak ikut rata-rata."""
    if not math.isfinite(threshold) or threshold <= 0:
        raise ValueError("Ambang harus positif dan terbatas.")
    if any(not math.isfinite(x) for x in offsets.values()):
        raise ValueError("Offset harus angka terbatas.")
    accepted = {name: value for name, value in offsets.items() if abs(value) <= threshold}
    average = sum(accepted.values()) / (len(accepted) + 1)
    return average, {name: average - value for name, value in offsets.items()}, accepted
