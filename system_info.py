import socket
import os
import platform
import shutil
import subprocess
import sys
import datetime
import time
import psutil
import uuid
import urllib.request
import json
import getpass

from utils import safe_int, bytes_to_gb

CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
IS_WIN = os.name == "nt"

# -------------------------
# Core identity & resources
# -------------------------
def identity():
    host = socket.gethostname()
    os_name = platform.system()
    os_ver = platform.version()
    macs = []
    try:
        for _, addrs in psutil.net_if_addrs().items():
            for a in addrs:
                addr = getattr(a, "address", "")
                # crude MAC-ish filter
                if addr and addr.count(":") == 5:
                    macs.append(addr)
    except Exception:
        pass

    base = {
        "hostname": host,
        "os": os_name,
        "os_version": os_ver,
        "macs": macs,
        "serial": None,
        "model": None,
        "domain": os.environ.get("USERDOMAIN") or None,
    }

    # Windows: enrich with WMIC where available
    if IS_WIN:
        try:
            model_output = subprocess.check_output(
                ["wmic", "computersystem", "get", "model"],
                universal_newlines=True,
                creationflags=CREATE_NO_WINDOW,
            ).strip().splitlines()
            base["model"] = _first_value_after_header(model_output, "Model")
        except Exception:
            pass

        try:
            serial_output = subprocess.check_output(
                ["wmic", "bios", "get", "serialnumber"],
                universal_newlines=True,
                creationflags=CREATE_NO_WINDOW,
            ).strip().splitlines()
            base["serial"] = _first_value_after_header(serial_output, "Serial")
        except Exception:
            pass

    return base


def resources():
    cpu = psutil.cpu_percent(interval=0.2)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\" if IS_WIN else "/")
    boot_ts = psutil.boot_time()
    return {
        "cpu_percent": float(cpu),
        "mem_percent": float(mem.percent),
        "disk_used_gb": float(disk.used / (1024**3)),
        "disk_total_gb": float(disk.total / (1024**3)),
        "uptime_seconds": int(time.time() - boot_ts),
    }

# -------------------------
# Additions you requested
# -------------------------
def get_current_user():
    # Friendly username
    try:
        return getpass.getuser()
    except Exception:
        return os.environ.get("USERNAME") or os.environ.get("USER") or "Unavailable"


def get_logged_in_email_or_upn():
    """
    Best-effort:
    - Windows domain/Entra: `whoami /upn` returns user@domain.tld
    - Fallback to USERNAME@USERDNSDOMAIN if available
    - Else 'Unavailable'
    """
    if IS_WIN:
        try:
            upn = subprocess.check_output(
                ["whoami", "/upn"],
                universal_newlines=True,
                creationflags=CREATE_NO_WINDOW,
            ).strip()
            if upn and "@" in upn:
                return upn
        except Exception:
            pass

        user = os.environ.get("USERNAME")
        dnsdom = os.environ.get("USERDNSDOMAIN")
        if user and dnsdom:
            return f"{user}@{dnsdom}".lower()

    # Non-Windows or no domain
    return "Unavailable"


def get_timezone_info():
    """
    Returns local system timezone name and UTC offset like '+07:00' or '-05:30'.
    """
    try:
        # Timezone display name
        tz_name = time.tzname[time.daylight] if time.daylight else time.tzname[0]
    except Exception:
        tz_name = time.strftime("%Z")

    try:
        # Compute offset from UTC in seconds
        # time.localtime().tm_gmtoff exists on many Unix; fallback via datetime
        if hasattr(time, "localtime") and hasattr(time.localtime(), "tm_gmtoff"):
            offset_sec = time.localtime().tm_gmtoff  # type: ignore[attr-defined]
        else:
            # Cross-platform fallback
            now = datetime.datetime.now(datetime.timezone.utc).astimezone()
            offset_sec = int(now.utcoffset().total_seconds()) if now.utcoffset() else 0

        sign = "+" if offset_sec >= 0 else "-"
        offset_sec = abs(offset_sec)
        hh = offset_sec // 3600
        mm = (offset_sec % 3600) // 60
        utc_offset = f"{sign}{hh:02d}:{mm:02d}"
    except Exception:
        utc_offset = "Unknown"

    return tz_name, utc_offset


