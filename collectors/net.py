import psutil
import time

_prev = None  # (ts, bytes_sent, bytes_recv)

def throughput():
    """Return kbps tx/rx since last call. First call returns zeros."""
    global _prev
    now = psutil.net_io_counters()
    ts = time.time()
    if not _prev:
        _prev = (ts, now.bytes_sent, now.bytes_recv)
        return {"net_tx_kbps": 0.0, "net_rx_kbps": 0.0}
    pts, psent, precv = _prev
    dt = max(0.001, ts - pts)
    tx = (now.bytes_sent - psent) * 8.0 / 1000.0 / dt
    rx = (now.bytes_recv - precv) * 8.0 / 1000.0 / dt
    _prev = (ts, now.bytes_sent, now.bytes_recv)
    return {"net_tx_kbps": round(tx, 1), "net_rx_kbps": round(rx, 1)}
