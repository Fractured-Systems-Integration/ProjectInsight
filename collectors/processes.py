import psutil

def top_n(n: int = 8):
    procs = []
    # first call to cpu_percent establishes baseline; second returns real values
    for p in psutil.process_iter(attrs=["pid", "name"]):
        try:
            p.cpu_percent(interval=None)
        except Exception:
            pass
    for p in psutil.process_iter(attrs=["pid", "name", "memory_percent"]):
        try:
            info = p.info
            cpu = p.cpu_percent(interval=0.0)  # non-blocking
            procs.append({
                "pid": int(info.get("pid") or 0),
                "name": (info.get("name") or "")[:128],
                "cpu_percent": float(cpu or 0.0),
                "mem_percent": float(info.get("memory_percent") or 0.0),
            })
        except Exception:
            continue
    procs.sort(key=lambda x: (x["cpu_percent"], x["mem_percent"]), reverse=True)
    return procs[:n]
