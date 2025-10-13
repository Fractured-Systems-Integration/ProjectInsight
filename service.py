# --- Robust import path setup (paste at very top of service.py) ---
import os, sys, importlib.util

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COLLECTORS_DIR = os.path.join(BASE_DIR, "collectors")

# Ensure both project root and collectors dir are on sys.path
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if COLLECTORS_DIR not in sys.path:
    sys.path.insert(0, COLLECTORS_DIR)

# Try normal package imports first; fall back to direct file loads
try:
    import collectors.processes as processes
    import collectors.net as net
except Exception:
    def _load_module(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[attr-defined]
        return mod

    processes = _load_module("processes", os.path.join(COLLECTORS_DIR, "processes.py"))
    net = _load_module("net", os.path.join(COLLECTORS_DIR, "net.py"))
# --- end robust import setup ---

import threading, time, json
from datetime import datetime
from schema import InsightEnvelope, DeviceIdentity, ResourceSample, ProcessSample, ProcessInfo
from transport.local_store import LocalStore
import system_info  # your existing module

class AgentService:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.store = LocalStore(cfg.get("sqlite_path", "insight.db"))
        self.identity = DeviceIdentity(**system_info.identity())
        self._stop = False
        self._thread = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop = False
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop = True
        if self._thread:
            self._thread.join(timeout=2)

    def _loop(self):
        interval = int(self.cfg.get("interval_seconds", 30))
        retention = int(self.cfg.get("retention_days", 14))
        tags = self.cfg.get("tags", {})
        while not self._stop:
            try:
                res = system_info.resources() | net.throughput()
                sample = ResourceSample(ts=datetime.utcnow(), **res)
                top_list = [ProcessInfo(**p) for p in processes.top_n(8)]
                env = InsightEnvelope(
                    device=self.identity,
                    samples=[sample],
                    processes=ProcessSample(ts=datetime.utcnow(), top=top_list),
                    tags=tags
                )
                self.store.append_json(datetime.utcnow().isoformat(), env.model_dump_json())
                self.store.prune_days(retention)
            except Exception:
                # keep agent resilient; you can add logging here
                pass
            time.sleep(interval)