def get_public_ip():
    try:
        return urllib.request.urlopen("https://api.ipify.org", timeout=5).read().decode("utf-8")
    except Exception:
        return "Unavailable"


def get_ip_geolocation(ip: str):
    """
    Fetch geo info for a public IP.
    Primary: ipapi.co
    Fallback: ipinfo.io
    Returns dict with city, region, country, org, latitude, longitude, timezone (from provider).
    """
    if not ip or ip == "Unavailable":
        return {
            "city": "Unavailable",
            "region": "Unavailable",
            "country": "Unavailable",
            "org": "Unavailable",
            "latitude": None,
            "longitude": None,
            "provider_tz": "Unavailable",
        }

    # ipapi.co
    try:
        with urllib.request.urlopen(f"https://ipapi.co/{ip}/json/", timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {
                "city": data.get("city") or "Unavailable",
                "region": data.get("region") or data.get("region_code") or "Unavailable",
                "country": data.get("country_name") or data.get("country") or "Unavailable",
                "org": data.get("org") or data.get("asn") or "Unavailable",
                "latitude": _safe_float(data.get("latitude")),
                "longitude": _safe_float(data.get("longitude")),
                "provider_tz": data.get("timezone") or "Unavailable",
            }
    except Exception:
        pass

    # ipinfo.io fallback
    try:
        with urllib.request.urlopen(f"https://ipinfo.io/{ip}/json", timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            loc = data.get("loc", "")
            lat, lon = (loc.split(",") + [None, None])[:2] if loc else (None, None)
            return {
                "city": data.get("city") or "Unavailable",
                "region": data.get("region") or "Unavailable",
                "country": data.get("country") or "Unavailable",
                "org": data.get("org") or "Unavailable",
                "latitude": _safe_float(lat),
                "longitude": _safe_float(lon),
                "provider_tz": data.get("timezone") or "Unavailable",
            }
    except Exception:
        pass

    return {
        "city": "Unavailable",
        "region": "Unavailable",
        "country": "Unavailable",
        "org": "Unavailable",
        "latitude": None,
        "longitude": None,
        "provider_tz": "Unavailable",
    }

# -------------------------
# Existing helpers
# -------------------------
def get_mac_address():
    mac = uuid.getnode()
    return ":".join(("%012X" % mac)[i:i+2] for i in range(0, 12, 2))


def _first_value_after_header(lines, header_keyword):
    """
    From a WMIC-style output, return the first non-header, non-empty line.
    """
    for line in lines:
        s = line.strip()
        if s and header_keyword.lower() not in s.lower():
            return s
    return "Unavailable"


def _safe_float(x):
    try:
        return float(x)
    except Exception:
        return None

# -------------------------
# Main single-shot collector
# -------------------------
def get_system_info():
    try:
        computer_name = socket.gethostname()

        # Local IPv4 best-effort
        try:
            ip_address = socket.gethostbyname(computer_name)
        except Exception:
            ip_address = "Unavailable"

        public_ip = get_public_ip()
        mac_address = get_mac_address()
        domain = os.environ.get("USERDOMAIN", "Unknown")
        os_version = platform.platform()

        # OS Install Date (Windows)
        if IS_WIN:
            try:
                install_output = subprocess.check_output(
                    ["powershell", "-Command",
                     "(Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion').InstallDate"],
                    universal_newlines=True,
                    creationflags=CREATE_NO_WINDOW,
                ).strip().splitlines()
                install_epoch = next((ln.strip() for ln in install_output if ln.strip().isdigit()), None)
                os_install_date = datetime.datetime.fromtimestamp(int(install_epoch)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ) if install_epoch else "Unavailable"
            except Exception:
                os_install_date = "Unavailable"
        else:
            os_install_date = "Unavailable"

        # Model (Windows WMIC)
        if IS_WIN:
            try:
                model_output = subprocess.check_output(
                    ["wmic", "computersystem", "get", "model"],
                    universal_newlines=True,
                    creationflags=CREATE_NO_WINDOW,
                ).strip().splitlines()
                model = _first_value_after_header(model_output, "Model")
            except Exception:
                model = "Unavailable"
        else:
            model = "Unavailable"

        # Last Booted (Windows WMIC)
        if IS_WIN:
            try:
                boot_output = subprocess.check_output(
                    ["wmic", "os", "get", "lastbootuptime"],
                    universal_newlines=True,
                    creationflags=CREATE_NO_WINDOW,
                ).strip().splitlines()
                boot_time_raw = _first_value_after_header(boot_output, "Boot")
                boot_time = datetime.datetime.strptime(boot_time_raw[:14], "%Y%m%d%H%M%S").strftime(
                    "%Y-%m-%d %H:%M:%S"
                ) if boot_time_raw and boot_time_raw != "Unavailable" else "Unavailable"
            except Exception:
                boot_time = "Unavailable"
        else:
            # Cross-platform fallback
            try:
                boot_ts = psutil.boot_time()
                boot_time = datetime.datetime.fromtimestamp(boot_ts).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                boot_time = "Unavailable"

        # Free Disk Space (GB) on system drive
        try:
            root_path = "C:\\" if IS_WIN else "/"
            total, used, free = shutil.disk_usage(root_path)
            free_gb = free // (2**30)
        except Exception:
            free_gb = "Unavailable"

        # Installed Memory (GB)
        try:
            if IS_WIN:
                ram_output = subprocess.check_output(
                    ["wmic", "computersystem", "get", "totalphysicalmemory"],
                    universal_newlines=True,
                    creationflags=CREATE_NO_WINDOW,
                ).strip().splitlines()
                ram_bytes = next((ln.strip() for ln in ram_output if ln.strip().isdigit()), None)
                ram_gb = bytes_to_gb(safe_int(ram_bytes))
            else:
                ram = psutil.virtual_memory()
                ram_gb = bytes_to_gb(int(ram.total))
        except Exception:
            ram_gb = "Unavailable"

        # Serial Number (Windows WMIC)
        if IS_WIN:
            try:
                serial_output = subprocess.check_output(
                    ["wmic", "bios", "get", "serialnumber"],
                    universal_newlines=True,
                    creationflags=CREATE_NO_WINDOW,
                ).strip().splitlines()
                serial = _first_value_after_header(serial_output, "Serial")
            except Exception:
                serial = "Unavailable"
        else:
            serial = "Unavailable"

        # NEW: user + email/UPN + timezone + IP geolocation
        user = get_current_user()
        upn_or_email = get_logged_in_email_or_upn()
        tz_name, utc_offset = get_timezone_info()
        geo = get_ip_geolocation(public_ip)

        return {
            # Device & network
            "Computer Name": computer_name,
            "IP Address": ip_address,
            "Public IP": public_ip,
            "MAC Address": mac_address,
            "Domain": domain,

            # OS
            "OS Version": os_version,
            "OS Install Date": os_install_date,
            "Model": model,
            "Last Booted": boot_time,
            "Free Disk Space (GB)": free_gb,
            "Installed Memory (GB)": ram_gb,
            "Serial Number": serial,

            # NEW: User/identity
            "Current User": user,
            "Logged-in Email/UPN": upn_or_email,

            # NEW: Timezone
            "Time Zone (System)": tz_name,
            "UTC Offset": utc_offset,

            # NEW: Public IP Geo
            "IP Location (City)": geo.get("city"),
            "IP Location (Region)": geo.get("region"),
            "IP Location (Country)": geo.get("country"),
            "ISP / Org": geo.get("org"),
            "Latitude": geo.get("latitude"),
            "Longitude": geo.get("longitude"),
            "Provider Timezone (IP)": geo.get("provider_tz"),
        }

    except Exception as e:
        raise RuntimeError(f"System info collection failed: {e}")
