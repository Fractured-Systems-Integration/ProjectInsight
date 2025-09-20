import socket
import os
import platform
import shutil
import subprocess
import sys
import datetime
import uuid
import urllib.request
from utils import safe_int, bytes_to_gb

CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

def get_mac_address():
    mac = uuid.getnode()
    mac_str = ':'.join(("%012X" % mac)[i:i+2] for i in range(0, 12, 2))
    return mac_str

def get_public_ip():
    try:
        return urllib.request.urlopen('https://api.ipify.org').read().decode('utf8')
    except:
        return "Unavailable"

def get_system_info():
    try:
        computer_name = socket.gethostname()
        ip_address = socket.gethostbyname(computer_name)
        public_ip = get_public_ip()
        mac_address = get_mac_address()
        domain = os.environ.get('USERDOMAIN', 'Unknown')
        os_version = platform.platform()

        # OS Install Date
        install_output = subprocess.check_output(
            ['powershell', '-Command',
             "(Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion').InstallDate"],
            universal_newlines=True, creationflags=CREATE_NO_WINDOW
        ).strip().split('\n')
        install_epoch = next((line.strip() for line in install_output if line.strip().isdigit()), None)
        os_install_date = datetime.datetime.fromtimestamp(int(install_epoch)).strftime('%Y-%m-%d %H:%M:%S') if install_epoch else "Unavailable"

        # Model
        model_output = subprocess.check_output(
            ['wmic', 'computersystem', 'get', 'model'],
            universal_newlines=True, creationflags=CREATE_NO_WINDOW
        ).strip().split('\n')
        model = next((line.strip() for line in model_output if line.strip() and "Model" not in line), "Unavailable")

        # Last Booted
        boot_output = subprocess.check_output(
            ['wmic', 'os', 'get', 'lastbootuptime'],
            universal_newlines=True, creationflags=CREATE_NO_WINDOW
        ).strip().split('\n')
        boot_time_raw = next((line.strip() for line in boot_output if line.strip() and "Boot" not in line), None)
        boot_time = datetime.datetime.strptime(boot_time_raw[:14], '%Y%m%d%H%M%S').strftime('%Y-%m-%d %H:%M:%S') if boot_time_raw else "Unavailable"

        # Free Disk Space
        total, used, free = shutil.disk_usage("C:\\")
        free_gb = free // (2**30)

        # RAM
        ram_output = subprocess.check_output(
            ['wmic', 'computersystem', 'get', 'totalphysicalmemory'],
            universal_newlines=True, creationflags=CREATE_NO_WINDOW
        ).strip().split('\n')
        ram_bytes = next((line.strip() for line in ram_output if line.strip().isdigit()), None)
        ram_gb = bytes_to_gb(safe_int(ram_bytes))

        # Serial Number
        serial_output = subprocess.check_output(
            ['wmic', 'bios', 'get', 'serialnumber'],
            universal_newlines=True, creationflags=CREATE_NO_WINDOW
        ).strip().split('\n')
        serial = next((line.strip() for line in serial_output if line.strip() and "Serial" not in line), "Unavailable")

        return {
            "Computer Name": computer_name,
            "IP Address": ip_address,
            "Public IP": public_ip,
            "MAC Address": mac_address,
            "Domain": domain,
            "OS Version": os_version,
            "OS Install Date": os_install_date,
            "Model": model,
            "Last Booted": boot_time,
            "Free Disk Space (GB)": free_gb,
            "Installed Memory (GB)": ram_gb,
            "Serial Number": serial
        }

    except Exception as e:
        raise RuntimeError(f"System info collection failed: {e}")

