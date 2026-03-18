import subprocess
import re
import time
import threading

def scan_bluetooth_devices(scan_on=True, scan_seconds=5):
    # scan_on=True: scan on, False: scan off, None: nur Liste abfragen
    if scan_on is True:
        try:
            subprocess.check_call(['bluetoothctl', 'scan', 'on'], timeout=3)
        except Exception:
            pass
    elif scan_on is False:
        try:
            subprocess.check_call(['bluetoothctl', 'scan', 'off'], timeout=3)
        except Exception:
            pass
        return []
    # scan_on=None: nur bekannte Geräte
    proc = subprocess.Popen(['bluetoothctl', 'scan', 'on'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    found = {}
    start = time.time()
    try:
        while time.time() - start < scan_seconds:
            line = proc.stdout.readline()
            if not line:
                break
            # Zeilen mit RSSI, TxPower oder Manufacturer überspringen
            if any(x in line for x in ['RSSI', 'TxPower', 'Manufacturer']):
                continue
            m = re.search(r'Device ([0-9A-F:]{17}) (.+)', line)
            if m:
                found[m.group(1)] = m.group(2)
    finally:
        proc.terminate()
        try:
            subprocess.check_call(['bluetoothctl', 'scan', 'off'], timeout=2)
        except Exception:
            pass
    return [{'address': addr, 'name': name} for addr, name in found.items()]

def pair_bluetooth_device(address):
    try:
        subprocess.check_call(['bluetoothctl', 'pair', address], timeout=10)
        subprocess.check_call(['bluetoothctl', 'trust', address], timeout=5)
        subprocess.check_call(['bluetoothctl', 'connect', address], timeout=10)
        return True
    except Exception as e:
        return False

def list_paired_devices():
    try:
        output = subprocess.check_output(['bluetoothctl', 'paired-devices']).decode()
    except Exception:
        output = ''
    devices = []
    for line in output.splitlines():
        m = re.search(r'Device ([0-9A-F:]{17}) (.+)', line)
        if m:
            devices.append({'address': m.group(1), 'name': m.group(2)})
    return devices
