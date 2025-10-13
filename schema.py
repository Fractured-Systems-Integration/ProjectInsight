from __future__ import annotations
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime

class DeviceIdentity(BaseModel):
    hostname: str
    os: str
    os_version: str
    macs: List[str] = []
    serial: Optional[str] = None
    model: Optional[str] = None
    domain: Optional[str] = None

class ResourceSample(BaseModel):
    ts: datetime
    cpu_percent: float
    mem_percent: float
    disk_used_gb: float
    disk_total_gb: float
    uptime_seconds: Optional[int] = None
    net_tx_kbps: Optional[float] = None
    net_rx_kbps: Optional[float] = None

class ProcessInfo(BaseModel):
    pid: int
    name: str
    cpu_percent: float
    mem_percent: float

class ProcessSample(BaseModel):
    ts: datetime
    top: List[ProcessInfo] = []

class InsightEnvelope(BaseModel):
    version: str = "1.0"
    device: DeviceIdentity
    samples: List[ResourceSample] = []
    processes: Optional[ProcessSample] = None
    tags: Dict[str, str] = {}
