import threading, time, json
from transport.local_store import LocalStore
from transport.http_out import post_batch

class Syncer:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.store = LocalStore(cfg.get("sqlite_path", "insight.db"))
        self._stop = False
        self._t = None

    def start(self):
        if not self.cfg.get("enable_http"):
            return
        self._stop = False
        self._t = threading.Thread(target=self._loop, daemon=True)
        self._t.start()

    def stop(self):
        self._stop = True
        if self._t:
            self._t.join(timeout=2)

    def _loop(self):
        endpoint = self.cfg.get("http_endpoint")
        token = self.cfg.get("device_token")
        if not (endpoint and token):
            return
        while not self._stop:
            rows = self.store.batch(limit=200)
            if rows:
                ids, payloads = zip(*rows)
                try:
                    post_batch(endpoint, token, list(payloads))
                    self.store.delete_ids(list(ids))
                except Exception:
                    # keep trying later
                    pass
            time.sleep(10)
